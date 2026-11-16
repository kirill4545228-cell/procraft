package io.github.artcraftandroid.procraft.ui

import android.content.Context
import android.os.SystemClock
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import io.github.artcraftandroid.procraft.i18n.Text
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.ceil
import kotlin.math.sin
import kotlinx.coroutines.delay

/** Whether the New Year decorations show; kept between runs. */
object NewYear {
    var enabled by mutableStateOf(true)
        private set
    private var loaded = false

    fun init(context: Context) {
        if (loaded) return
        loaded = true
        enabled = runCatching {
            context.applicationContext.getSharedPreferences("newyear", Context.MODE_PRIVATE).getBoolean("on", true)
        }.getOrDefault(true)
    }

    fun set(context: Context, on: Boolean) {
        init(context)
        enabled = on
        runCatching {
            context.applicationContext.getSharedPreferences("newyear", Context.MODE_PRIVATE).edit().putBoolean("on", on).apply()
        }
    }
}

private val NyWire = Color(0xFF2F4A2F)
private val NyColors = listOf(
    Color(0xFFFF4A4A), Color(0xFFFFC83D), Color(0xFF47D16C), Color(0xFF4DA3FF), Color(0xFFE056FD),
)

private fun nyFrac(v: Float): Float = v - kotlin.math.floor(v)

/**
 * Draws the garland and the snow over what it is put on. It only draws: touches go through it.
 * One turn of its clock is 60 seconds, and everything moves in whole turns of it, so it never jumps.
 */
fun Modifier.newYear(): Modifier = composed {
    val context = LocalContext.current
    NewYear.init(context)
    val clock by rememberInfiniteTransition(label = "newYear").animateFloat(
        initialValue = 0f,
        targetValue = 60f,
        animationSpec = infiniteRepeatable(tween(60000, easing = LinearEasing)),
        label = "clock",
    )
    drawWithContent {
        drawContent()
        if (NewYear.enabled) drawFestive(clock)
    }
}

private fun DrawScope.drawFestive(clock: Float) {
    val w = size.width
    val h = size.height
    val dp = 1.dp.toPx()
    // the garland: swags hung along the top edge, small and quiet
    val seg = 150f * dp
    val sag = 9f * dp
    val swags = ceil(w / seg).toInt() + 1
    var index = 0
    for (k in 0 until swags) {
        val x0 = k * seg
        val x2 = x0 + seg
        val cx = x0 + seg / 2
        val y0 = -2f * dp
        val cy = y0 + sag * 2
        fun at(t: Float): Offset {
            val u = 1 - t
            return Offset(u * u * x0 + 2 * u * t * cx + t * t * x2, u * u * y0 + 2 * u * t * cy + t * t * y0)
        }
        val wire = Path()
        wire.moveTo(x0, y0)
        for (s in 1..24) {
            val p = at(s / 24f)
            wire.lineTo(p.x, p.y)
        }
        drawPath(wire, NyWire.copy(alpha = 0.9f), style = Stroke(width = 1.4f * dp))
        for (j in 0 until 5) {
            val p = at((j + 0.5f) / 5f)
            val bulb = Offset(p.x, p.y + 6.5f * dp)
            val color = NyColors[index % NyColors.size]
            val glow = 0.5f + 0.5f * sin((2.0 * PI * (clock * 0.5f + index * 0.23f)).toFloat())
            drawLine(NyWire, p, Offset(p.x, p.y + 3f * dp), strokeWidth = 1.2f * dp)
            drawCircle(
                brush = Brush.radialGradient(listOf(color.copy(alpha = 0.55f * glow), Color.Transparent), center = bulb, radius = 13f * dp),
                radius = 13f * dp,
                center = bulb,
            )
            drawCircle(color.copy(alpha = 0.45f + 0.5f * glow), radius = 3.2f * dp, center = bulb)
            index++
        }
    }
    // a little snow, now and then, drifting down from the top and gone before the middle
    val periods = floatArrayOf(10f, 12f, 15f, 20f, 30f, 12f, 20f)
    for (i in 0 until 26) {
        val p = periods[i % periods.size]
        val phase = nyFrac(i * 0.618034f)
        val fall = nyFrac(clock / p + phase)
        val y = fall * (h * 0.62f)
        val x = nyFrac(i * 0.754878f) * w + sin((2.0 * PI * (clock / 6f + phase * 3f)).toFloat()) * 14f * dp
        val fade = (1f - fall).coerceIn(0f, 1f) * (0.35f + 0.5f * nyFrac(i * 0.37f))
        val r = (1.3f + 1.4f * nyFrac(i * 0.91f)) * dp
        drawCircle(Color(0xFF8FA6C8).copy(alpha = fade * 0.5f), radius = r + 0.6f * dp, center = Offset(x, y))
        drawCircle(Color.White.copy(alpha = fade), radius = r, center = Offset(x, y))
    }
}

