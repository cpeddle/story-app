package io.storyapp.feature.scene.prototype

import android.graphics.BitmapFactory
import android.graphics.Paint
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.storyapp.core.model.depth.DepthBounds
import io.storyapp.core.model.depth.EasingCurve
import io.storyapp.domain.depth.scaleForY
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.hypot
import kotlin.math.roundToInt

private data class ProtoEntity(
    val id: String,
    val x: Float,
    val y: Float,
    val color: Color,
)

private const val ENTITY_RADIUS_DP = 28f
private const val HIT_RADIUS_DP = 28f
private const val DEPTH_MARGIN = 0.02f

private enum class ScenePreset(
    val label: String,
    val assetPath: String,
    val defaultYMin: Float,
    val defaultYMax: Float,
    val defaultScaleAtBack: Float,
    val defaultScaleAtFront: Float,
) {
    THRONE_ROOM("Throne Room", "scenes/throne-room-v1.jpg", 0.15f, 0.85f, 0.55f, 1.0f),
    CORRIDOR("Corridor", "scenes/corridor-v1.jpg", 0.25f, 0.75f, 0.70f, 1.0f),
    OUTDOOR("Outdoor", "scenes/carriage-scene-v1.jpg", 0.10f, 0.90f, 0.50f, 1.0f),
}

private val CURVES = listOf(
    EasingCurve.LINEAR to "LINEAR",
    EasingCurve.EASE_IN_QUAD to "QUAD",
    EasingCurve.EASE_IN_CUBIC to "CUBIC",
)

