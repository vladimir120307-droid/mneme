#include "mneme/scoring.hpp"

#include <cmath>

#ifdef MNEME_HAVE_OPENMP
#include <omp.h>
#endif

namespace mneme {

void compute_scores(
    std::size_t n,
    const ScoreInputs& in,
    const ScoreWeights& w,
    double now_ts,
    float* out
) {
    const float secs_per_day = 86400.0f;
    const float inv_half_life = 1.0f / w.recency_half_life_days;
    const float inv_access_scale = 1.0f / 5.0f;

#ifdef MNEME_HAVE_OPENMP
#pragma omp parallel for schedule(static) if (n > 512)
#endif
    for (std::ptrdiff_t i = 0; i < static_cast<std::ptrdiff_t>(n); ++i) {
        float age_days =
            static_cast<float>((now_ts - in.created_ts[i]) / secs_per_day);
        if (age_days < 0.0f) age_days = 0.0f;
        const float recency = std::exp(-age_days * inv_half_life);
        const float access_boost =
            1.0f - std::exp(-static_cast<float>(in.access[i]) * inv_access_scale);
        out[i] = w.w_sim * in.similarity[i]
               + w.w_recency * recency
               + w.w_importance * in.importance[i]
               + w.w_access * access_boost;
    }
}

}  // namespace mneme
