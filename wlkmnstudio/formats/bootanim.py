"""Sony icx_bootanimation format.

Frames are 480x200 16-bit RGB565 BMPs (BI_BITFIELDS; part headers differ: 138B / 70B), packed STORED
(uncompressed) in a zip alongside desc.txt (`<count> <pause> <lastframe>` per part, positional
part0/part1/part2; last part loops). The safe method — proven on-device — is to keep the STOCK zip's
structure verbatim (desc + per-part frame counts + BMP headers) and only rewrite the 192000 pixel bytes.

Two builders:
  build_from_gif  — drop the user's own GIF in (resampled to each part; part2 = seamless loop).
  build_from_logo — the WLKMN squish→line→waves intro, reusing the device's OWN stock wave footage.

No Sony assets are bundled: both read the stock bootanimation.zip pulled from the user's device.
"""
import io, struct, zipfile
import numpy as np
from PIL import Image, ImageSequence, ImageOps, ImageDraw

W, H = 480, 200


# ---------- RGB565 BMP codec (preserves the original header) ----------
def read_bmp(data):
    off = struct.unpack_from("<I", data, 10)[0]
    w, h = struct.unpack_from("<ii", data, 18)
    ah = abs(h)
    pix = np.frombuffer(data[off:off + w * ah * 2], dtype="<u2").reshape(ah, w)
    r = ((pix >> 11) & 0x1f).astype(np.uint16); r = (r << 3) | (r >> 2)
    g = ((pix >> 5) & 0x3f).astype(np.uint16); g = (g << 2) | (g >> 4)
    b = (pix & 0x1f).astype(np.uint16); b = (b << 3) | (b >> 2)
    rgb = np.dstack([r, g, b]).astype(np.uint8)[::-1]  # BMP bottom-up -> top-down
    return data[:off], Image.fromarray(rgb, "RGB")


def write_bmp(header, img):
    arr = np.asarray(img.convert("RGB"), dtype=np.uint16)[::-1]  # top-down -> bottom-up
    r = arr[:, :, 0] >> 3
    g = arr[:, :, 1] >> 2
    b = arr[:, :, 2] >> 3
    pix = ((r << 11) | (g << 5) | b).astype("<u2")
    return header + pix.tobytes()


def colorize(img, accent, bg=(0, 0, 0)):
    """white->accent, black->bg, gradients preserved via luminance."""
    return ImageOps.colorize(img.convert("L"), black=bg, white=accent)


