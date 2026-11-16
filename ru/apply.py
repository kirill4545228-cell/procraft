#!/usr/bin/env python3
"""Puts the Russian interface into a checkout of artcraft-android/procraft (run from the repo root)."""
import glob, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = "android/app/src/main"
PKG = f"{MAIN}/java/io/github/artcraftandroid/procraft"
IMP = "import io.github.artcraftandroid.procraft.i18n.I18n"
warn = []

def read(p): return open(p, encoding="utf8").read()
def write(p, s): open(p, "w", encoding="utf8").write(s)

def add_import(s):
    if IMP + "\n" in s + "\n" and re.search(re.escape(IMP) + r"$", s, re.M): return s
    lines = s.split("\n")
    idx = max(i for i, l in enumerate(lines) if l.startswith("import "))
    lines.insert(idx + 1, IMP)
    return "\n".join(lines)

def edit(rel, fn, need=True):
    p = f"{PKG}/{rel}"
    if not os.path.exists(p):
        warn.append(f"missing file {rel}"); return
    s = read(p); n = fn(s)
    if n == s:
        if need: warn.append(f"nothing changed in {rel}")
        return
    write(p, add_import(n))

def rep(old, new):
    return lambda s: s.replace(old, new, 1)

# 1. the dictionary and the translating Text
os.makedirs(f"{PKG}/i18n", exist_ok=True)
shutil.copy(f"{HERE}/I18n.kt", f"{PKG}/i18n/I18n.kt")
shutil.copy(f"{HERE}/Text.kt", f"{PKG}/i18n/Text.kt")
os.makedirs(f"{MAIN}/assets/i18n", exist_ok=True)
shutil.copy(f"{HERE}/ru.tsv", f"{MAIN}/assets/i18n/ru.tsv")
os.makedirs(f"{MAIN}/res/values-ru", exist_ok=True)
shutil.copy(f"{HERE}/strings-ru.xml", f"{MAIN}/res/values-ru/strings.xml")

# 2. every Material 3 Text becomes the translating one
n = 0
for p in glob.glob(f"{PKG}/**/*.kt", recursive=True):
    if "/i18n/" in p: continue
    s = read(p)
    t = re.sub(r"^import androidx\.compose\.material3\.Text$",
               "import io.github.artcraftandroid.procraft.i18n.Text", s, flags=re.M)
    if t != s: write(p, t); n += 1
print(f"Text swapped in {n} files")

# 3. the other places text is shown
for f in ["MainActivity.kt", "SettingsActivity.kt", "SaveToDeviceActivity.kt"]:
    edit(f, rep("super.onCreate(savedInstanceState)\n", "super.onCreate(savedInstanceState)\n        I18n.init(this)\n"))
edit("SaveToDeviceActivity.kt", rep('"Couldn\'t save the file"', 'I18n.tr("Couldn\'t save the file")'), need=False)
cd = re.compile(r'contentDescription = "([^"$\\]+)"')
for p in glob.glob(f"{PKG}/**/*.kt", recursive=True):
    if "/i18n/" in p: continue
    rel = os.path.relpath(p, PKG)
    edit(rel, lambda s: cd.sub(r'contentDescription = I18n.tr("\1")', s), need=False)
edit("ui/Chrome.kt", rep('append(if (size) "Size" else "Opacity")', 'append(I18n.tr(if (size) "Size" else "Opacity"))'), need=False)
edit("ui/BrushStudio.kt", rep("measurer.measure(label, androidx", "measurer.measure(I18n.tr(label), androidx"), need=False)
edit("ui/AlertUi.kt", lambda s: s.replace("measurer.measure(said, androidx", "measurer.measure(I18n.tr(said), androidx")
     .replace("measurer.measure(title(kept), androidx", "measurer.measure(I18n.tr(title(kept)), androidx"), need=False)
edit("ui/AppRoot.kt", rep('w.joinToString("\\n") },', 'w.joinToString("\\n") { I18n.tr(it) } },'), need=False)
edit("ui/CanvasInfoUi.kt", rep('+ " at " +', '+ I18n.tr(" at ") +'), need=False)

