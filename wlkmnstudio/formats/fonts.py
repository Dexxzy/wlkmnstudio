"""Font impersonation for Sony's SST / SST UI families.

The UI requests families "SST" and "SST UI". To swap the typeface we take a replacement font's outlines
and copy the ORIGINAL device font's whole `name` table onto it (family/subfamily/full/PS all become
SST*), then save under the original filename. A glyf(TTF) font saved as `.otf` loads fine (FreeType
detects by content). Use the matching weight per file (Light->300 / Roman->400 / Bold->700) so
usWeightClass + style bits are already correct — only the name table is swapped.

Six device files: SST-{Roman,Bold,Light}.otf (the MAIN UI family) + SSTUI-{Roman,Bold,Light}.ttf.
Ships only OFL fonts (or the user's own upload). Reverting = re-push the originals we backed up.
"""
import copy, io
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

# device filename -> desired weight (usWeightClass)
STOCK_FILES = {
    "SST-Roman.otf": 400, "SST-Bold.otf": 700, "SST-Light.otf": 300,
    "SSTUI-Roman.ttf": 400, "SSTUI-Bold.ttf": 700, "SSTUI-Light.ttf": 300,
}
FONT_DIR = "/system/vendor/sony/lib/fonts"


def instance_weight(src_bytes, wght):
    """If the source is a variable font, pin its weight; else return as-is."""
    f = TTFont(io.BytesIO(src_bytes))
    if "fvar" in f:
        axes = {a.axisTag: a.defaultValue for a in f["fvar"].axes}
        axes["wght"] = wght
        instantiateVariableFont(f, axes, inplace=True)
        out = io.BytesIO(); f.save(out); return out.getvalue()
    return src_bytes


def impersonate(new_font_bytes, orig_font_bytes):
    """Copy the original's `name` table onto the new font's outlines. Returns font bytes."""
    new = TTFont(io.BytesIO(new_font_bytes))
    orig = TTFont(io.BytesIO(orig_font_bytes))
    new["name"].names = [copy.deepcopy(r) for r in orig["name"].names]
    out = io.BytesIO(); new.save(out); return out.getvalue()


def build_font_set(family_weight_bytes, stock_bytes):
    """family_weight_bytes: {weight(300/400/700): source_font_bytes}
       stock_bytes: {filename: original_device_font_bytes}
       -> {filename: impersonated_font_bytes} for all six SST/SST UI files."""
    out = {}
    for fname, wght in STOCK_FILES.items():
        src = family_weight_bytes.get(wght) or family_weight_bytes.get(400)
        if src is None:
            raise ValueError("need at least a Regular (400) weight")
        pinned = instance_weight(src, wght)
        out[fname] = impersonate(pinned, stock_bytes[fname])
    return out


def family_name(font_bytes):
    return TTFont(io.BytesIO(font_bytes))["name"].getDebugName(1)
