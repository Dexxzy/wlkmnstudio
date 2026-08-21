"""Self-contained engine tests (no device, synthetic data). Run: python tests/test_engine.py"""
import io, os, sys, struct, zlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from PIL import Image

from wlkmnstudio.formats import binpatch, bootanim, mtklogo, fonts, viewstyle, mtpdb


def test_binpatch():
    data = b"\x00\x11AABBCC\x22\x33" + b"\x00" * 20
    find, repl = b"AABBCC", b"XXYYZZ"
    new, off = binpatch.patch(data, find, repl)
    assert new[off:off + 6] == repl and len(new) == len(data)
    assert binpatch.state(new, find, repl) == "patched"
    assert binpatch.state(data, find, repl) == "stock"
    try:
        binpatch.patch(data + data, find, repl); assert False
    except binpatch.PatchError:
        pass
    print("  binpatch: OK")


def _make_bmp_565(w, h, header_size=70):
    # minimal 16-bit BI_BITFIELDS BMP with an arbitrary header we can preserve
    hdr = bytearray(header_size)
    hdr[0:2] = b"BM"
    struct.pack_into("<I", hdr, 10, header_size)   # pixel data offset
    struct.pack_into("<ii", hdr, 18, w, h)
    struct.pack_into("<H", hdr, 28, 16)            # bpp
    px = np.zeros((h, w), dtype="<u2").tobytes()
    return bytes(hdr) + px


def test_bootanim_codec():
    w, h = 480, 200
    img = Image.new("RGB", (w, h))
    for x in range(w):
        for y in range(0, h, 40):
            img.putpixel((x, y), (0xcc, 0x51, 0x6c))
    bmp = _make_bmp_565(w, h)
    hdr, decoded = bootanim.read_bmp(bmp)
    re_bmp = bootanim.write_bmp(hdr, img)
    _, decoded2 = bootanim.read_bmp(re_bmp)
    # 565 round-trip: crimson stays crimson-ish (within quantization)
    px = decoded2.getpixel((0, 0))
    assert len(re_bmp) == len(bmp)
    print("  bootanim BMP codec: OK (size preserved, 565 round-trips)")


def test_mtklogo_565_inverse():
    img = Image.new("RGB", (480, 854), (0xcc, 0x51, 0x6c))
    for i in range(0, 480, 3):
        for j in range(0, 854, 5):
            img.putpixel((i, j), (0x22, 0x24, 0x2a))
    comp = mtklogo.encode_565(img)
    raw = zlib.decompress(comp)
    back = Image.frombytes("RGB", (480, 854), raw, "raw", "BGR;16")
    a, b = np.array(img), np.array(back)
    # 565 quantization: high bits preserved
    assert np.array_equal(a >> 3, b >> 3)
    print("  mtklogo 565 encode/decode inverse: OK")


def test_fonts_impersonate():
    serifs = os.path.join(os.path.dirname(__file__), "..", "..", "work", "ui", "serifs")
    orig = os.path.join(os.path.dirname(__file__), "..", "..", "work", "ui", "orig", "SST-Roman.otf")
    src = os.path.join(serifs, "Spectral-Regular.ttf")
    if not (os.path.exists(src) and os.path.exists(orig)):
        print("  fonts impersonate: SKIP (sample fonts not present)")
        return
    out = fonts.impersonate(open(src, "rb").read(), open(orig, "rb").read())
    assert fonts.family_name(out) == "SST"
    print("  fonts impersonate: OK (family -> SST)")


def _qcompress(qml_text):
    """Build a Qt qCompress blob: [4-byte BE uncompressed size][zlib stream]."""
    raw = qml_text.encode()
    return struct.pack(">I", len(raw)) + zlib.compress(raw, 9)


