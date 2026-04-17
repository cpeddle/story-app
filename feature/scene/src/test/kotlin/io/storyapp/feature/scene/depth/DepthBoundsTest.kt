package io.storyapp.feature.scene.depth

import io.storyapp.core.model.depth.DepthBounds
import io.storyapp.core.model.depth.EasingCurve
import io.storyapp.domain.depth.scaleForY
import org.junit.jupiter.api.Nested
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import kotlin.test.assertEquals
import kotlin.test.assertTrue

private const val EPSILON = 1e-4f

class DepthBoundsTest {

    @Nested
    inner class EasingCurveTests {

        @Test
        fun `LINEAR at t=0_5 returns 0_5`() {
            assertEquals(0.5f, EasingCurve.LINEAR.easeForNormalisedT(0.5f), EPSILON)
        }

        @Test
        fun `EASE_IN_QUAD at t=0_5 returns 0_25`() {
            assertEquals(0.25f, EasingCurve.EASE_IN_QUAD.easeForNormalisedT(0.5f), EPSILON)
        }

        @Test
        fun `EASE_IN_CUBIC at t=0_5 returns 0_125`() {
            assertEquals(0.125f, EasingCurve.EASE_IN_CUBIC.easeForNormalisedT(0.5f), EPSILON)
        }

        @Test
        fun `all curves return 0 at t=0`() {
            listOf(EasingCurve.LINEAR, EasingCurve.EASE_IN_QUAD, EasingCurve.EASE_IN_CUBIC).forEach {
                assertEquals(0f, it.easeForNormalisedT(0f), EPSILON)
            }
        }

        @Test
        fun `all curves return 1 at t=1`() {
            listOf(EasingCurve.LINEAR, EasingCurve.EASE_IN_QUAD, EasingCurve.EASE_IN_CUBIC).forEach {
                assertEquals(1f, it.easeForNormalisedT(1f), EPSILON)
            }
        }
    }

    @Nested
    inner class ValidationTests {

        @Test
        fun `yMin greater than yMax throws`() {
            assertThrows<IllegalArgumentException> {
                DepthBounds(yMin = 0.8f, yMax = 0.2f, scaleAtBack = 0.55f, scaleAtFront = 1.0f)
            }
        }

        @Test
        fun `yMin equals yMax throws`() {
            assertThrows<IllegalArgumentException> {
                DepthBounds(yMin = 0.5f, yMax = 0.5f, scaleAtBack = 0.55f, scaleAtFront = 1.0f)
            }
        }

        @Test
        fun `yMin below 0 throws`() {
            assertThrows<IllegalArgumentException> {
                DepthBounds(yMin = -0.1f, yMax = 0.8f, scaleAtBack = 0.55f, scaleAtFront = 1.0f)
            }
        }

        @Test
        fun `yMax above 1 throws`() {
            assertThrows<IllegalArgumentException> {
                DepthBounds(yMin = 0.1f, yMax = 1.1f, scaleAtBack = 0.55f, scaleAtFront = 1.0f)
            }
        }

        @Test
        fun `scaleAtBack zero throws`() {
            assertThrows<IllegalArgumentException> {
                DepthBounds(yMin = 0.15f, yMax = 0.85f, scaleAtBack = 0f, scaleAtFront = 1.0f)
            }
        }

        @Test
        fun `scaleAtBack negative throws`() {
            assertThrows<IllegalArgumentException> {
                DepthBounds(yMin = 0.15f, yMax = 0.85f, scaleAtBack = -0.1f, scaleAtFront = 1.0f)
            }
        }

        @Test
        fun `scaleAtFront less than scaleAtBack throws`() {
            assertThrows<IllegalArgumentException> {
                DepthBounds(yMin = 0.15f, yMax = 0.85f, scaleAtBack = 1.0f, scaleAtFront = 0.55f)
            }
        }
    }