# 4. "Copy Here": copy the selection onto the same layer. The selection is lifted to a layer of its
#    own (what Copy & Paste does), transform opens on it, and keeping the transform merges it back
#    down onto the layer it came from; cancelling removes it.
def copy_here():
    vm_path = f"{PKG}/canvas/CanvasViewModel.kt"
    ui_path = f"{PKG}/ui/SelectionUi.kt"
    if not (os.path.exists(vm_path) and os.path.exists(ui_path)):
        warn.append("Copy Here: files not found"); return
    vm, ui = read(vm_path), read(ui_path)
    end_anchor = "        transformNumeric = null\n        refresh()\n"
    i = vm.find("fun endTransform(commit: Boolean)")
    j = vm.find(end_anchor, i) if i >= 0 else -1
    k = vm.find("    fun copySelectionToLayer() {")
    btn = '        ToolbarButton(PcIcons.SelectCopyPaste, "Copy & Paste", '
    ok = (j > 0 and k > 0 and btn in ui and ui.count("toolbarLayout(screenWidth, 8, SelectionButtonRoomy") == 2
          and "copySelectionToSameLayer" not in vm)
    if not ok:
        warn.append("Copy Here: the code looks different, button not added"); return
    vm = vm[:j] + end_anchor + "        afterTransform?.let { done -> afterTransform = null; done(commit) }\n" + vm[j + len(end_anchor):]
    k = vm.find("    fun copySelectionToLayer() {")
    new_fn = """    /** What to do once transform ends: set by [copySelectionToSameLayer], run once. */
    private var afterTransform: ((Boolean) -> Unit)? = null

    /**
     * Copy onto the same layer: the selection is lifted to a layer of its own to be moved, and kept
     * by merging it back down onto the layer it came from when the transform is kept.
     */
    fun copySelectionToSameLayer() {
        if (transforming) return
        val s = session ?: return
        val id = s.copySelectionToLayer() ?: return
        s.selectNone()
        selectionChanged(fill = false)
        refresh()
        toggleTransform()
        if (transforming) {
            afterTransform = { keep ->
                if (keep) layerChange { it.mergeDown(id) } else layerChange { it.deleteLayer(id) }
            }
        } else {
            layerChange { it.deleteLayer(id) }
        }
    }

"""
    vm = vm[:k] + new_fn + vm[k:]
    ui = ui.replace("toolbarLayout(screenWidth, 8, SelectionButtonRoomy", "toolbarLayout(screenWidth, 9, SelectionButtonRoomy")
    line = ui[ui.find(btn):].split("\n", 1)[0]
    here = '        ToolbarButton(PcIcons.SelectCopyPaste, "Copy Here", enabled = has || drawing, width = w, iconSize = 44.dp, labelSize = long) { vm.copySelectionToSameLayer() }\n'
    ui = ui.replace(line + "\n", line + "\n" + here, 1)
    write(vm_path, vm); write(ui_path, ui)
    print("Copy Here added")

copy_here()