def letterbox(img, w=W, h=H, bg=(0, 0, 0)):
    img = img.convert("RGB")
    s = min(w / img.width, h / img.height)
    nw, nh = max(1, round(img.width * s)), max(1, round(img.height * s))
    base = Image.new("RGB", (w, h), bg)
    base.paste(img.resize((nw, nh), Image.LANCZOS), ((w - nw) // 2, (h - nh) // 2))
    return base


def gif_frames(gif):
    im = gif if hasattr(gif, "read") else Image.open(gif)
    if not isinstance(im, Image.Image):
        im = Image.open(im)
    return [f.convert("RGB").copy() for f in ImageSequence.Iterator(im)]


# ---------- stock zip structure ----------
def read_structure(zip_bytes):
    """desc bytes + ordered [(part, sorted_frame_names, header_bytes, W, H)]."""
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    desc = z.read("desc.txt")
    parts, order = {}, []
    for n in z.namelist():
        if "/" in n and n.lower().endswith(".bmp"):
            p = n.split("/")[0]
            parts.setdefault(p, []).append(n)
            if p not in order:
                order.append(p)
    out = []
    for p in order:
        frames = sorted(parts[p])
        hdr, img = read_bmp(z.read(frames[0]))
        out.append((p, frames, hdr, img.width, img.height))
    return desc, out


def _load_part(z, frames):
    return [read_bmp(z.read(n))[1] for n in frames]


def _pack(desc, parts_frames):
    """parts_frames: [(part, header, [PIL images])] -> STORED zip bytes."""
    out = io.BytesIO()
    z = zipfile.ZipFile(out, "w", zipfile.ZIP_STORED)
    z.writestr("desc.txt", desc)
    for part, hdr, imgs in parts_frames:
        z.writestr(part + "/", b"")
        for i, im in enumerate(imgs):
            z.writestr(f"{part}/boot_{i:04d}.bmp", write_bmp(hdr, im))
    z.close()
    return out.getvalue()


# ---------- builders ----------
def build_from_gif(stock_zip_bytes, gif, bg=(0, 0, 0)):
    """Fill the stock structure with the user's GIF (one full cycle per part -> part2 loops cleanly)."""
    desc, parts = read_structure(stock_zip_bytes)
    frames = [letterbox(f, parts[0][3], parts[0][4], bg) for f in gif_frames(gif)]
    g = len(frames)
    if g == 0:
        raise ValueError("GIF has no frames")
    built = []
    for part, names, hdr, w, h in parts:
        n = len(names)
        imgs = [frames[round(i * g / n) % g] for i in range(n)]
        built.append((part, hdr, imgs))
    return _pack(desc, built)


def _smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def _ease_in(t):
    t = max(0.0, min(1.0, t)); return t * t


def build_from_logo(stock_zip_bytes, logo_img, accent, bg=(0, 0, 0), target_w=244):
    """WLKMN intro: logo held -> compresses onto the stock 'line' frame -> stock line->waves footage
    (recolored to `accent`) grows out, then the stock wave loop (recolored). Uses the device's OWN
    stock part1/part2 frames as the wave source (nothing Sony is bundled)."""
    z = zipfile.ZipFile(io.BytesIO(stock_zip_bytes))
    desc, parts = read_structure(stock_zip_bytes)
    by = {p: (frames, hdr, w, h) for p, frames, hdr, w, h in parts}
    p0, p1, p2 = "part0", "part1", "part2"
    (f0, h0, _, _), (f1, h1, _, _), (f2, h2, _, _) = by[p0], by[p1], by[p2]
    n0, n1, n2 = len(f0), len(f1), len(f2)

    # prep logo
    logo = logo_img.convert("RGBA")
    lw = target_w
    lh = round(logo.height * target_w / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    lx, ly = (W - lw) // 2, (H - lh) // 2
    cy = ly + lh // 2

    def logo_on_bg(op=1.0):
        base = Image.new("RGB", (W, H), bg)
        lg = logo.copy()
        if op < 1.0:
            lg.putalpha(lg.split()[3].point(lambda p: int(p * op)))
        base.paste(lg, (lx, ly), lg)
        return base

    def squished(hpx):
        base = Image.new("RGB", (W, H), bg)
        sq = logo.resize((lw, max(2, hpx)), Image.BILINEAR)
        base.paste(sq, (lx, cy - max(2, hpx) // 2), sq)
        return base

    # find the flattest stock part1 frame (the "line") by bright-pixel vertical spread
    p1_imgs = _load_part(z, f1)
    spreads = []
    for im in p1_imgs:
        a = np.array(im.convert("L")); ys, _ = np.where(a > 60)
        spreads.append((ys.max() - ys.min()) if len(ys) else 999)
    line_idx = int(np.argmin(spreads))
    target_line = colorize(p1_imgs[line_idx], accent, bg)

    part0 = [logo_on_bg(1.0) for _ in range(n0)]

    part1 = []
    for i in range(n1):
        if i <= line_idx:
            q = i / max(1, line_idx)
            hpx = int(round(lh * (1 - _smooth(q))))
            cw = _smooth(max(0.0, (q - 0.55) / 0.45))
            part1.append(Image.blend(squished(hpx), target_line, cw))
        else:
            part1.append(colorize(p1_imgs[i], accent, bg))

    part2 = [colorize(im, accent, bg) for im in _load_part(z, f2)]
    return _pack(desc, [(p0, h0, part0), (p1, h1, part1), (p2, h2, part2)])


def preview_gif(zip_bytes, max_frames=181, duration=33):
    """Render a bootanimation.zip back to an animated GIF (for the UI preview)."""
    desc, parts = read_structure(zip_bytes)
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    imgs = []
    for part, frames, hdr, w, h in parts:
        for n in frames:
            imgs.append(read_bmp(z.read(n))[1])
    imgs = imgs[:max_frames]
    if not imgs:
        return b""
    pal = imgs[len(imgs) // 2].convert("P", palette=Image.ADAPTIVE, colors=256)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]
    out = io.BytesIO()
    q[0].save(out, format="GIF", save_all=True, append_images=q[1:], duration=duration,
              loop=0, optimize=False, disposal=1)
    return out.getvalue()
