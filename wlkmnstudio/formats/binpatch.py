"""Generic byte-pattern patch for the mtkbt ELF (and future binaries).

Same approach as the shipped AirPods fix: search for an exact byte pattern and replace it in place.
The pattern MUST occur exactly once (0 = build differs, >1 = ambiguous) so we never corrupt the wrong
site. Callers keep a backup + verify md5 via the device engine.
"""


class PatchError(Exception):
    pass


def patch(data, find, replace):
    """Return (new_bytes, file_offset). find/replace must be equal length and find must be unique."""
    if len(find) != len(replace):
        raise PatchError("find/replace length mismatch")
    n = data.count(find)
    if n == 0:
        raise PatchError("pattern not found — firmware build differs")
    if n > 1:
        raise PatchError(f"pattern found {n}× (ambiguous) — aborting")
    i = data.find(find)
    return data[:i] + replace + data[i + len(find):], i


def state(data, find, replace):
    """'patched' if the replacement is present, 'stock' if the original pattern is, else 'unknown'."""
    if data.count(replace):
        return "patched"
    if data.count(find):
        return "stock"
    return "unknown"
