"""Thin adb wrapper. Uses the staging tricks we learned: partitions are read/written via /data dd
(not exec-out), system files via push + remount + chmod, everything md5-verified."""
import subprocess, hashlib, os, tempfile, time

ADB = os.environ.get("WLKMN_ADB", "adb")


class DeviceError(Exception):
    pass


def _run(args, timeout=180, binary=False, check=True):
    r = subprocess.run([ADB, *args], capture_output=True, timeout=timeout)
    if check and r.returncode != 0:
        msg = (r.stderr or r.stdout).decode("utf-8", "replace").strip()
        raise DeviceError(msg or f"adb {' '.join(args)} failed")
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def devices():
    out = _run(["devices"], check=False)
    return [l.split()[0] for l in out.splitlines()[1:]
            if l.strip() and l.split()[1:2] == ["device"]]


def shell(cmd, **kw):
    return _run(["shell", cmd], **kw)


def is_root():
    # some Walkman toolbox builds print the full `uid=0(root)…` for `id -u`, not a bare "0"
    try:
        out = shell("id").strip()
        return out.strip() == "0" or "uid=0" in out
    except DeviceError:
        return False


def detect():
    ds = devices()
    if not ds:
        return {"connected": False}
    model = ""
    try:
        model = shell("getprop ro.product.model").strip()
    except DeviceError:
        pass
    wm1 = False
    try:
        wm1 = bool(shell("ls /system/vendor/sony 2>/dev/null || true").strip())
    except DeviceError:
        pass
    return {"connected": True, "serial": ds[0], "root": is_root(),
            "model": model or "?", "walkman_one": wm1}


def remount_rw():
    shell("mount -o rw,remount /system 2>/dev/null; mount -o rw,remount / 2>/dev/null; true")


def md5_remote(path):
    return shell(f"busybox md5sum {path}").split()[0]


def md5_bytes(b):
    return hashlib.md5(b).hexdigest()


def pull_file(remote):
    """Direct adb pull of a regular file -> bytes."""
    fd, local = tempfile.mkstemp()
    os.close(fd)
    try:
        _run(["pull", remote, local])
        with open(local, "rb") as fh:
            return fh.read()
    finally:
        try:
            os.unlink(local)
        except OSError:
            pass


def push_bytes(data, remote):
    fd, local = tempfile.mkstemp()
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    try:
        _run(["push", local, remote])
    finally:
        os.unlink(local)


def read_partition(dev, size):
    """dd the block device to /data (fits in /data free space), pull, clean up."""
    tmp = f"/data/.wlkmn_pull_{int(time.time() * 1000)}"
    blocks = (size + 4095) // 4096
    shell(f"dd if={dev} of={tmp} bs=4096 count={blocks} 2>/dev/null; chmod 644 {tmp}")
    try:
        data = pull_file(tmp)
        return data[:size]
    finally:
        shell(f"busybox rm -f {tmp}")


def install_file(data, remote, mode="644"):
    """Push bytes to a system path (rw remount), fix perms, verify md5."""
    remount_rw()
    want = md5_bytes(data)
    push_bytes(data, remote)
    shell(f"chmod {mode} {remote}; chown root:root {remote} 2>/dev/null || chown 0.0 {remote}; true")
    got = md5_remote(remote)
    if got != want:
        raise DeviceError(f"install verify mismatch {remote} ({got} != {want})")
    return want


def pidof(name):
    out = shell(f"busybox pidof {name} 2>/dev/null || ps 2>/dev/null | busybox grep '{name}' | busybox grep -v grep")
    for tok in out.split():
        if tok.isdigit():
            return int(tok)
    return None


def read_mem(pid, addr, n):
    """Read n bytes at virtual address `addr` from /proc/pid/mem (root)."""
    tmp = f"/data/.rm{int(time.time()*1000)}"
    shell(f"dd if=/proc/{pid}/mem bs=1 skip={addr} count={n} of={tmp} 2>/dev/null; chmod 644 {tmp}")
    try:
        return pull_file(tmp)[:n]
    finally:
        shell(f"busybox rm -f {tmp}")


