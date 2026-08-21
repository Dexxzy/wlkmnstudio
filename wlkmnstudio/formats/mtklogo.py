"""Sony NW-A50 MTK `logo` partition (3 MiB, /dev/block/mmcblk0p12).

Container (reversed + verified on-device):
  0x000 u32 magic 0x58881688 | 0x004 u32 payload_size | 0x008 "LOGO" | 0x00c..0x1ff padding
  0x200 u32 count | 0x204 u32 payload_size | 0x208 u32 offset[count] (RELATIVE to 0x200)
  then `count` zlib streams (each 480x854, pixels = 565 with R in bits[15:11] G[10:5] B[4:0]).
Images end at 0x200+payload_size; partition padded to 0x300000.

img0 = the orange WALKMAN power-on splash. We replace ONLY img0 and keep every other blob verbatim,
fixing the offset table + sizes. PIL decodes 565 via 'BGR;16' but has no matching encoder -> numpy.
"""
import struct, zlib
import numpy as np
from PIL import Image

IW, IH = 480, 854
BASE = 0x200
PART_SIZE = 0x300000
MAGIC = 0x58881688


def parse(d):
    assert struct.unpack_from("<I", d, 0)[0] == MAGIC, "bad logo magic"
    count = struct.unpack_from("<I", d, BASE)[0]
    payload = struct.unpack_from("<I", d, BASE + 4)[0]
    offs = [struct.unpack_from("<I", d, BASE + 8 + 4 * i)[0] for i in range(count)]
    bounds = [BASE + o for o in offs] + [BASE + payload]
    return count, payload, offs, bounds


def blobs(d):
    count, payload, offs, bounds = parse(d)
    return [bytes(d[bounds[i]:bounds[i + 1]]) for i in range(count)]


def decode_img(d, i):
    """Decode image i (only meaningful for full-screen 480x854 images, e.g. img0)."""
    _, _, _, bounds = parse(d)
    raw = zlib.decompress(d[bounds[i]:bounds[i + 1]])
    if len(raw) != IW * IH * 2:
        return None
    return Image.frombytes("RGB", (IW, IH), raw, "raw", "BGR;16")


def encode_565(img):
    a = np.asarray(img.convert("RGB"), dtype=np.uint16)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    val = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    return zlib.compress(val.astype("<u2").tobytes(), 9)


def build_splash(logo_img, width=244, bg=(0, 0, 0), center=(240, 427)):
    """Center the logo (crimson-on-bg) where the WALKMAN sat (measured center 240,427)."""
    logo = logo_img.convert("RGBA")
    h = round(logo.height * width / logo.width)
    logo = logo.resize((width, h), Image.LANCZOS)
    base = Image.new("RGB", (IW, IH), bg)
    base.paste(logo, (center[0] - width // 2, center[1] - h // 2), logo)
    return base


def replace_img0(logo_bin, new_img0):
    """Return a rebuilt 3MiB partition image with img0 swapped, offset table + sizes fixed."""
    d = bytearray(logo_bin)
    count, payload, offs, bounds = parse(d)
    bl = blobs(d)
    bl[0] = encode_565(new_img0)
    first_rel = offs[0]
    new_offs, cur = [], first_rel
    for b in bl:
        new_offs.append(cur); cur += len(b)
    new_payload = cur
    out = bytearray(d[:BASE])
    struct.pack_into("<I", out, 0x04, new_payload)
    hdr = bytearray(d[BASE:BASE + 8 + 4 * count])
    struct.pack_into("<I", hdr, 0, count)
    struct.pack_into("<I", hdr, 4, new_payload)
    for i, o in enumerate(new_offs):
        struct.pack_into("<I", hdr, 8 + 4 * i, o)
    out += hdr
    assert len(out) == BASE + first_rel
    for b in bl:
        out += b
    if len(out) < PART_SIZE:
        out += bytes(PART_SIZE - len(out))
    assert len(out) == PART_SIZE, f"size {len(out):#x} != {PART_SIZE:#x}"
    return bytes(out)


def verify_rebuild(orig_bin, new_bin):
    """Sanity: same count, all decompress, images 1..n-1 identical, size == 3MiB, offsets monotonic."""
    oc, _, _, _ = parse(orig_bin)
    nc, npay, no, _ = parse(new_bin)
    ob, nb = blobs(orig_bin), blobs(new_bin)
    for i in range(nc):
        zlib.decompress(nb[i])
    ok = (oc == nc and len(new_bin) == PART_SIZE
          and all(ob[i] == nb[i] for i in range(1, oc))
          and all(no[i] < no[i + 1] for i in range(len(no) - 1)))
    return ok