# 5. Animation bar: previous / next frame and an onion skin switch, next to Play.
def animation_bar():
    vm_path = f"{PKG}/canvas/CanvasViewModel.kt"
    ui_path = f"{PKG}/ui/AnimationUi.kt"
    if not (os.path.exists(vm_path) and os.path.exists(ui_path)):
        warn.append("Animation bar: files not found"); return
    vm, ui = read(vm_path), read(ui_path)
    step = "    private fun stepFrame(by: Int) {"
    anchor = "                    Spacer(Modifier.weight(1f))\n                    if (!pages) BarText(\n"
    if not (step in vm and anchor in ui and "private fun toggleOnionSkin()" in vm and "barPreviousFrame" not in vm):
        warn.append("Animation bar: the code looks different, buttons not added"); return
    funcs = """    /** The animation bar's previous and next frame, and its onion skin switch. */
    fun barPreviousFrame() = stepFrame(-1)

    fun barNextFrame() = stepFrame(1)

    fun barToggleOnionSkin() = toggleOnionSkin()

"""
    vm = vm.replace("    /** Animation Assist's next or previous frame drawn on", funcs + "    /** Animation Assist's next or previous frame drawn on", 1) if "    /** Animation Assist's next or previous frame drawn on" in vm else vm.replace(step, funcs + step, 1)
    row = """                    if (!pages) {
                        Spacer(Modifier.width(14.dp))
                        BarText("\u2039", Modifier.width(30.dp)) { vm.barPreviousFrame() }
                        BarText("\u203A", Modifier.width(30.dp)) { vm.barNextFrame() }
                        Spacer(Modifier.width(8.dp))
                        BarText("Onion", Modifier) { vm.barToggleOnionSkin() }
                    }
"""
    ui = ui.replace(anchor, row + anchor, 1)
    write(vm_path, vm); write(ui_path, ui)
    print("Animation bar buttons added")

animation_bar()

# 6. Frame options: Clear Frame, First Frame and Last Frame.
def frame_options():
    vm_path = f"{PKG}/canvas/CanvasViewModel.kt"
    ui_path = f"{PKG}/ui/AnimationUi.kt"
    if not (os.path.exists(vm_path) and os.path.exists(ui_path)):
        warn.append("Frame options: files not found"); return
    vm, ui = read(vm_path), read(ui_path)
    doc = "    /** Animation Assist's next or previous frame drawn on"
    anchor = "        // a plugin's in-betweens: a frame drawn between this one and the next\n"
    if not (doc in vm and anchor in ui and "fun clearCurrentLayer()" in vm and "barFirstFrame" not in vm):
        warn.append("Frame options: the code looks different, rows not added"); return
    funcs = """    /** The first and the last frame of the animation. */
    fun barFirstFrame() = stepFrame(-1_000_000)

    fun barLastFrame() = stepFrame(1_000_000)

"""
    vm = vm.replace(doc, funcs + doc, 1)
    def row(label, call):
        return ("        RowLine()\n"
                "        Row(Modifier.fillMaxWidth().height(44.dp).clickable { " + call + " }.padding(start = 16.dp), verticalAlignment = Alignment.CenterVertically) {\n"
                "            Text(\"" + label + "\", color = Pc.PanelTitle, fontSize = 17.sp)\n"
                "        }\n")
    rows = ("        if (!a.pages) {\n"
            + row("Clear Frame", "vm.clearCurrentLayer()")
            + row("First Frame", "vm.barFirstFrame()")
            + row("Last Frame", "vm.barLastFrame()")
            + "        }\n")
    ui = ui.replace(anchor, rows + anchor, 1)
    write(vm_path, vm); write(ui_path, ui)
    print("Frame options rows added")

frame_options()

