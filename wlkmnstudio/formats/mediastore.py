"""Marker-gated media scanner — the "fast boot" / skip-DB-scan patch.

Sony's player runs a full `/contents` filesystem crawl on every boot (the blocking
"Creating Database" screen). This patches `libMediaStoreService.so` so the scan worker
only runs the crawl when a marker file (`/data/wlkmn_rescan`) exists; otherwise it skips
straight to the completion callback (so the screen still dismisses — no hang).

A companion boot watcher (see the FastBoot mod) drops that marker whenever a USB
mass-storage session is detected (`/contents` unmounts), so:
  * normal boot   -> no marker  -> crawl skipped -> no "Creating Database", fast boot
  * USB transfer  -> marker set -> crawl runs   -> new music indexed, marker cleared

Mechanism: a tiny stub is written into a `.text` code cave and the scan worker's
`bl <crawl>` is redirected to it. The stub `unlink()`s the marker — which both *checks
existence* and *clears it* in one call (one-shot) — then tail-calls the real crawl if it
existed, else returns 0 (skip). Everything is md5-verified; on an unrecognized build it
raises so the caller aborts cleanly instead of flashing a bad patch.
"""
import hashlib
import struct

MARKER_PATH = "/data/wlkmn_rescan"

# Per-build FILE offsets (== ELF vaddr for the single R-X segment; load base cancels at
# runtime). Keyed by the stock libMediaStoreService.so md5. Add rows for other firmwares.
KNOWN_BUILDS = {
    # NW-A50 (A55/56/57) Walkman One stock
    "d3268ccc423d8369043a378ba26ebe0b": {
        "callsite":   0x134a8,   # `bl <crawl>` inside the scan worker (bytes 0ef044f8)
        "cave":       0x1d4168,  # 4-aligned run of zeros in an executable section
        "crawl":      0x21534,   # the crawl function the worker calls
        "unlink_plt": 0xcfa4,    # unlink() PLT stub (ARM)
    },
}

# The crawl call must be exactly this `bl` for the known build (belt-and-suspenders check).
_CALLSITE_SIG = bytes.fromhex("0ef044f8")

# Thumb code of the stub, branches left as NOPs — patched in _build_stub() once we know
# the cave address. Layout:
#   push {r0-r3,lr}; adr r0,marker; <blx unlink>; cmp r0,#0; pop {r0-r3,lr};
#   beq crawl; movs r0,#0; bx lr;  crawl: <b.w crawl>;  marker: "/data/wlkmn_rescan\0"
_STUB_CODE = bytes.fromhex("0fb505a000bf00bf0028bde80f4001d00020704700bf00bf")
_OFF_BLX = 0x04   # where the `blx unlink` goes
_OFF_BW = 0x14    # where the `b.w crawl` goes
_OFF_STR = 0x18   # marker string (adr r0,#0x14 resolves here)


def _jbits(i1, i2, s):
    return ((i1 ^ 1) ^ s) & 1, ((i2 ^ 1) ^ s) & 1


def _enc_bl(addr, target):        # Thumb->Thumb BL (T1)
    imm = target - (addr + 4)
    s = (imm >> 24) & 1; i1 = (imm >> 23) & 1; i2 = (imm >> 22) & 1
    j1, j2 = _jbits(i1, i2, s)
    return struct.pack("<HH", 0xF000 | (s << 10) | ((imm >> 12) & 0x3FF),
                       0xD000 | (j1 << 13) | (j2 << 11) | ((imm >> 1) & 0x7FF))


def _enc_blx(addr, target):       # Thumb->ARM BLX (target 4-aligned)
    base = (addr + 4) & ~3
    imm = target - base
    s = (imm >> 24) & 1; i1 = (imm >> 23) & 1; i2 = (imm >> 22) & 1
    j1, j2 = _jbits(i1, i2, s)
    return struct.pack("<HH", 0xF000 | (s << 10) | ((imm >> 12) & 0x3FF),
                       0xC000 | (j1 << 13) | (j2 << 11) | (((imm >> 2) & 0x3FF) << 1))


def _enc_bw(addr, target):        # Thumb B.W (T4)
    imm = target - (addr + 4)
    s = (imm >> 24) & 1; i1 = (imm >> 23) & 1; i2 = (imm >> 22) & 1
    j1, j2 = _jbits(i1, i2, s)
    return struct.pack("<HH", 0xF000 | (s << 10) | ((imm >> 12) & 0x3FF),
                       0x9000 | (j1 << 13) | (j2 << 11) | ((imm >> 1) & 0x7FF))


