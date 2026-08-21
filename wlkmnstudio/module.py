"""Mod base class, shared Context, and a registry. Every mod implements the same shape:
    inputs()  -> UI field schema
    preview() -> {'kind','data'} for the GUI (optional)
    apply()   -> backup targets via ctx.ledger, then write; return a summary string
    revert()  -> restore its targets from the ledger
"""
import os
from . import device

REGISTRY = {}


def register(cls):
    REGISTRY[cls.id] = cls
    return cls


class Context:
    """Holds the ledger + a cache of stock assets pulled from the device, so multiple mods share
    one pull of bootanimation.zip / logo.bin / the fonts."""
    def __init__(self, ledger):
        self.ledger = ledger
        self._cache = {}

    def stock_bootanim(self):
        if "boot" not in self._cache:
            self._cache["boot"] = device.pull_file("/system/media/bootanimation.zip")
        return self._cache["boot"]

    def stock_logo(self):
        if "logo" not in self._cache:
            from .formats.mtklogo import PART_SIZE
            self._cache["logo"] = device.read_partition("/dev/block/mmcblk0p12", PART_SIZE)
        return self._cache["logo"]

    def stock_font(self, filename):
        key = "font:" + filename
        if key not in self._cache:
            self._cache[key] = device.pull_file("/system/vendor/sony/lib/fonts/" + filename)
        return self._cache[key]


class Mod:
    id = ""
    name = ""
    category = ""          # Theme | QOL | Audio | System
    description = ""
    risk = "low"           # low | med | high
    status = "built"       # built | shipped | prototype | research
    readonly = False       # diagnostics/monitors: preview only, no apply/revert (no device writes)

    def inputs(self):
        return []

    def preview(self, config, ctx):
        return None

    def apply(self, config, ctx):
        raise NotImplementedError

    def revert(self, ctx):
        raise NotImplementedError