@Composable
fun DepthScalingPrototype(modifier: Modifier = Modifier) {
    var selectedScene by remember { mutableStateOf(ScenePreset.THRONE_ROOM) }
    var selectedCurve by remember { mutableStateOf<EasingCurve>(EasingCurve.EASE_IN_QUAD) }
    var yMin by remember { mutableFloatStateOf(ScenePreset.THRONE_ROOM.defaultYMin) }
    var yMax by remember { mutableFloatStateOf(ScenePreset.THRONE_ROOM.defaultYMax) }
    var scaleAtBack by remember { mutableFloatStateOf(ScenePreset.THRONE_ROOM.defaultScaleAtBack) }
    var scaleAtFront by remember { mutableFloatStateOf(ScenePreset.THRONE_ROOM.defaultScaleAtFront) }

    val entities = remember {
        mutableStateListOf(
            ProtoEntity("e1", x = 0.3f, y = 0.20f, color = Color.Red),
            ProtoEntity("e2", x = 0.5f, y = 0.35f, color = Color.Green),
            ProtoEntity("e3", x = 0.4f, y = 0.50f, color = Color.Blue),
            ProtoEntity("e4", x = 0.6f, y = 0.65f, color = Color(0xFFFF8800)),
            ProtoEntity("e5", x = 0.5f, y = 0.80f, color = Color.Magenta),
        )
    }

    var draggedId by remember { mutableStateOf<String?>(null) }
    var lastFrameNanos by remember { mutableLongStateOf(System.nanoTime()) }
    var frameTimeMs by remember { mutableLongStateOf(0L) }

    val context = LocalContext.current
    val backgroundImage by produceState<ImageBitmap?>(null, selectedScene) {
        value = withContext(Dispatchers.IO) {
            runCatching {
                context.assets.open(selectedScene.assetPath).use { stream ->
                    BitmapFactory.decodeStream(stream)?.asImageBitmap()
                }
            }.getOrNull()
        }
    }

    val density = LocalDensity.current
    val hitRadiusPx = with(density) { HIT_RADIUS_DP.dp.toPx() }
    val entityRadiusPx = with(density) { ENTITY_RADIUS_DP.dp.toPx() }

    fun applyPreset(preset: ScenePreset) {
        selectedScene = preset
        yMin = preset.defaultYMin
        yMax = preset.defaultYMax
        scaleAtBack = preset.defaultScaleAtBack
        scaleAtFront = preset.defaultScaleAtFront
    }

    val depthBounds = DepthBounds(yMin, yMax, scaleAtBack, scaleAtFront, selectedCurve)

    Row(modifier = modifier.fillMaxSize()) {
        Canvas(
            modifier = Modifier
                .weight(7f)
                .fillMaxHeight()
                .pointerInput(Unit) {
                    detectDragGestures(
                        onDragStart = { offset ->
                            draggedId = entities
                                .sortedByDescending { it.y }
                                .firstOrNull { entity ->
                                    val cx = entity.x * size.width
                                    val cy = entity.y * size.height
                                    hypot(offset.x - cx, offset.y - cy) <= hitRadiusPx
                                }?.id
                            lastFrameNanos = System.nanoTime()
                        },
                        onDrag = { _, dragAmount ->
                            val id = draggedId ?: return@detectDragGestures
                            val idx = entities.indexOfFirst { it.id == id }
                            if (idx >= 0) {
                                val e = entities[idx]
                                entities[idx] = e.copy(
                                    x = (e.x + dragAmount.x / size.width).coerceIn(0f, 1f),
                                    y = (e.y + dragAmount.y / size.height).coerceIn(0f, 1f),
                                )
                            }
                            val now = System.nanoTime()
                            frameTimeMs = (now - lastFrameNanos) / 1_000_000
                            lastFrameNanos = now
                        },
                        onDragEnd = { draggedId = null },
                    )
                },
        ) {
            val bgImage = backgroundImage
            if (bgImage != null) {
                drawBackgroundCenterCrop(bgImage)
            } else {
                drawFloorPlaneLines()
            }
            drawDepthZoneBands(depthBounds)
            drawEntities(entities, depthBounds, draggedId, entityRadiusPx)
            val curveLabel = CURVES.firstOrNull { it.first == selectedCurve }?.second ?: "?"
            drawCanvasDebugOverlay(selectedScene.label, curveLabel, frameTimeMs)
        }

        Column(
            modifier = Modifier
                .weight(3f)
                .fillMaxHeight()
                .verticalScroll(rememberScrollState())
                .padding(12.dp),
        ) {
            Text("Scene", fontSize = 14.sp, color = Color.Gray)
            Row(modifier = Modifier.fillMaxWidth()) {
                ScenePreset.entries.forEach { preset ->
                    FilterChip(
                        selected = selectedScene == preset,
                        onClick = { applyPreset(preset) },
                        label = { Text(preset.label, fontSize = 12.sp) },
                        modifier = Modifier.padding(end = 4.dp),
                    )
                }
            }

            Spacer(Modifier.height(8.dp))

            Text("Curve", fontSize = 14.sp, color = Color.Gray)
            Row(modifier = Modifier.fillMaxWidth()) {
                CURVES.forEach { (curve, label) ->
                    FilterChip(
                        selected = selectedCurve == curve,
                        onClick = { selectedCurve = curve },
                        label = { Text(label, fontSize = 12.sp) },
                        modifier = Modifier.padding(end = 4.dp),
                    )
                }
            }

            Spacer(Modifier.height(8.dp))
            HorizontalDivider()
            Spacer(Modifier.height(8.dp))

            Text("yMin: %.2f".format(yMin), fontSize = 13.sp)
            Slider(
                value = yMin,
                onValueChange = { yMin = it.coerceAtMost(yMax - DEPTH_MARGIN) },
                valueRange = 0.01f..0.99f,
            )

            Text("yMax: %.2f".format(yMax), fontSize = 13.sp)
            Slider(
                value = yMax,
                onValueChange = { yMax = it.coerceAtLeast(yMin + DEPTH_MARGIN) },
                valueRange = 0.01f..0.99f,
            )

            Text("scaleAtBack: %.2f".format(scaleAtBack), fontSize = 13.sp)
            Slider(
                value = scaleAtBack,
                onValueChange = { scaleAtBack = it.coerceAtMost(scaleAtFront) },
                valueRange = 0.10f..1.50f,
            )

            Text("scaleAtFront: %.2f".format(scaleAtFront), fontSize = 13.sp)
            Slider(
                value = scaleAtFront,
                onValueChange = { scaleAtFront = it.coerceAtLeast(scaleAtBack) },
                valueRange = 0.10f..1.50f,
            )

            TextButton(onClick = { applyPreset(selectedScene) }) {
                Text("Reset to Defaults")
            }

            Spacer(Modifier.height(8.dp))
            HorizontalDivider()
            Spacer(Modifier.height(8.dp))

            Text("Entities", fontSize = 14.sp, color = Color.Gray)
            entities.forEach { entity ->
                val scale = depthBounds.scaleForY(entity.y)
                val prefix = if (entity.id == draggedId) "▶ " else "  "
                Text(
                    "${prefix}${entity.id}: Y=%.2f scale=%.3f".format(entity.y, scale),
                    fontSize = 12.sp,
                    fontFamily = FontFamily.Monospace,
                )
            }

            Spacer(Modifier.height(8.dp))
            HorizontalDivider()
            Spacer(Modifier.height(8.dp))

            Text("Export", fontSize = 14.sp, color = Color.Gray)
            val curveExport = when (selectedCurve) {
                is EasingCurve.LINEAR -> "EasingCurve.LINEAR"
                is EasingCurve.EASE_IN_QUAD -> "EasingCurve.EASE_IN_QUAD"
                is EasingCurve.EASE_IN_CUBIC -> "EasingCurve.EASE_IN_CUBIC"
            }
            Text(
                buildString {
                    appendLine("// ${selectedScene.label}")
                    appendLine("DepthBounds(")
                    appendLine("    yMin = %.2ff, yMax = %.2ff,".format(yMin, yMax))
                    appendLine("    scaleAtBack = %.2ff, scaleAtFront = %.2ff,".format(scaleAtBack, scaleAtFront))
                    appendLine("    curve = $curveExport,")
                    append(")")
                },
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                lineHeight = 16.sp,
            )
        }
    }
}

