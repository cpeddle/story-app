package io.storyapp.core.model.depth

sealed interface EasingCurve {
    fun easeForNormalisedT(t: Float): Float

    /** Linear: f(t) = t */
    data object LINEAR : EasingCurve {
        override fun easeForNormalisedT(t: Float): Float = t
    }

    /** Ease-in quadratic: f(t) = t² */
    data object EASE_IN_QUAD : EasingCurve {
        override fun easeForNormalisedT(t: Float): Float = t * t
    }

    /** Ease-in cubic: f(t) = t³ */
    data object EASE_IN_CUBIC : EasingCurve {
        override fun easeForNormalisedT(t: Float): Float = t * t * t
    }
}

data class DepthBounds(
    val yMin: Float,
    val yMax: Float,
    val scaleAtBack: Float,
    val scaleAtFront: Float,
    val curve: EasingCurve = EasingCurve.EASE_IN_QUAD,
) {
    init {
        require(yMin in 0f..1f) { "yMin must be in [0.0, 1.0], got $yMin" }
        require(yMax in 0f..1f) { "yMax must be in [0.0, 1.0], got $yMax" }
        require(yMin < yMax) { "yMin ($yMin) must be < yMax ($yMax)" }
        require(scaleAtBack > 0f) { "scaleAtBack must be positive, got $scaleAtBack" }
        require(scaleAtFront >= scaleAtBack) { "scaleAtFront ($scaleAtFront) must be >= scaleAtBack ($scaleAtBack)" }
    }
}