/**
 * The snowflake button that switches the decorations on and off. Five quick taps in a row show
 * a small surprise instead.
 */
@Composable
fun NewYearButton() {
    val context = LocalContext.current
    NewYear.init(context)
    var taps by remember { mutableIntStateOf(0) }
    var last by remember { mutableLongStateOf(0L) }
    var egg by remember { mutableStateOf(false) }
    val on = NewYear.enabled
    val ink = Pc.GalleryText
    Box(
        Modifier.padding(end = 12.dp).size(45.dp).clip(CircleShape).background(Pc.Capsule).border(1.dp, Pc.CapsuleEdge, CircleShape)
            .clickable {
                val now = SystemClock.uptimeMillis()
                taps = if (now - last < 2000) taps + 1 else 1
                last = now
                if (taps >= 5) {
                    taps = 0
                    NewYear.set(context, true)
                    egg = true
                } else {
                    NewYear.set(context, !NewYear.enabled)
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.size(22.dp)) {
            val c = center
            val r = size.minDimension / 2
            val color = ink.copy(alpha = if (on) 1f else 0.4f)
            for (a in 0 until 3) {
                val ang = (a * PI / 3).toFloat()
                val d = Offset(cos(ang) * r, sin(ang) * r)
                drawLine(color, c - d, c + d, strokeWidth = 1.8f * density, cap = StrokeCap.Round)
            }
            for (a in 0 until 6) {
                val ang = (a * PI / 3).toFloat()
                val tip = Offset(c.x + cos(ang) * r * 0.62f, c.y + sin(ang) * r * 0.62f)
                for (side in listOf(-1f, 1f)) {
                    val b = ang + side * 0.75f
                    drawLine(color, tip, Offset(tip.x + cos(b) * r * 0.3f, tip.y + sin(b) * r * 0.3f), strokeWidth = 1.4f * density, cap = StrokeCap.Round)
                }
            }
        }
    }
    if (egg) {
        Dialog(onDismissRequest = { egg = false }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
            NewYearEgg { egg = false }
        }
    }
}

private val NyGold = Color(0xFFFFD54F)
private val NyConfetti = listOf(
    Color(0xFFFF4A4A), Color(0xFFFFC83D), Color(0xFF47D16C), Color(0xFF4DA3FF), Color(0xFFE056FD), Color(0xFFFFFFFF),
)

@Composable
private fun NewYearEgg(onClose: () -> Unit) {
    val clock by rememberInfiniteTransition(label = "egg").animateFloat(
        initialValue = 0f,
        targetValue = 10f,
        animationSpec = infiniteRepeatable(tween(10000, easing = LinearEasing)),
        label = "clock",
    )
    LaunchedEffect(Unit) {
        delay(9000)
        onClose()
    }
    Box(
        Modifier.fillMaxSize().background(Color(0xE60B0B14))
            .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null, onClick = onClose),
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.fillMaxSize()) { drawConfetti(clock) }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Canvas(Modifier.size(180.dp, 200.dp)) { drawTree(clock) }
            Spacer(Modifier.height(10.dp))
            Text("Happy New Year!", color = Color.White, fontSize = 34.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
            Text("2027", color = NyGold, fontSize = 56.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            Text(
                "May drawing be easy and bright in the new year",
                color = Color(0xFFCCCCDD), fontSize = 17.sp, textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 32.dp),
            )
            Spacer(Modifier.height(26.dp))
            Text("Tap anywhere to close", color = Color(0xFF8888A0), fontSize = 14.sp)
        }
    }
}

