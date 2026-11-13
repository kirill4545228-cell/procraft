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

for w in warn: print("WARNING:", w)
print("done")
sys.exit(0)
