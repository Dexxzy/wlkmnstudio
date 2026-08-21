"""viewstyle themer — recolor the Hagoromo player's MAIN UI text + background to any color.

Every screen reads its palette as plain-text QML bindings (e.g. `color: viewstyle.textcolor.L1`)
embedded in the app's zlib-compressed Qt resource blobs. The palette VALUES come from a C++
QVariantMap (`ScreenController.styleProperties`) with no editable string anchor — but the *consumers*
are editable QML. So we redirect each binding to a static color literal.

Fit method (validated on-device, size + offset preserving):
  * replace the 22-char token `viewstyle.textcolor.L1` with a 9-char `"#RRGGBB"` literal
    -> uncompressed content SHRINKS
  * update the blob's 4-byte big-endian uncompressed-size prefix (immediately before the zlib stream)
  * recompress at level 9 (now smaller) and overwrite in place, zero-padding the slot tail
    (zlib ignores trailing zeros; every downstream qrc offset and the ELF size stay identical)
  * if a blob still overflows its slot (max seen: 19B), reclaim bytes by trimming leading QML/JS
    indentation, which is always insignificant and never inside a string literal.

Public API:
  TOKENS                       friendly slot -> qml token
  scan(app_bytes)   -> {token: count}          how many bindings exist for each token
  patch(app_bytes, colormap)   -> (new_bytes, stats)   colormap: {qml_token: "#RRGGBB"}
"""
import struct
import zlib

# friendly slot name -> the QML token it maps to (what consumers actually reference)
TOKENS = {
    "primary_text":   "viewstyle.textcolor.L1",   # titles, track names, main body   (~130x)
    "secondary_text": "viewstyle.textcolor.L2",   # subtitles, secondary labels       (~56x)
    "disabled_text":  "viewstyle.textcolor.L3",   # greyed / disabled items           (~25x)
    "highlight_text": "viewstyle.textcolor.Y1",   # hi-res / accent badge (gold stock) (~6x)
    "vivid_text":     "viewstyle.textcolor.V1",   # vivid/reverse-mode text            (~3x)
    "extra_text":     "viewstyle.textcolor.E1",   # emphasis text                     (~5x)
    "background":     "viewstyle.bgcolor.D1",     # main screen background            (~70x)
    "vivid_bg":       "viewstyle.bgcolor.V1",     # vivid/reverse-mode background      (~6x)
}

# hardcoded literal colors (not viewstyle tokens) that are safe to swap because they occur in a
# single blob. slot -> stock hex; the themer maps stock->user via hexmap.
HARDCODED = {
    "spectrum_low":  "#143a8b",   # spectrum-analyzer gradient, low end  (blue)
    "spectrum_high": "#21d6cd",   # spectrum-analyzer gradient, high end  (teal)
}


def _valid_hex(c):
    if not (isinstance(c, str) and len(c) == 7 and c[0] == "#"):
        return False
    try:
        int(c[1:], 16)
        return True
    except ValueError:
        return False


def iter_blobs(data):
    """Yield (start, comp_len, decompressed_bytes) for every zlib stream (non-overlapping)."""
    n = len(data)
    i = 0
    while True:
        j = data.find(b"\x78", i)
        if j < 0:
            break
        if j + 1 < n and data[j + 1] in (0x01, 0x9c, 0xda):
            d = zlib.decompressobj()
            try:
                out = d.decompress(data[j:])
                if len(out) > 40:
                    comp_len = (len(data) - j) - len(d.unused_data)
                    yield j, comp_len, out
                    i = j + comp_len
                    continue
            except zlib.error:
                pass
        i = j + 1


def _reduce_indent(text, keep):
    """Trim each line's leading-space run to at most `keep` spaces (safe: leading indentation is
    insignificant in QML/JS and, after a newline, never inside a string literal)."""
    out = bytearray()
    i = 0
    n = len(text)
    at_line_start = True
    while i < n:
        c = text[i]
        if at_line_start and c == 0x20:
            j = i
            while j < n and text[j] == 0x20:
                j += 1
            out += b" " * min(j - i, keep)
            i = j
            at_line_start = False
            continue
        out.append(c)
        at_line_start = (c == 0x0a)
        i += 1
    return bytes(out)


