"""Live Bluetooth/RTP monitor — reads mtkbt's per-connection RTP session state from /proc/pid/mem.

From the RTP RE: the session array base is at link vaddr 0x1caee4 (stride 0x669c); within a struct,
+0x10 = RTP sequence (u16), +0x14 = RTP timestamp (u32). Sampling the timestamp/sequence deltas over a
short window shows whether audio is streaming AND whether the AirPods fix is active (fixed = timestamp
advances by SAMPLES ~1536/packet; unfixed = by BYTES ~6144/packet). Read-only — no writes.
"""
import time
from . import device

RTP_BASE_VADDR = 0x1caee4
STRIDE = 0x669c
OFF_SEQ = 0x10
OFF_TS = 0x14


def _u(b):
    return int.from_bytes(b, "little")


def bt_status(conn=0, window=0.5):
    pid = device.pidof("mtkbt")
    if not pid:
        return {"running": False, "text": "mtkbt not running"}
    base = device.module_base(pid, "/system/bin/mtkbt")
    if base is None:
        return {"running": True, "pid": pid, "text": "could not resolve mtkbt load base"}
    st = base + RTP_BASE_VADDR + conn * STRIDE
    seq1 = _u(device.read_mem(pid, st + OFF_SEQ, 2))
    ts1 = _u(device.read_mem(pid, st + OFF_TS, 4))
    time.sleep(window)
    seq2 = _u(device.read_mem(pid, st + OFF_SEQ, 2))
    ts2 = _u(device.read_mem(pid, st + OFF_TS, 4))
    dseq = (seq2 - seq1) & 0xffff
    dts = (ts2 - ts1) & 0xffffffff
    streaming = dseq > 0 or dts > 0
    per_pkt = (dts / dseq) if dseq else 0
    if not streaming:
        fix = "idle (play A2DP audio to a BT sink to read live)"
    elif 1400 <= per_pkt <= 1700:
        fix = "AirPods fix ACTIVE (timestamp counts samples ✓)"
    elif 5800 <= per_pkt <= 6500:
        fix = "AirPods fix NOT active (timestamp counts bytes ✗)"
    else:
        fix = f"streaming (ts/pkt≈{per_pkt:.0f})"
    return {"running": True, "pid": pid, "base": hex(base), "seq_delta": dseq, "ts_delta": dts,
            "streaming": streaming, "text": fix}


def format_status(s):
    if not s.get("running"):
        return s["text"]
    lines = [f"mtkbt pid {s['pid']}  base {s.get('base','?')}",
             f"Δseq={s.get('seq_delta','?')}  Δts={s.get('ts_delta','?')} over the sample window",
             s["text"]]
    return "\n".join(lines)