def _build_stub(cave, unlink_plt, crawl):
    body = bytearray(_STUB_CODE) + MARKER_PATH.encode() + b"\x00"
    body[_OFF_BLX:_OFF_BLX + 4] = _enc_blx(cave + _OFF_BLX, unlink_plt)
    body[_OFF_BW:_OFF_BW + 4] = _enc_bw(cave + _OFF_BW, crawl)
    return bytes(body)


# md5s of libMediaStoreService.so already carrying the marker gate (build_gated_service output
# for each known stock). Lets is_gated() recognize an already-installed device.
GATED_BUILDS = {
    "6199936247993fcac26fec6950e7da12",   # gated NW-A50 WM1 build (from d3268ccc… stock)
}


def is_gated(so_bytes):
    """True if these bytes are already the marker-gated build, False if a recognized stock,
    None if the build is unknown (neither stock nor a known gated output)."""
    md5 = hashlib.md5(so_bytes).hexdigest()
    if md5 in GATED_BUILDS:
        return True
    o = KNOWN_BUILDS.get(md5)
    if o is None:
        return None            # unknown build
    return so_bytes[o["callsite"]:o["callsite"] + 4] != _CALLSITE_SIG


def build_gated_service(stock_bytes):
    """Return the marker-gated libMediaStoreService.so bytes. Raises ValueError if the
    stock build isn't recognized or the target signature doesn't match (abort clean)."""
    d = bytearray(stock_bytes)
    md5 = hashlib.md5(bytes(d)).hexdigest()
    o = KNOWN_BUILDS.get(md5)
    if o is None:
        raise ValueError(
            "libMediaStoreService.so build not recognized (md5 %s…). The fast-boot patch "
            "currently supports the NW-A50 Walkman One build only." % md5[:8])
    if d[o["callsite"]:o["callsite"] + 4] != _CALLSITE_SIG:
        raise ValueError("scan-worker crawl call signature mismatch — aborting to avoid a bad patch")
    stub = _build_stub(o["cave"], o["unlink_plt"], o["crawl"])
    if any(b != 0 for b in d[o["cave"]:o["cave"] + len(stub)]):
        raise ValueError("code cave is not empty — aborting")
    d[o["cave"]:o["cave"] + len(stub)] = stub
    d[o["callsite"]:o["callsite"] + 4] = _enc_bl(o["callsite"], o["cave"])
    return bytes(d)


# The boot watcher: sets the rescan marker while /contents is unmounted (USB mass storage
# grabs it — the only time it's unmounted outside diag), so the post-transfer scan crawls.
WATCHER_PATH = "/system/vendor/sony/bin/wlkmn_scanwatch.sh"
WATCHER_SCRIPT = """#!/system/bin/sh
# WLKMN Studio fast-boot DB gate. /contents unmounts only during a USB mass-storage
# session (it stays mounted through a normal boot), so when it's unmounted, drop the
# rescan marker -> the post-session library scan runs. No marker -> scan skips (fast boot).
while true; do
  if ! /sbin/busybox grep -q ' /contents ' /proc/mounts; then
    echo 1 > %s 2>/dev/null
  fi
  /sbin/busybox sleep 1
done
""" % MARKER_PATH

# Boot hook: buildinfo.sh runs early on every normal boot via `exec` in init and lives in
# /system (persistent). setsid detaches the watcher so init doesn't reap it.
HOOK_TARGET = "/system/bin/buildinfo.sh"
_HOOK_MARK = "wlkmn_scanwatch"
HOOK_LINE = ("\n# WLKMN Studio scan-watcher (fast-boot DB gate)\n"
             "if [ -x %s ]; then /sbin/busybox setsid %s >/dev/null 2>&1 & fi\n"
             % (WATCHER_PATH, WATCHER_PATH))


def hook_buildinfo(orig_bytes):
    """Append the watcher launch to buildinfo.sh (idempotent). Returns new bytes."""
    text = orig_bytes.decode("utf-8", "replace")
    if _HOOK_MARK in text:
        return orig_bytes                       # already hooked
    return (text.rstrip() + "\n" + HOOK_LINE).encode("utf-8")


def unhook_buildinfo(cur_bytes):
    """Strip the watcher launch from buildinfo.sh. Returns new bytes."""
    text = cur_bytes.decode("utf-8", "replace")
    if _HOOK_MARK not in text:
        return cur_bytes
    out = []
    skip = 0
    for line in text.splitlines(keepends=True):
        if "WLKMN Studio scan-watcher" in line or _HOOK_MARK in line:
            continue
        out.append(line)
    return "".join(out).encode("utf-8")
