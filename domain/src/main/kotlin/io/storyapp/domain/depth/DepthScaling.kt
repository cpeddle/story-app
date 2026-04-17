package io.storyapp.domain.depth

import io.storyapp.core.model.depth.DepthBounds

fun DepthBounds.scaleForY(y: Float): Float {
    val t = ((y - yMin) / (yMax - yMin)).coerceIn(0f, 1f)
    val eased = curve.easeForNormalisedT(t)
    return scaleAtBack + (scaleAtFront - scaleAtBack) * eased
}
