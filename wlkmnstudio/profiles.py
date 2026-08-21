"""Profiles: save/load a set of mod configs as JSON.

A profile is the shareable/reusable unit — {name, mods: {mod_id: {field: value}}}. For the beta it
stores your settings (including file paths) locally; bundling the actual assets (logo/gif/fonts) into a
self-contained pack is a v2 item toward the wlkmn.studio gallery.
"""
import json

VERSION = 1


def dump(mod_configs, name="untitled"):
    return json.dumps({"name": name, "version": VERSION, "mods": mod_configs}, indent=2)


def load(text):
    obj = json.loads(text)
    if obj.get("version") != VERSION:
        # forward-compatible: accept but note
        pass
    return obj.get("mods", {}), obj.get("name", "untitled")
