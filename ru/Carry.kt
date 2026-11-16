package io.github.artcraftandroid.procraft.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.github.artcraftandroid.procraft.canvas.CanvasViewModel
import io.github.artcraftandroid.procraft.canvas.Screen
import io.github.artcraftandroid.procraft.i18n.Text

/**
 * Taking a layer along to another artwork: a layer held down (until it can be dragged) is taken
 * by a second finger touching the screen. The held finger can then stay down, or lift: the layer
 * is in hand until it is pasted, in whichever artwork is opened next.
 */
object LayerCarry {
    private var carry: (() -> Unit)? = null

    /** A layer is held: what to do if a second finger comes down. */
    fun hold(action: () -> Unit) {
        carry = action
    }

    /** The layer is let go (or the touch is over). */
    fun release() {
        carry = null
    }

    /** A second finger came down: the held layer, if there is one, is taken along. */
    fun secondFinger() {
        val action = carry ?: return
        carry = null
        action()
    }
}

/** The app, with the "in hand" plate over it. */
@Composable
fun AppWithCarry(vm: CanvasViewModel) {
    Box(Modifier.fillMaxSize()) {
        AppRoot(vm)
        CarryPlate(vm)
    }
}

/** What is in hand: "Paste here" in an artwork, a reminder in the gallery, and a cross to put it down. */
@Composable
private fun CarryPlate(vm: CanvasViewModel) {
    if (!vm.carrying) return
    val inArtwork = vm.screen == Screen.CANVAS
    Box(Modifier.fillMaxSize()) {
        Row(
            Modifier.align(Alignment.BottomCenter).padding(bottom = 28.dp).clip(CircleShape).background(Pc.Accent),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier.then(if (inArtwork) Modifier.clickable { vm.paste() } else Modifier).padding(start = 22.dp, end = 12.dp, top = 12.dp, bottom = 12.dp),
            ) {
                Text(
                    if (inArtwork) "Paste here" else "In hand: open an artwork to paste it",
                    color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold,
                )
            }
            Box(Modifier.clickable { vm.endCarry() }.padding(start = 10.dp, end = 20.dp, top = 12.dp, bottom = 12.dp)) {
                androidx.compose.material3.Text("\u2715", color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}