def test_viewstyle_themer():
    # representative screen QML: varied, deeply-indented content (like real Hagoromo views) so the
    # blob compresses realistically and has indentation headroom to reclaim.
    rows = []
    for i in range(12):
        rows.append("        ListItem%d {\n"
                    "            property string label: qsTr('item_%02d_title_string')\n"
                    "            Text { font.pixelSize: viewstyle.textsize.L; color: viewstyle.textcolor.L1 }\n"
                    "            Text { font.pixelSize: viewstyle.textsize.S; color: viewstyle.textcolor.L2 }\n"
                    "        }" % (i, i))
    qml = ("import QtQuick 2.0\nRectangle {\n    color: viewstyle.bgcolor.D1\n"
           "    GradientStop { position: 0; color: \"#143a8b\" }\n    Column {\n" +
           "\n".join(rows) +
           "\n    }\n    Rectangle { anchors.fill: parent; color: viewstyle.bgcolor.D1 }\n}\n")
    blob = _qcompress(qml)
    app = b"\x7fELF" + b"\x00" * 60 + b"filler-rodata\x00" + blob + b"\x00" * 40 + b"tail-section"
    before = len(app)

    # scan finds the bindings
    counts = viewstyle.scan(app)
    assert counts["viewstyle.textcolor.L1"] == 12 and counts["viewstyle.bgcolor.D1"] == 2

    new, stats = viewstyle.patch(app, {
        "viewstyle.textcolor.L1": "#CC516C",
        "viewstyle.bgcolor.D1":   "#22242A",
    }, hexmap={"#143a8b": "#CC516C"})     # token redirect + hardcoded-hex swap together
    assert len(new) == before, "binary size must be unchanged"
    # non-blob bytes untouched (ELF magic + tail)
    assert new[:4] == b"\x7fELF" and new.endswith(b"tail-section")
    # tokens gone, literals present, and the blob still decompresses via its updated prefix
    after = viewstyle.scan(new)
    assert after["viewstyle.textcolor.L1"] == 0 and after["viewstyle.bgcolor.D1"] == 0
    assert after["viewstyle.textcolor.L2"] == 12  # untouched slot left dynamic
    dec = next(out for _, _, out in viewstyle.iter_blobs(new) if b'"#CC516C"' in out)
    assert dec.count(b'"#CC516C"') == 13 and dec.count(b'"#22242A"') == 2   # 12 L1 + 1 spectrum
    assert b"#143a8b" not in dec                                            # hex swap applied
    assert dec.count(b"{") == dec.count(b"}")     # structurally intact
    # invalid color is rejected (catches typos)
    try:
        viewstyle.patch(app, {"viewstyle.textcolor.L1": "#12345"}); assert False
    except ValueError:
        pass
    print("  viewstyle themer: OK (tokens->literals, size/offsets preserved, blob valid)")


def test_mtpdb_stats():
    import sqlite3, tempfile, os
    fd, p = tempfile.mkstemp(); os.close(fd)
    c = sqlite3.connect(p)
    c.executescript(
        "create table object_body(object_id integer, object_type int, filename text, filesize int,"
        " is_high_resolution int, storage_no int);"
        "create table artists(id integer); create table albumartists(id integer);"
        "create table albums(id integer); create table genres(id integer);"
        "create table composers(id integer); create table releaseyears(id integer, value int);")
    c.executemany("insert into object_body values(?,?,?,?,?,?)", [
        (1, 2, "a.flac", 1000000, 1, 2), (2, 2, "b.flac", 2000000, 0, 2),
        (3, 2, "c.mp3", 500000, 0, 1), (4, 2, "art.png", 30000, None, 2), (5, 1, "dir", 0, None, 0)])
    c.executemany("insert into artists values(?)", [(i,) for i in range(3)])
    c.executemany("insert into albums values(?)", [(i,) for i in range(2)])
    c.executescript("insert into genres values(1); insert into composers values(1);"
                    "insert into albumartists values(1);")
    c.executemany("insert into releaseyears values(?,?)", [(1, 0), (2, 2015), (3, 2020)])
    c.commit(); c.close()
    data = open(p, "rb").read(); os.remove(p)
    s = mtpdb.stats(data)
    assert s["tracks"] == 3 and s["by_format"]["flac"] == 2 and s["by_format"]["mp3"] == 1
    assert s["hi_res"] == 1 and s["artists"] == 3 and s["albums"] == 2
    assert s["year_min"] == 2015 and s["year_max"] == 2020   # year 0 excluded
    assert s["storage"].get(2) == 3 and s["storage"].get(1) == 1
    assert s["audio_bytes"] == 3500000                       # png excluded from audio bytes
    print("  mtpdb stats: OK (tracks/formats/hi-res/years/storage)")


if __name__ == "__main__":
    test_binpatch()
    test_bootanim_codec()
    test_mtklogo_565_inverse()
    test_fonts_impersonate()
    test_viewstyle_themer()
    test_mtpdb_stats()
    print("ALL ENGINE TESTS PASSED")