private fun DrawScope.drawConfetti(clock: Float) {
    val w = size.width
    val h = size.height
    val dp = 1.dp.toPx()
    val periods = floatArrayOf(5f, 10f, 5f, 10f, 2.5f)
    for (i in 0 until 70) {
        val p = periods[i % periods.size]
        val phase = nyFrac(i * 0.618034f)
        val y = nyFrac(clock / p + phase) * (h + 24f * dp) - 12f * dp
        val x = nyFrac(i * 0.754878f) * w + sin((2.0 * PI * (clock / 2.5f + phase * 4f)).toFloat()) * 18f * dp
        rotate(degrees = (clock * 90f * (1 + i % 3)) % 360f, pivot = Offset(x, y)) {
            drawRect(NyConfetti[i % NyConfetti.size].copy(alpha = 0.9f), topLeft = Offset(x - 3f * dp, y - 5f * dp), size = androidx.compose.ui.geometry.Size(6f * dp, 10f * dp))
        }
    }
}

private fun DrawScope.drawTree(clock: Float) {
    val dp = 1.dp.toPx()
    val cx = size.width / 2
    drawRect(Color(0xFF6B4A2B), topLeft = Offset(cx - 9f * dp, size.height - 28f * dp), size = androidx.compose.ui.geometry.Size(18f * dp, 28f * dp))
    val tiers = listOf(Triple(40f, 68f, Color(0xFF1F8A3B)), Triple(78f, 88f, Color(0xFF26994A)), Triple(118f, 108f, Color(0xFF2AA64A)))
    for ((top, half, color) in tiers) {
        val t = Path()
        t.moveTo(cx, top * dp - 22f * dp)
        t.lineTo(cx - half * dp / 2, top * dp + 50f * dp)
        t.lineTo(cx + half * dp / 2, top * dp + 50f * dp)
        t.close()
        drawPath(t, color)
    }
    // the star
    val star = Path()
    val sc = Offset(cx, 14f * dp)
    for (k in 0 until 10) {
        val a = (-PI / 2 + k * PI / 5).toFloat()
        val rr = if (k % 2 == 0) 13f * dp else 5.5f * dp
        val px = sc.x + cos(a) * rr
        val py = sc.y + sin(a) * rr
        if (k == 0) star.moveTo(px, py) else star.lineTo(px, py)
    }
    star.close()
    drawPath(star, NyGold)
    // ornaments that blink
    val spots = listOf(
        Offset(-14f, 54f), Offset(12f, 66f), Offset(-26f, 96f), Offset(2f, 100f), Offset(28f, 108f),
        Offset(-36f, 140f), Offset(-8f, 138f), Offset(22f, 146f), Offset(40f, 150f),
    )
    for ((n, s) in spots.withIndex()) {
        val b = 0.5f + 0.5f * sin((2.0 * PI * (clock * 0.5f + n * 0.21f)).toFloat())
        val c = Offset(cx + s.x * dp, s.y * dp)
        val color = NyColors[n % NyColors.size]
        drawCircle(Brush.radialGradient(listOf(color.copy(alpha = 0.5f * b), Color.Transparent), center = c, radius = 11f * dp), radius = 11f * dp, center = c)
        drawCircle(color.copy(alpha = 0.55f + 0.45f * b), radius = 4f * dp, center = c)
    }
}