# 7. Frames made of several layers. In Animation Assist each top-level layer or group is a frame;
#    a layer added inside a group is not. "Add Layer" (frame options) puts a new layer inside the
#    current frame (a frame that is a single layer is made a group first), and "Frames hold layers"
#    (settings) makes Add Frame start a group, so layers can be added into it right away.
def frames_with_layers():
    vm_path = f"{PKG}/canvas/CanvasViewModel.kt"
    ui_path = f"{PKG}/ui/AnimationUi.kt"
    if not (os.path.exists(vm_path) and os.path.exists(ui_path)):
        warn.append("Frames with layers: files not found"); return
    vm, ui = read(vm_path), read(ui_path)
    old_add = "        layerChange { if (it.addFrame() == 0uL) message = noRoom() }\n"
    head = "    fun addFrame() {\n"
    toggle = '        ToggleRow("Blend primary frame", a.blendPrimary, 44.5.dp) { vm.changeAnimation { it.copy(blendPrimary = !it.blendPrimary) } }\n        RowLine()\n'
    anchor = "        // a plugin's in-betweens: a frame drawn between this one and the next\n"
    if not (old_add in vm and head in vm and toggle in ui and anchor in ui and "framesAsGroups" not in vm):
        warn.append("Frames with layers: the code looks different, nothing added"); return
    new_add = """        layerChange {
            val id = it.addFrame()
            if (id == 0uL) {
                message = noRoom()
            } else if (framesAsGroups && animation?.pages != true) {
                // the new frame becomes a group, so layers can be added inside it
                it.selectLayer(id)
                it.groupPicked()
            }
            Unit
        }
"""
    vm = vm.replace(old_add, new_add, 1)
    funcs = """    /** New frames start as groups, so a frame can hold several layers. */
    var framesAsGroups by mutableStateOf(true)

    /**
     * Another layer drawn in the current frame, which stays one frame: a frame that is a single
     * layer is put in a group first, and the new layer goes inside the group.
     */
    fun addLayerToFrame() {
        frameOptionsOpen = false
        stopPlaying()
        val s = session ?: return
        val frame = currentFrameLayer() ?: return
        val inside: ULong? = when (frame.kind) {
            LayerType.GROUP -> layers.firstOrNull { it.parent == frame.id && it.kind != LayerType.MASK }?.id
            LayerType.PAINT -> {
                s.selectLayer(frame.id)
                if (s.groupPicked() == 0uL) null else frame.id
            }
            else -> null
        }
        if (inside == null) return
        refresh()
        selectLayer(inside)
        addLayer()
    }

"""
    vm = vm.replace(head, funcs + head, 1)
    ui = ui.replace(toggle, toggle + '        ToggleRow("Frames hold layers", vm.framesAsGroups, 44.5.dp) { vm.framesAsGroups = !vm.framesAsGroups }\n        RowLine()\n', 1)
    row = ("        if (!a.pages) {\n        RowLine()\n"
           "        Row(Modifier.fillMaxWidth().height(44.dp).clickable { vm.addLayerToFrame() }.padding(start = 16.dp), verticalAlignment = Alignment.CenterVertically) {\n"
           "            Text(\"Add Layer to Frame\", color = Pc.PanelTitle, fontSize = 17.sp)\n"
           "        }\n        }\n")
    ui = ui.replace(anchor, row + anchor, 1)
    write(vm_path, vm); write(ui_path, ui)
    print("Frames with layers added")

frames_with_layers()

# 8. The app's name, its own package id (so it installs beside the original ProCraft), and a
#    language button (RU / EN) in the gallery's header.
def branding_and_language():
    gradle = "android/app/build.gradle.kts"
    if os.path.exists(gradle):
        g = read(gradle)
        old = 'applicationId = "io.github.artcraftandroid.procraft"'
        if old in g:
            write(gradle, g.replace(old, 'applicationId = "io.github.artcraftandroid.studio"', 1))
        else:
            warn.append("applicationId not found: the app keeps ProCraft's id")
    strings = f"{MAIN}/res/values/strings.xml"
    if os.path.exists(strings):
        write(strings, read(strings).replace("ProCraft", "Procreate Android"))
    gp = f"{PKG}/ui/GalleryScreen.kt"
    if not os.path.exists(gp):
        warn.append("Language button: GalleryScreen.kt not found"); return
    g = read(gp)
    anchor = ("        Row(Modifier.align(Alignment.TopEnd).padding(top = 10.dp, end = 20.dp), verticalAlignment = Alignment.CenterVertically) {\n"
              "            Row(\n")
    if g.count(anchor) != 1:
        warn.append("Language button: the gallery header looks different, button not added"); return
    button = (
        "        val languageContext = androidx.compose.ui.platform.LocalContext.current\n"
        "        Row(Modifier.align(Alignment.TopEnd).padding(top = 10.dp, end = 20.dp), verticalAlignment = Alignment.CenterVertically) {\n"
        "            Box(\n"
        "                Modifier.padding(end = 12.dp).size(52.dp, 45.dp).clip(CircleShape).background(Pc.Capsule).border(1.dp, Pc.CapsuleEdge, CircleShape)\n"
        "                    .clickable { io.github.artcraftandroid.procraft.i18n.I18n.toggle(languageContext) },\n"
        "                contentAlignment = Alignment.Center,\n"
        "            ) {\n"
        "                androidx.compose.material3.Text(\n"
        "                    if (io.github.artcraftandroid.procraft.i18n.I18n.isRussian) \"RU\" else \"EN\",\n"
        "                    color = Pc.GalleryText, fontSize = 16.sp, fontWeight = FontWeight.Bold,\n"
        "                )\n"
        "            }\n"
        "            NewYearButton()\n"
        "            Row(\n")
    write(gp, g.replace(anchor, button, 1))
    print("Branding and language button added")