def _fit_compress(new, comp_len):
    """Return (content, compressed) fitting comp_len, trimming indentation only as needed."""
    comp = zlib.compress(new, 9)
    if len(comp) <= comp_len:
        return new, comp
    for keep in (8, 6, 4, 3, 2, 1, 0):
        cand = _reduce_indent(new, keep)
        comp = zlib.compress(cand, 9)
        if len(comp) <= comp_len:
            return cand, comp
    raise ValueError("blob cannot be made to fit even at zero indent (%d > %d)" % (len(comp), comp_len))


def scan(data):
    """Return {qml_token: total binding count} across all compressed blobs."""
    counts = {tok: 0 for tok in TOKENS.values()}
    for _, _, out in iter_blobs(data):
        for tok in counts:
            counts[tok] += out.count(tok.encode())
    return counts


def patch(data, colormap=None, hexmap=None):
    """Rewrite the app's QML palette in place. Returns (new_bytes, stats).

    colormap : {qml_token: '#RRGGBB'}  — redirect a `viewstyle.*` binding to a static color literal.
    hexmap   : {'#OLDHEX': '#NEWHEX'}  — swap a hardcoded literal hex (same length) wherever it appears,
               for colors that aren't viewstyle tokens (e.g. the spectrum-analyzer gradient).

    stats = {'tokens': {find: count}, 'blobs': n, 'size': len}. Raises on invalid color, a blob that
    won't fit, an unexpected size change, or if any `find` still remains (fails safe — no partial write).
    """
    colormap = {t: c for t, c in (colormap or {}).items() if c}   # drop blank slots
    hexmap = {o: n for o, n in (hexmap or {}).items() if n}
    reps = {}                                     # find bytes -> replace bytes
    for tok, col in colormap.items():
        if not _valid_hex(col):
            raise ValueError("bad color for %s: %r (want #rrggbb)" % (tok, col))
        if len(('"%s"' % col)) > len(tok):
            raise ValueError("color literal longer than token %s" % tok)
        reps[tok.encode()] = ('"%s"' % col).encode()
    for old, new in hexmap.items():
        if not (_valid_hex(old) and _valid_hex(new)):
            raise ValueError("hexmap needs #rrggbb -> #rrggbb, got %r -> %r" % (old, new))
        reps[old.encode()] = new.encode()         # equal length by construction
    if not reps:
        raise ValueError("no colors selected")

    data = bytearray(data)
    orig_size = len(data)
    stats = {f.decode(): 0 for f in reps}
    touched = 0
    for start, comp_len, out in list(iter_blobs(bytes(data))):
        if not any(f in out for f in reps):
            continue
        if start < 4 or struct.unpack(">I", data[start - 4:start])[0] != len(out):
            continue    # not a size-prefixed qCompress blob
        new = out
        for f, rep in reps.items():
            c = new.count(f)
            if c:
                new = new.replace(f, rep)
                stats[f.decode()] += c
        if new == out:
            continue
        new, comp = _fit_compress(new, comp_len)
        data[start - 4:start] = struct.pack(">I", len(new))
        data[start:start + len(comp)] = comp
        for k in range(start + len(comp), start + comp_len):
            data[k] = 0
        touched += 1

    if len(data) != orig_size:
        raise RuntimeError("size drift %d -> %d (aborted)" % (orig_size, len(data)))
    # verify: no targeted find-string remains anywhere, and blobs still decompress
    left = {f.decode(): 0 for f in reps}
    for _, _, out in iter_blobs(bytes(data)):
        for f in reps:
            left[f.decode()] += out.count(f)
    for f, cnt in left.items():
        if cnt != 0:
            raise RuntimeError("incomplete: %s still present (%d)" % (f, cnt))
    return bytes(data), {"tokens": stats, "blobs": touched, "size": len(data)}