def module_base(pid, path_substr):
    """Lowest mapped address of the module whose maps line contains path_substr (its load base)."""
    maps = shell(f"cat /proc/{pid}/maps 2>/dev/null")
    lo = None
    for line in maps.splitlines():
        if path_substr in line:
            start = int(line.split("-")[0], 16)
            lo = start if lo is None else min(lo, start)
    return lo


def _fb_geometry():
    """(width, visible_height, virtual_height, bpp) for /dev/graphics/fb0."""
    import re
    vs = shell("cat /sys/class/graphics/fb0/virtual_size 2>/dev/null").strip()   # "480,2400"
    W, VH = (int(x) for x in vs.split(","))
    try:
        bpp = int(shell("cat /sys/class/graphics/fb0/bits_per_pixel 2>/dev/null").strip())
    except (ValueError, DeviceError):
        bpp = 32
    H = None
    try:
        m = re.search(r"(\d+)x(\d+)", shell("cat /sys/class/graphics/fb0/mode 2>/dev/null"))
        if m:
            H = int(m.group(2))
    except DeviceError:
        pass
    if not H:                                   # framebuffer is usually 2–3 stacked buffers
        H = VH // 3 if VH % 3 == 0 else (VH // 2 if VH % 2 == 0 else VH)
    return W, H, VH, bpp


def screenshot(path=None, fmt="PNG"):
    """Grab the live screen from the framebuffer. Returns PNG bytes; also saves to `path` if given.

    The fb holds several stacked buffers (double/triple buffering); we decode each and return the
    one with the most on-screen content (the visible frame). Handles 32bpp BGRA and 16bpp BGR565.
    """
    import io
    from PIL import Image
    W, H, VH, bpp = _fb_geometry()
    Bpp = bpp // 8
    rowbytes = W * Bpp
    tmp = f"/data/.wlkmn_fb_{int(time.time() * 1000)}"
    shell(f"dd if=/dev/graphics/fb0 of={tmp} bs={rowbytes} count={VH} 2>/dev/null; chmod 644 {tmp}")
    try:
        raw = pull_file(tmp)
    finally:
        shell(f"busybox rm -f {tmp}")
    frame = W * H * Bpp
    nbuf = max(1, len(raw) // frame)
    best = None
    for b in range(nbuf):
        seg = raw[b * frame:(b + 1) * frame]
        if len(seg) < frame:
            break
        if bpp == 32:
            im = Image.frombytes("RGBA", (W, H), seg, "raw", "BGRA").convert("RGB")
        elif bpp == 16:
            im = Image.frombytes("RGB", (W, H), seg, "raw", "BGR;16")
        else:
            raise DeviceError(f"unsupported framebuffer depth {bpp}bpp")
        # content score = count of non-near-black pixels
        score = sum(1 for p in im.convert("L").getdata() if p > 12)
        if best is None or score > best[0]:
            best = (score, im)
    if best is None:
        raise DeviceError("framebuffer read produced no frames")
    im = best[1]
    buf = io.BytesIO()
    im.save(buf, fmt)
    data = buf.getvalue()
    if path:
        with open(path, "wb") as fh:
            fh.write(data)
    return data


def write_partition(data, dev):
    """Stage bytes in /data, verify, dd onto the block device, verify readback."""
    remount_rw()
    tmp = f"/data/.wlkmn_flash_{int(time.time() * 1000)}"
    want = md5_bytes(data)
    push_bytes(data, tmp)
    if md5_remote(tmp) != want:
        shell(f"busybox rm -f {tmp}")
        raise DeviceError("staged md5 mismatch before partition write")
    shell(f"dd if={tmp} of={dev} bs=4096 2>/dev/null; sync")
    blocks = (len(data) + 4095) // 4096
    got = shell(f"dd if={dev} bs=4096 count={blocks} 2>/dev/null | busybox md5sum").split()[0]
    shell(f"busybox rm -f {tmp}")
    if got != want:
        raise DeviceError(f"partition verify mismatch ({got} != {want})")
    return want