    @Nested
    inner class ScaleForYTests {

        private val throneRoom = DepthBounds(
            yMin = 0.15f, yMax = 0.85f,
            scaleAtBack = 0.55f, scaleAtFront = 1.0f,
            curve = EasingCurve.EASE_IN_QUAD,
        )

        @Test
        fun `at yMin returns scaleAtBack`() {
            assertEquals(0.55f, throneRoom.scaleForY(0.15f), EPSILON)
        }

        @Test
        fun `at yMax returns scaleAtFront`() {
            assertEquals(1.0f, throneRoom.scaleForY(0.85f), EPSILON)
        }

        @Test
        fun `EASE_IN_QUAD midpoint is non-linear (0_6625 not 0_775)`() {
            // t = (0.5 - 0.15) / (0.85 - 0.15) = 0.5
            // eased = 0.5² = 0.25
            // scale = 0.55 + 0.45 × 0.25 = 0.6625
            val scale = throneRoom.scaleForY(0.5f)
            assertEquals(0.6625f, scale, EPSILON)
            assertTrue(scale < 0.775f, "Quad must be less than linear at midpoint")
        }

        @Test
        fun `LINEAR midpoint returns 0_775`() {
            val linear = throneRoom.copy(curve = EasingCurve.LINEAR)
            assertEquals(0.775f, linear.scaleForY(0.5f), EPSILON)
        }

        @Test
        fun `EASE_IN_CUBIC midpoint returns 0_60625`() {
            // t = 0.5, eased = 0.125, scale = 0.55 + 0.45 × 0.125 = 0.60625
            val cubic = throneRoom.copy(curve = EasingCurve.EASE_IN_CUBIC)
            assertEquals(0.60625f, cubic.scaleForY(0.5f), EPSILON)
        }

        @Test
        fun `below yMin clamps to scaleAtBack`() {
            assertEquals(0.55f, throneRoom.scaleForY(0.0f), EPSILON)
        }

        @Test
        fun `above yMax clamps to scaleAtFront`() {
            assertEquals(1.0f, throneRoom.scaleForY(1.0f), EPSILON)
        }

        @Test
        fun `scaleAtBack equals scaleAtFront gives constant scale`() {
            val flat = DepthBounds(
                yMin = 0.2f, yMax = 0.8f,
                scaleAtBack = 0.8f, scaleAtFront = 0.8f,
            )
            assertEquals(0.8f, flat.scaleForY(0.2f), EPSILON)
            assertEquals(0.8f, flat.scaleForY(0.5f), EPSILON)
            assertEquals(0.8f, flat.scaleForY(0.8f), EPSILON)
        }
    }

    @Nested
    inner class PerSceneTests {

        @Test
        fun `throne room (yMin=0_15 yMax=0_85 back=0_55)`() {
            val bounds = DepthBounds(
                yMin = 0.15f, yMax = 0.85f,
                scaleAtBack = 0.55f, scaleAtFront = 1.0f,
                curve = EasingCurve.EASE_IN_QUAD,
            )
            assertEquals(0.55f, bounds.scaleForY(0.15f), EPSILON)
            assertEquals(0.6625f, bounds.scaleForY(0.5f), EPSILON)
            assertEquals(1.0f, bounds.scaleForY(0.85f), EPSILON)
        }

        @Test
        fun `corridor (yMin=0_25 yMax=0_75 back=0_70)`() {
            val bounds = DepthBounds(
                yMin = 0.25f, yMax = 0.75f,
                scaleAtBack = 0.70f, scaleAtFront = 1.0f,
                curve = EasingCurve.EASE_IN_QUAD,
            )
            assertEquals(0.70f, bounds.scaleForY(0.25f), EPSILON)
            // t = (0.5 - 0.25) / 0.5 = 0.5, eased = 0.25, scale = 0.70 + 0.30 × 0.25 = 0.775
            assertEquals(0.775f, bounds.scaleForY(0.5f), EPSILON)
            assertEquals(1.0f, bounds.scaleForY(0.75f), EPSILON)
        }

        @Test
        fun `courtyard (yMin=0_10 yMax=0_90 back=0_50)`() {
            val bounds = DepthBounds(
                yMin = 0.10f, yMax = 0.90f,
                scaleAtBack = 0.50f, scaleAtFront = 1.0f,
                curve = EasingCurve.EASE_IN_QUAD,
            )
            assertEquals(0.50f, bounds.scaleForY(0.10f), EPSILON)
            // t = (0.5 - 0.10) / 0.8 = 0.5, eased = 0.25, scale = 0.50 + 0.50 × 0.25 = 0.625
            assertEquals(0.625f, bounds.scaleForY(0.5f), EPSILON)
            assertEquals(1.0f, bounds.scaleForY(0.90f), EPSILON)
        }
    }

    @Nested
    inner class ExtremeBoundaryTests {

        @Test
        fun `far below yMin returns scaleAtBack`() {
            val bounds = DepthBounds(
                yMin = 0.3f, yMax = 0.7f,
                scaleAtBack = 0.6f, scaleAtFront = 1.0f,
                curve = EasingCurve.LINEAR,
            )
            assertEquals(0.6f, bounds.scaleForY(-10f), EPSILON)
        }

        @Test
        fun `far above yMax returns scaleAtFront`() {
            val bounds = DepthBounds(
                yMin = 0.3f, yMax = 0.7f,
                scaleAtBack = 0.6f, scaleAtFront = 1.0f,
                curve = EasingCurve.LINEAR,
            )
            assertEquals(1.0f, bounds.scaleForY(10f), EPSILON)
        }
    }
}
