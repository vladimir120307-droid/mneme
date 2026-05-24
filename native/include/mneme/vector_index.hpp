// SIMD-friendly brute-force cosine vector index.
//
// Layout: row-major float32 matrix of L2-normalised vectors. Search is a
// dense matrix-vector product followed by partial top-k. With AVX2 + -O3
// the compiler auto-vectorises the inner loop to one fused multiply-add per
// 8 floats per cycle, and OpenMP fans batches across cores.

#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace mneme {

class VectorIndex {
public:
    using Hit = std::pair<std::string, float>;

    explicit VectorIndex(std::size_t dim);

    // Vectors are assumed to be L2-normalised by the caller (the embedder
    // already does this). We do not re-normalise to keep search hot.
    void add(const std::string& memory_id, const float* vec);

    // Returns up to k hits sorted by descending cosine similarity.
    std::vector<Hit> search(const float* query, std::size_t k) const;

    // Soft removal: drops the id from the lookup map and zeroes its row so
    // it scores -1 against any query. Cheap; periodic compact() reclaims rows.
    void remove(const std::string& memory_id);

    void compact();

    std::size_t size() const noexcept { return id_to_row_.size(); }
    std::size_t dim() const noexcept { return dim_; }

    void save(const std::filesystem::path& path) const;
    static VectorIndex load(const std::filesystem::path& path);

private:
    std::size_t dim_ = 0;
    std::vector<float> vectors_;                              // row-major, rows_ * dim_
    std::vector<std::string> row_ids_;                        // row -> id ("" = tombstone)
    std::unordered_map<std::string, std::size_t> id_to_row_;  // id -> row
    std::vector<std::size_t> free_rows_;                      // reusable tombstoned rows
};

}  // namespace mneme
