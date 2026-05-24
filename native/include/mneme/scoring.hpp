// Hybrid retrieval score, same formula as the Python implementation but
// vectorised on a batch of candidates.

#pragma once

#include <cstddef>
#include <cstdint>

namespace mneme {

struct ScoreInputs {
    const float* similarity;       // [n]
    const double* created_ts;      // [n], unix seconds
    const std::int64_t* access;    // [n]
    const float* importance;       // [n]
};

struct ScoreWeights {
    float w_sim = 0.55f;
    float w_recency = 0.20f;
    float w_importance = 0.20f;
    float w_access = 0.05f;
    float recency_half_life_days = 30.0f;
};

// Writes hybrid scores into `out` (length n). `now_ts` is unix seconds.
void compute_scores(
    std::size_t n,
    const ScoreInputs& in,
    const ScoreWeights& w,
    double now_ts,
    float* out
);

}  // namespace mneme