private fun DrawScope.drawBackgroundCenterCrop(image: ImageBitmap) {
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

private fun DrawScope.drawFloorPlaneLines() {
    val lineColor = Color(0xFFCCCCCC)
    listOf(0.2f, 0.5f, 0.8f).forEach { ny ->
        val y = ny * size.height
        drawLine(lineColor, Offset(0f, y), Offset(size.width, y), strokeWidth = 2f)
    }
}

private fun DrawScope.drawDepthZoneBands(depthBounds: DepthBounds) {
    val yMinPx = depthBounds.yMin * size.height
    val yMaxPx = depthBounds.yMax * size.height
    val deadZoneColor = Color.Red.copy(alpha = 0.15f)

    drawRect(deadZoneColor, Offset.Zero, Size(size.width, yMinPx))
    drawRect(deadZoneColor, Offset(0f, yMaxPx), Size(size.width, size.height - yMaxPx))

    drawLine(Color.Yellow, Offset(0f, yMinPx), Offset(size.width, yMinPx), strokeWidth = 3f)
    drawLine(Color.Yellow, Offset(0f, yMaxPx), Offset(size.width, yMaxPx), strokeWidth = 3f)

    val labelPaint = Paint().apply {
        color = android.graphics.Color.YELLOW
        textSize = 24f
        isAntiAlias = true
        setShadowLayer(3f, 0f, 0f, android.graphics.Color.BLACK)
    }
    drawContext.canvas.nativeCanvas.drawText(
        "yMin = %.2f".format(depthBounds.yMin), 8f, yMinPx + 18f, labelPaint,
    )
    drawContext.canvas.nativeCanvas.drawText(
        "yMax = %.2f".format(depthBounds.yMax), 8f, yMaxPx - 8f, labelPaint,
    )
}

private fun DrawScope.drawEntities(
    entities: List<ProtoEntity>,
    depthBounds: DepthBounds,
    draggedId: String?,
    radiusPx: Float,
) {
    val nonDragged = entities.filter { it.id != draggedId }.sortedBy { it.y }
    val dragged = entities.find { it.id == draggedId }

    nonDragged.forEach { drawEntity(it, depthBounds, radiusPx) }
    dragged?.let { drawEntity(it, depthBounds, radiusPx) }
}

private fun DrawScope.drawEntity(
    entity: ProtoEntity,
    depthBounds: DepthBounds,
    radiusPx: Float,
) {
    val scale = depthBounds.scaleForY(entity.y)
    val cx = entity.x * size.width
    val cy = entity.y * size.height

    withTransform({
        translate(left = cx, top = cy)
        scale(scaleX = scale, scaleY = scale, pivot = Offset.Zero)
    }) {
        drawCircle(entity.color, radiusPx, Offset.Zero)
        drawCircle(Color.Black, radiusPx, Offset.Zero, style = Stroke(3f))
    }
}

private fun DrawScope.drawCanvasDebugOverlay(
    sceneName: String,
    curveLabel: String,
    frameTimeMs: Long,
) {
    val lineHeight = 30f
    val overlayHeight = lineHeight * 3 + 16f

    drawRect(
        color = Color.Black.copy(alpha = 0.5f),
        topLeft = Offset.Zero,
        size = Size(280f, overlayHeight),
    )

    val paint = Paint().apply {
        color = android.graphics.Color.WHITE
        textSize = 24f
        isAntiAlias = true
    }

    var y = 28f
    drawContext.canvas.nativeCanvas.drawText("Scene: $sceneName", 10f, y, paint)
    y += lineHeight
    drawContext.canvas.nativeCanvas.drawText("Curve: $curveLabel", 10f, y, paint)
    y += lineHeight
    drawContext.canvas.nativeCanvas.drawText("Frame: ${frameTimeMs}ms", 10f, y, paint)
}