branding_and_language()

# 9. New Year: a garland and a little snow drawn over the gallery (touches go through them), and a
#    snowflake button beside RU / EN that switches them. Five quick taps on it show a surprise.
def new_year():
    shutil.copy(f"{HERE}/NewYear.kt", f"{PKG}/ui/NewYear.kt")
    gp = f"{PKG}/ui/GalleryScreen.kt"
    if not os.path.exists(gp):
        warn.append("New Year: GalleryScreen.kt not found"); return
    g = read(gp)
    old = "BoxWithConstraints(Modifier.fillMaxSize().background(Pc.GalleryBackground)) {"
    if old not in g:
        warn.append("New Year: the gallery looks different, the garland is not drawn"); return
    write(gp, g.replace(old, "BoxWithConstraints(Modifier.fillMaxSize().background(Pc.GalleryBackground).newYear()) {", 1))
    print("New Year added")

new_year()

# 10. The app icon, made from ru/icon.png at every size the icon needs (needs Pillow).
def app_icon():
    src = f"{HERE}/icon.png"
    if not os.path.exists(src):
        warn.append("icon.png not found: the icon is not changed"); return
    try:
        from PIL import Image
    except ImportError:
        warn.append("Pillow is missing: the icon is not changed"); return
    im = Image.open(src).convert("RGB")
    bg = im.getpixel((4, 4))
    for density, px in {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}.items():
        folder = f"{MAIN}/res/drawable-{density}"
        if not os.path.isdir(folder):
            continue
        side = int(px * 0.52)
        art = im.resize((side, side), Image.LANCZOS)
        pos = ((px - side) // 2, (px - side) // 2)
        fg = Image.new("RGB", (px, px), bg)
        fg.paste(art, pos)
        fg.save(f"{folder}/ic_launcher_foreground.png")
        # the one-colour icon some launchers use: the bright parts of the picture
        alpha = art.convert("L").point(lambda v: 0 if v < 70 else min(255, (v - 70) * 4))
        mono = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        mono.paste(Image.new("RGBA", (side, side), (255, 255, 255, 255)), pos, alpha)
        mono.save(f"{folder}/ic_launcher_monochrome.png")
    print("Icon replaced")

app_icon()

# 11. Take a layer to another artwork: hold a layer (until it can be dragged) and touch the screen with
#     a second finger; the layer goes in hand (the app's clipboard), and a plate offers "Paste here"
#     in whichever artwork is opened next. Copy Layer and Copy Canvas put theirs in hand too.
def carry():
    shutil.copy(f"{HERE}/Carry.kt", f"{PKG}/ui/Carry.kt")
    vm_path = f"{PKG}/canvas/CanvasViewModel.kt"
    lp_path = f"{PKG}/ui/LayersPanel.kt"
    ma_path = f"{PKG}/MainActivity.kt"
    if not all(os.path.exists(p) for p in (vm_path, lp_path, ma_path)):
        warn.append("Carry: files not found"); return
    vm, lp, ma = read(vm_path), read(lp_path), read(ma_path)
    copy_layer = "    fun copyLayer() {\n"
    layer_note = '        if (copied != null) showNotice("Layer copied")\n'
    canvas_note = '            if (copied != null) showNotice("Canvas copied")\n'
    paste_head = "    fun paste(private: Boolean = false) {\n        val image = clipboard ?: return\n"
    drag_start = "                                    dragId = l.id\n                                    dragOffset = 0f\n                                    dragUnit = vm.movingWith(l) + l.id\n"
    drag_end = "                                onDragEnd = {\n                                    rows[l.id]?.let { drop(vm, l, it.center.y + dragOffset, rows) }\n"
    drag_cancel = "                                onDragCancel = {\n                                    dragId = null\n                                    dragOffset = 0f\n                                    dragUnit = emptySet()\n                                    pinned[0]?.release()\n"
    touch_head = "    override fun dispatchTouchEvent(e: android.view.MotionEvent): Boolean {\n"
    app_call = ") { AppRoot(model) }"
    checks = [(vm, copy_layer), (vm, layer_note), (vm, canvas_note), (vm, paste_head),
              (lp, drag_start), (lp, drag_end), (lp, drag_cancel), (ma, touch_head), (ma, app_call)]
    if any(text.count(anchor) != 1 for text, anchor in checks) or "var carrying" in vm:
        warn.append("Carry: the code looks different, the gesture is not added"); return
    funcs = (
        "    /** A layer (or the canvas) taken along to paste into another artwork: the plate over the app. */\n"
        "    var carrying by mutableStateOf(false)\n\n"
        "    /** The layer held down goes in hand: it is in the clipboard until it is pasted somewhere. */\n"
        "    fun carryLayer(l: LayerInfo) {\n"
        "        copyLayerContents(l)\n"
        "        carrying = canPaste\n"
        '        if (carrying) showNotice("Layer in hand")\n'
        "    }\n\n"
        "    fun endCarry() {\n"
        "        carrying = false\n"
        "    }\n\n")
    vm = vm.replace(copy_layer, funcs + copy_layer, 1)
    vm = vm.replace(layer_note, layer_note + "        if (copied != null) carrying = true\n", 1)
    vm = vm.replace(canvas_note, canvas_note + "            if (copied != null) carrying = true\n", 1)
    vm = vm.replace(paste_head, paste_head + "        carrying = false\n", 1)
    lp = lp.replace(drag_start, drag_start + "                                    LayerCarry.hold { vm.carryLayer(l) }\n", 1)
    lp = lp.replace(drag_end, "                                onDragEnd = {\n                                    LayerCarry.release()\n" + drag_end.split("\n", 1)[1], 1)
    lp = lp.replace(drag_cancel, "                                onDragCancel = {\n                                    LayerCarry.release()\n" + drag_cancel.split("\n", 1)[1], 1)
    touch = (touch_head +
             "        when (e.actionMasked) {\n"
             "            android.view.MotionEvent.ACTION_POINTER_DOWN -> io.github.artcraftandroid.procraft.ui.LayerCarry.secondFinger()\n"
             "            android.view.MotionEvent.ACTION_DOWN, android.view.MotionEvent.ACTION_UP, android.view.MotionEvent.ACTION_CANCEL -> io.github.artcraftandroid.procraft.ui.LayerCarry.release()\n"
             "        }\n")
    ma = ma.replace(touch_head, touch, 1)
    ma = ma.replace(app_call, ") { io.github.artcraftandroid.procraft.ui.AppWithCarry(model) }", 1)
    write(vm_path, vm); write(lp_path, lp); write(ma_path, ma)
    print("Carry added")

carry()

# 12. Auto In-betweens: with the Tweening plugin on, one tap draws several evenly spaced frames between
#     a frame and the next (the plugin's In-between, called one after another with the slider set so
#     the frames fall at 1/(n+1), 2/(n+1) ... of the way). The frames need one layer each.
def auto_inbetweens():
    vm_path = f"{PKG}/canvas/CanvasViewModel.kt"
    ui_path = f"{PKG}/ui/AnimationUi.kt"
    if not (os.path.exists(vm_path) and os.path.exists(ui_path)):
        warn.append("Auto in-betweens: files not found"); return
    vm, ui = read(vm_path), read(ui_path)
    doc = "    /** A plugin's In-between: a frame drawn between this frame and the next by the plugin (off the main thread: it takes a moment), made current. */\n"
    row = ('            Row(Modifier.fillMaxWidth().height(44.dp).clickable { vm.addInbetween() }.padding(start = 16.dp), verticalAlignment = Alignment.CenterVertically) {\n'
           '                Text("In-between", color = Pc.PanelTitle, fontSize = 17.sp)\n'
           '            }\n')
    if not (doc in vm and row in ui and "autoInbetweens" not in vm and "val pluginList" not in "" and "pluginList" in vm):
        warn.append("Auto in-betweens: the code looks different, nothing added"); return
    funcs = """    /** How many frames Auto In-betweens draws between a frame and the next. */
    var autoInbetweens by androidx.compose.runtime.mutableIntStateOf(3)

    /**
     * Auto In-betweens: [autoInbetweens] frames between this frame and the next, evenly spaced. The
     * Tweening plugin draws each (its "Nearer the next frame" slider set to what the spacing needs,
     * then put back), one after another, each between the last one made and the next frame.
     */
    fun addAutoInbetweens() {
        frameOptionsOpen = false
        stopPlaying()
        val layer = currentFrameLayer() ?: return
        val s = session ?: return
        val count = autoInbetweens.coerceIn(1, 8)
        val near = pluginList.firstOrNull { it.id == "io.github.artcraftandroid.tweening" && it.on }
            ?.controls
            ?.firstNotNullOfOrNull { (it as? io.github.artcraftandroid.procraft.core.PluginControl.Slider)?.control?.takeIf { c -> c.key.endsWith("near") } }
        if (near == null) {
            message = "Turn on the Tweening plugin first."
            return
        }
        val was = near.value
        viewModelScope.launch {
            var from = layer.id
            var made = 0
            for (k in 1..count) {
                plugins.setSlider(near.key, 1f / (count + 2 - k))
                val next = withContext(Dispatchers.Default) { s.addInbetween(from) } ?: break
                from = next
                made++
            }
            plugins.setSlider(near.key, was)
            if (made == 0) message = "An in-between goes between two frames of one layer each, with something drawn." else layerChange { }
        }
    }

"""
    vm = vm.replace(doc, funcs + doc, 1)
    more = row + (
        '            RowLine()\n'
        '            Row(Modifier.fillMaxWidth().height(44.dp).padding(start = 16.dp), verticalAlignment = Alignment.CenterVertically) {\n'
        '                Text("Auto In-betweens", color = Pc.PanelTitle, fontSize = 17.sp, modifier = Modifier.weight(1f).clickable { vm.addAutoInbetweens() })\n'
        '                Text("\\u2212", color = Pc.PanelTitle, fontSize = 22.sp, textAlign = androidx.compose.ui.text.style.TextAlign.Center, modifier = Modifier.width(36.dp).clickable { vm.autoInbetweens = (vm.autoInbetweens - 1).coerceAtLeast(1) })\n'
        '                Text("${vm.autoInbetweens}", color = Pc.PanelTitle, fontSize = 17.sp, textAlign = androidx.compose.ui.text.style.TextAlign.Center, modifier = Modifier.width(22.dp))\n'
        '                Text("+", color = Pc.PanelTitle, fontSize = 22.sp, textAlign = androidx.compose.ui.text.style.TextAlign.Center, modifier = Modifier.width(36.dp).clickable { vm.autoInbetweens = (vm.autoInbetweens + 1).coerceAtMost(8) })\n'
        '            }\n')
    ui = ui.replace(row, more, 1)
    write(vm_path, vm); write(ui_path, ui)
    print("Auto in-betweens added")

auto_inbetweens()

for w in warn: print("WARNING:", w)
print("done")
sys.exit(0)
