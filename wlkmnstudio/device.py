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


def stat_mode(remote):
    """Octal permission string of a remote file, e.g. '755'. None if it can't be read. Used so a
    restore puts the ORIGINAL mode back — restoring an executable (the player app) as 644 drops the
    execute bit and the watchdog then bootloops the device."""
    try:
        out = shell(f"busybox stat -c %a {remote} 2>/dev/null").strip()
    except DeviceError:
        return None
    if out and all(c in "01234567" for c in out) and 3 <= len(out) <= 4:
        return out
    return None


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


# ---------------------------------------------------------------------------
# Bootloop recovery
# ---------------------------------------------------------------------------
PLAYER_APP = "/system/vendor/sony/bin/HgrmMediaPlayerApp"


def uptime_seconds():
    """Device uptime in whole seconds, or None. Recovery uses it to tell a stable boot (uptime
    keeps climbing) from a reboot loop (it keeps resetting to a few seconds)."""
    try:
        return int(float(shell("cat /proc/uptime", timeout=6).split()[0]))
    except (DeviceError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def _catch_window(timeout=6):
    """Wait up to `timeout`s for adb to see a device — the brief window that opens on each reboot of
    a bootlooping device. True if a device came up."""
    try:
        _run(["wait-for-device"], timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return False
    return bool(devices())


def emergency_restore_player(good_local, on_log=None, remote=PLAYER_APP,
                             stage="/data/.wlkmn_good_app", max_seconds=300):
    """Bootloop rescue. Catches the brief adb window during a reboot loop and re-installs a known-good
    player app with the correct 755 root:root perms, then confirms the device stays up.

    A bad UI theme — or a restore that dropped the execute bit — stops HgrmMediaPlayerApp from
    launching, and the watchdog then reboots the device every ~15s. We stage the good app to /data
    once (it survives the reboots), and on each catch cp it into /system, chmod 755, chown root:root,
    sync, and md5-verify. Success = the app is verified in place AND uptime is climbing with the
    player process alive. Returns True on confirmed-stable, False if it couldn't confirm in time.

    on_log(msg): optional callback for progress lines (the GUI pipes these to a live log).
    """
    log = on_log or (lambda *_: None)
    with open(good_local, "rb") as fh:
        good = fh.read()
    want = md5_bytes(good)
    log(f"good app md5 = {want}  ({len(good) / 1e6:.1f} MB)")
    log("Plug the Walkman in over USB and leave it powered — it will keep rebooting; that's fine. Catching…")
    staged = False
    stable = 0
    deadline = time.time() + max_seconds
    tries = 0
    while time.time() < deadline:
        tries += 1
        if not _catch_window(6):
            continue
        try:
            shell("mount -o rw,remount /system 2>/dev/null; mount -o rw,remount / 2>/dev/null; true",
                  timeout=10)
            if not staged:
                push_bytes(good, stage)          # ~9 MB, once; persists across the reboots
                staged = True
                log("staged good app to /data (survives reboots)")
            shell(f"cp {stage} {remote}; chmod 755 {remote}; "
                  f"chown root:root {remote} 2>/dev/null || chown 0.0 {remote}; sync; true",
                  timeout=20)
            got = md5_remote(remote)
        except DeviceError as e:
            log(f"  window closed mid-write ({str(e)[:60]}); retrying")
            stable = 0
            continue
        if got != want:
            log(f"  md5 still {got[:8]}… retrying")
            stable = 0
            continue
        mode = stat_mode(remote) or "?"
        u = uptime_seconds()
        p = pidof("HgrmMediaPlayerApp")
        log(f"  restored ✓  mode={mode} md5 ok · uptime={u}s player_pid={p}")
        if u and u > 35 and p:
            stable += 1
        else:
            stable = 0
        if stable >= 2:
            log("Device is stable — recovery complete. You can unplug when ready. ✓")
            try:
                shell(f"busybox rm -f {stage}; true")
            except DeviceError:
                pass
            return True
        time.sleep(3)
    log("Could not confirm stability in time. Keep it plugged in and press Start Recovery again.")
    return False
