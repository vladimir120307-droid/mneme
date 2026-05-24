// Python bindings for the Mneme native core.

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <pybind11/stl/filesystem.h>

#include "mneme/scoring.hpp"
#include "mneme/vector_index.hpp"

namespace py = pybind11;
using mneme::ScoreInputs;
using mneme::ScoreWeights;
using mneme::VectorIndex;

namespace {

using F32Array = py::array_t<float, py::array::c_style | py::array::forcecast>;
using F64Array = py::array_t<double, py::array::c_style | py::array::forcecast>;
using I64Array = py::array_t<std::int64_t, py::array::c_style | py::array::forcecast>;

void check_vec(const F32Array& v, std::size_t dim, const char* who) {
    if (v.ndim() != 1 || static_cast<std::size_t>(v.shape(0)) != dim) {
        throw py::value_error(std::string(who)
            + ": expected 1-D float32 array of length " + std::to_string(dim));
    }
}

}  // namespace

PYBIND11_MODULE(_native, m) {
    m.doc() = "Mneme native core: vector index and scoring (C++17 + SIMD).";

    py::class_<VectorIndex>(m, "VectorIndex")
        .def(py::init<std::size_t>(), py::arg("dim"))
        .def_property_readonly("dim", &VectorIndex::dim)
        .def("__len__", &VectorIndex::size)
        .def("add",
            [](VectorIndex& self, const std::string& id, F32Array v) {
                check_vec(v, self.dim(), "add");
                self.add(id, v.data());
            },
            py::arg("memory_id"), py::arg("vector"))
        .def("search",
            [](const VectorIndex& self, F32Array q, std::size_t k) {
                check_vec(q, self.dim(), "search");
                return self.search(q.data(), k);
            },
            py::arg("query"), py::arg("k") = 10)
        .def("remove", &VectorIndex::remove, py::arg("memory_id"))
        .def("compact", &VectorIndex::compact)
        .def("save", &VectorIndex::save, py::arg("path"))
        .def_static("load", &VectorIndex::load, py::arg("path"));

    py::class_<ScoreWeights>(m, "ScoreWeights")
        .def(py::init<>())
        .def_readwrite("w_sim", &ScoreWeights::w_sim)
        .def_readwrite("w_recency", &ScoreWeights::w_recency)
        .def_readwrite("w_importance", &ScoreWeights::w_importance)
        .def_readwrite("w_access", &ScoreWeights::w_access)
        .def_readwrite("recency_half_life_days",
                       &ScoreWeights::recency_half_life_days);

    m.def("compute_scores",
        [](F32Array similarity, F64Array created_ts, I64Array access,
           F32Array importance, const ScoreWeights& w, double now_ts) {
            const auto n = static_cast<std::size_t>(similarity.shape(0));
            if (created_ts.shape(0) != similarity.shape(0)
                || access.shape(0) != similarity.shape(0)
                || importance.shape(0) != similarity.shape(0)) {
                throw py::value_error("input arrays must have equal length");
            }
            ScoreInputs in{
                similarity.data(),
                created_ts.data(),
                access.data(),
                importance.data(),
            };
            auto out = F32Array(n);
            mneme::compute_scores(n, in, w, now_ts, out.mutable_data());
            return out;
        },
        py::arg("similarity"),
        py::arg("created_ts"),
        py::arg("access"),
        py::arg("importance"),
        py::arg("weights"),
        py::arg("now_ts"));
}
