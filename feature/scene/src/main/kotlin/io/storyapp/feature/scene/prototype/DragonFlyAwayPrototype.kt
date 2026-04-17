package io.storyapp.feature.scene.prototype

import android.graphics.BitmapFactory
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.roundToInt

private enum class DragonState { IDLE, WINGS_SPREAD, FLYING_AWAY, GONE }

@Composable
fun DragonFlyAwayPrototype(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    // --- sprite loading ---
    val idleSprite by produceState<ImageBitmap?>(null) {
        value = withContext(Dispatchers.IO) {
            runCatching {
                context.assets.open("characters/dragon/dragon-full-v4.png").use { stream ->
                    BitmapFactory.decodeStream(stream)?.asImageBitmap()
                }
            }.getOrNull()
        }
    }
    val wingsSprite by produceState<ImageBitmap?>(null) {
        value = withContext(Dispatchers.IO) {
            runCatching {
                context.assets.open("characters/dragon/dragon-wings-spread-v3.png").use { stream ->
                    BitmapFactory.decodeStream(stream)?.asImageBitmap()
                }
            }.getOrNull()
        }
    }

    // --- scene background ---
    val sceneSprite by produceState<ImageBitmap?>(null) {
        value = withContext(Dispatchers.IO) {
            runCatching {
                context.assets.open("scenes/throne-room-v1.jpg").use { stream ->
                    BitmapFactory.decodeStream(stream)?.asImageBitmap()
                }
            }.getOrNull()
        }
    }

    // --- story state ---
    var dragonState by remember { mutableStateOf(DragonState.IDLE) }

    // Animation values — reset each time the story element starts
    val flyOffsetX = remember { Animatable(0f) }
    val flyOffsetY = remember { Animatable(0f) }
    val flyScale = remember { Animatable(1f) }
    val flyAlpha = remember { Animatable(1f) }

    fun resetAnimation() {
        scope.launch {
            flyOffsetX.snapTo(0f)
            flyOffsetY.snapTo(0f)
            flyScale.snapTo(1f)
            flyAlpha.snapTo(1f)
            dragonState = DragonState.IDLE
        }
    }

    // Launch fly-away animation when state transitions to FLYING_AWAY
    LaunchedEffect(dragonState) {
        if (dragonState != DragonState.FLYING_AWAY) return@LaunchedEffect
        // Phase 1: rise up slowly (dragon gains lift, 600ms)
        launch { flyOffsetY.animateTo(-0.12f, tween(600, easing = LinearEasing)) }
        launch { flyOffsetX.animateTo(0.04f, tween(600, easing = LinearEasing)) }
        kotlinx.coroutines.delay(600)
        // Phase 2: shoot off into the sky (1 400ms), shrink and fade
        launch { flyOffsetY.animateTo(-1.1f, tween(1400, easing = LinearEasing)) }
        launch { flyOffsetX.animateTo(0.20f, tween(1400, easing = LinearEasing)) }
        launch { flyScale.animateTo(0.15f, tween(1400, easing = LinearEasing)) }
        launch { flyAlpha.animateTo(0f, tween(1200, easing = LinearEasing)) }
        kotlinx.coroutines.delay(1400)
        dragonState = DragonState.GONE
    }

    // --- layout: canvas left, controls right ---
    Row(modifier = modifier.fillMaxSize()) {
        Canvas(
            modifier = Modifier
                .weight(7f)
                .fillMaxHeight(),
        ) {
            // Background
            val bg = sceneSprite
            if (bg != null) {
                drawBackgroundFill(bg)
            } else {
                drawRect(Color(0xFF8B7355), size = size)
            }

            if (dragonState == DragonState.GONE) return@Canvas

            // Determine which sprite to draw
            val sprite = when (dragonState) {
                DragonState.IDLE -> idleSprite
                else -> wingsSprite ?: idleSprite
            }
            sprite ?: return@Canvas

            // Dragon rests at bottom-centre of scene, scaled to ~28% of canvas height
            val baseScale = size.height * 0.28f / sprite.height.toFloat()
            val spriteW = sprite.width * baseScale
            val spriteH = sprite.height * baseScale

            // Normalised offsets → pixel offsets (relative to canvas)
            val offsetPxX = flyOffsetX.value * size.width
            val offsetPxY = flyOffsetY.value * size.height

            val anchorX = size.width * 0.50f - spriteW / 2f + offsetPxX
            val anchorY = size.height * 0.62f - spriteH + offsetPxY

            val totalScale = baseScale * flyScale.value
            withTransform({
                translate(anchorX + spriteW / 2f, anchorY + spriteH / 2f)
                scale(scaleX = totalScale, scaleY = totalScale)
            }) {
                drawImage(
                    image = sprite,
                    srcOffset = IntOffset.Zero,
                    srcSize = IntSize(sprite.width, sprite.height),
                    dstOffset = IntOffset((-sprite.width / 2), (-sprite.height / 2)),
                    dstSize = IntSize(sprite.width, sprite.height),
                    alpha = flyAlpha.value,
                )
            }
        }

        // --- Control panel ---
        Column(
            modifier = Modifier
                .weight(3f)
                .fillMaxHeight()
                .padding(16.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("Dragon Story", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            Text(
                text = when (dragonState) {
                    DragonState.IDLE -> "The dragon is resting."
                    DragonState.WINGS_SPREAD -> "The dragon spreads its wings!"
                    DragonState.FLYING_AWAY -> "The dragon soars away!"
                    DragonState.GONE -> "The dragon has flown away…"
                },
                fontSize = 14.sp,
                color = Color.DarkGray,
            )
            Spacer(Modifier.height(24.dp))

            when (dragonState) {
                DragonState.IDLE -> Button(
                    onClick = { dragonState = DragonState.WINGS_SPREAD },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Spread Wings")
                }
                DragonState.WINGS_SPREAD -> Button(
                    onClick = { dragonState = DragonState.FLYING_AWAY },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Fly Away!")
                }
                DragonState.FLYING_AWAY -> Text(
                    "✈ Flying…",
                    color = Color.Gray,
                    fontSize = 14.sp,
                )
                DragonState.GONE -> {
                    Text("🐉 Gone!", fontSize = 14.sp, color = Color(0xFFB71C1C))
                    Spacer(Modifier.height(16.dp))
                    TextButton(onClick = { resetAnimation() }) {
                        Text("Replay")
                    }
                }
            }
        }
    }
}

// Fills the canvas with the image, centre-cropped (matches DepthScalePrototype behaviour)
private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawBackgroundFill(image: ImageBitmap) {
    val canvasAspect = size.width / size.height
    val imageAspect = image.width.toFloat() / image.height.toFloat()
    val srcOffset: IntOffset
    val srcSize: IntSize
    if (imageAspect > canvasAspect) {
        val scaledWidth = (image.height * canvasAspect).roundToInt()
        srcOffset = IntOffset((image.width - scaledWidth) / 2, 0)
        srcSize = IntSize(scaledWidth, image.height)
    } else {
        val scaledHeight = (image.width / canvasAspect).roundToInt()
        srcOffset = IntOffset(0, (image.height - scaledHeight) / 2)
        srcSize = IntSize(image.width, scaledHeight)
    }
    drawImage(
        image = image,
        srcOffset = srcOffset,
        srcSize = srcSize,
        dstSize = IntSize(size.width.roundToInt(), size.height.roundToInt()),
    )
}
