#include "mneme/vector_index.hpp"

#include <algorithm>
#include <cstring>
#include <fstream>
#include <stdexcept>

#ifdef MNEME_HAVE_OPENMP
#include <omp.h>
#endif

namespace mneme {

namespace {

constexpr std::uint32_t kMagic = 0x4D4E4D49u;  // 'MNMI'
constexpr std::uint32_t kVersion = 1;

// Dot product of two L2-normalised float vectors. -O3 + -mavx2 turns this
// into one FMA per 8 floats; with OpenMP the outer search loop is what
// scales across cores.
float dot(const float* __restrict a, const float* __restrict b, std::size_t n) noexcept {
    float acc = 0.0f;
    for (std::size_t i = 0; i < n; ++i) {
        acc += a[i] * b[i];
    }
    return acc;
}

}  // namespace

VectorIndex::VectorIndex(std::size_t dim) : dim_(dim) {
    if (dim == 0) throw std::invalid_argument("dim must be > 0");
}

void VectorIndex::add(const std::string& memory_id, const float* vec) {
    auto it = id_to_row_.find(memory_id);
    std::size_t row;
    if (it != id_to_row_.end()) {
        row = it->second;
    } else if (!free_rows_.empty()) {
        row = free_rows_.back();
        free_rows_.pop_back();
        row_ids_[row] = memory_id;
        id_to_row_.emplace(memory_id, row);
    } else {
        row = row_ids_.size();
        row_ids_.push_back(memory_id);
        vectors_.resize(vectors_.size() + dim_);
        id_to_row_.emplace(memory_id, row);
    }
    std::memcpy(&vectors_[row * dim_], vec, dim_ * sizeof(float));
}

std::vector<VectorIndex::Hit>
VectorIndex::search(const float* query, std::size_t k) const {
    const std::size_t rows = row_ids_.size();
    if (rows == 0 || k == 0) return {};

    std::vector<float> sims(rows);

#ifdef MNEME_HAVE_OPENMP
#pragma omp parallel for schedule(static) if (rows > 512)
#endif
    for (std::ptrdiff_t r = 0; r < static_cast<std::ptrdiff_t>(rows); ++r) {
        if (row_ids_[r].empty()) {
            sims[r] = -1.0f;  // tombstone
        } else {
            sims[r] = dot(&vectors_[r * dim_], query, dim_);
        }
    }

    const std::size_t kk = std::min(k, rows);
    std::vector<std::size_t> idx(rows);
    for (std::size_t i = 0; i < rows; ++i) idx[i] = i;
    std::partial_sort(
        idx.begin(), idx.begin() + kk, idx.end(),
        [&](std::size_t a, std::size_t b) { return sims[a] > sims[b]; }
    );

    std::vector<Hit> out;
    out.reserve(kk);
    for (std::size_t i = 0; i < kk; ++i) {
        const std::size_t r = idx[i];
        if (row_ids_[r].empty()) continue;  // skip tombstones in case k > live
        out.emplace_back(row_ids_[r], sims[r]);
    }
    return out;
}

void VectorIndex::remove(const std::string& memory_id) {
    auto it = id_to_row_.find(memory_id);
    if (it == id_to_row_.end()) return;
    const std::size_t row = it->second;
    id_to_row_.erase(it);
    row_ids_[row].clear();
    std::fill_n(&vectors_[row * dim_], dim_, 0.0f);
    free_rows_.push_back(row);
}

void VectorIndex::compact() {
    if (free_rows_.empty()) return;
    std::vector<float> new_vecs;
    std::vector<std::string> new_ids;
    new_vecs.reserve(id_to_row_.size() * dim_);
    new_ids.reserve(id_to_row_.size());
    std::unordered_map<std::string, std::size_t> new_map;
    new_map.reserve(id_to_row_.size());
    for (std::size_t r = 0; r < row_ids_.size(); ++r) {
        if (row_ids_[r].empty()) continue;
        const std::size_t new_row = new_ids.size();
        new_map.emplace(row_ids_[r], new_row);
        new_ids.push_back(std::move(row_ids_[r]));
        new_vecs.insert(
            new_vecs.end(),
            vectors_.begin() + static_cast<std::ptrdiff_t>(r * dim_),
            vectors_.begin() + static_cast<std::ptrdiff_t>((r + 1) * dim_)
        );
    }
    vectors_ = std::move(new_vecs);
    row_ids_ = std::move(new_ids);
    id_to_row_ = std::move(new_map);
    free_rows_.clear();
}

void VectorIndex::save(const std::filesystem::path& path) const {
    std::ofstream f(path, std::ios::binary | std::ios::trunc);
    if (!f) throw std::runtime_error("cannot open " + path.string());
    const std::uint64_t rows = row_ids_.size();
    const std::uint64_t d = dim_;
    f.write(reinterpret_cast<const char*>(&kMagic), sizeof(kMagic));
    f.write(reinterpret_cast<const char*>(&kVersion), sizeof(kVersion));
    f.write(reinterpret_cast<const char*>(&d), sizeof(d));
    f.write(reinterpret_cast<const char*>(&rows), sizeof(rows));
    f.write(
        reinterpret_cast<const char*>(vectors_.data()),
        static_cast<std::streamsize>(vectors_.size() * sizeof(float))
    );
    for (const auto& id : row_ids_) {
        const std::uint32_t len = static_cast<std::uint32_t>(id.size());
        f.write(reinterpret_cast<const char*>(&len), sizeof(len));
        if (len) f.write(id.data(), len);
    }
}

VectorIndex VectorIndex::load(const std::filesystem::path& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("cannot open " + path.string());
    std::uint32_t magic = 0, version = 0;
    std::uint64_t d = 0, rows = 0;
    f.read(reinterpret_cast<char*>(&magic), sizeof(magic));
    f.read(reinterpret_cast<char*>(&version), sizeof(version));
    f.read(reinterpret_cast<char*>(&d), sizeof(d));
    f.read(reinterpret_cast<char*>(&rows), sizeof(rows));
    if (magic != kMagic) throw std::runtime_error("bad magic in index file");
    if (version != kVersion) throw std::runtime_error("unsupported index version");

    VectorIndex idx(static_cast<std::size_t>(d));
    idx.vectors_.resize(static_cast<std::size_t>(rows * d));
    f.read(
        reinterpret_cast<char*>(idx.vectors_.data()),
        static_cast<std::streamsize>(idx.vectors_.size() * sizeof(float))
    );
    idx.row_ids_.resize(static_cast<std::size_t>(rows));
    for (std::size_t r = 0; r < rows; ++r) {
        std::uint32_t len = 0;
        f.read(reinterpret_cast<char*>(&len), sizeof(len));
        if (len) {
            idx.row_ids_[r].resize(len);
            f.read(idx.row_ids_[r].data(), len);
            idx.id_to_row_.emplace(idx.row_ids_[r], r);
        } else {
            idx.free_rows_.push_back(r);
        }
    }
    return idx;
}

}  // namespace mneme
