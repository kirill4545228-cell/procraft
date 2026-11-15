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
        "            Row(\n")
    write(gp, g.replace(anchor, button, 1))
    print("Branding and language button added")

branding_and_language()

for w in warn: print("WARNING:", w)
print("done")
sys.exit(0)
