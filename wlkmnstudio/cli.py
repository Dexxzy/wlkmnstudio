"""WLKMN Studio CLI — headless/scriptable front-end over the same engine as the GUI.

    wlkmn list
    wlkmn detect
    wlkmn monitor
    wlkmn preview <mod> [key=value ...]
    wlkmn apply   <mod> [key=value ...]
    wlkmn revert  <mod>
    wlkmn revert-all
    wlkmn apply-profile <profile.json>
"""
import argparse, os, sys, tempfile
from . import device, ledger, profiles, monitor
from .module import Context, REGISTRY
from . import mods  # noqa: F401  (registers the mods)

BACKUP_DIR = os.path.expanduser("~/.wlkmnstudio/backups")


def _ctx():
    return Context(ledger.Ledger(BACKUP_DIR))


def _opts(pairs):
    cfg = {}
    for p in pairs:
        if "=" in p:
            k, v = p.split("=", 1)
            cfg[k] = v
    return cfg


def _require_device():
    d = device.detect()
    if not d.get("connected"):
        sys.exit("no device on adb")
    if not d.get("root"):
        sys.exit("device is not rooted (adb shell id -> uid=0 required)")
    return d


def cmd_list(a):
    for m in REGISTRY.values():
        tag = " [read-only]" if m.readonly else ""
        print(f"  {m.id:16} {m.category:7} {m.name}{tag}  ({m.status}, risk={m.risk})")


def cmd_detect(a):
    d = device.detect()
    print("  " + ("  ".join(f"{k}={v}" for k, v in d.items()) if d.get("connected") else "no device"))


def cmd_monitor(a):
    _require_device()
    print(monitor.format_status(monitor.bt_status()))


def cmd_preview(a):
    pv = REGISTRY[a.mod]().preview(_opts(a.opt), _ctx())
    if not pv:
        print("(no preview)")
    elif pv["kind"] == "text":
        print(pv["data"])
    else:
        ext = "gif" if pv["kind"] == "gif" else "png"
        out = os.path.join(tempfile.gettempdir(), f"wlkmn_preview_{a.mod}.{ext}")
        open(out, "wb").write(pv["data"])
        print("preview written:", out)


def cmd_apply(a):
    _require_device()
    print(REGISTRY[a.mod]().apply(_opts(a.opt), _ctx()))


def cmd_revert(a):
    REGISTRY[a.mod]().revert(_ctx())
    print("reverted", a.mod)


def cmd_revert_all(a):
    _ctx().ledger.restore_all()
    print("reverted all mods from backup ledger")


def cmd_shot(a):
    _require_device()
    out = a.out or os.path.join(tempfile.gettempdir(), "wlkmn_shot.png")
    device.screenshot(out)
    print("screenshot saved:", out)


def cmd_apply_profile(a):
    _require_device()
    mods_cfg, name = profiles.load(open(a.file).read())
    ctx = _ctx()
    print(f"applying profile '{name}' ({len(mods_cfg)} mods)")
    for mid, cfg in mods_cfg.items():
        if mid in REGISTRY and not REGISTRY[mid].readonly:
            print(" -", REGISTRY[mid]().apply(cfg, ctx))


def main(argv=None):
    p = argparse.ArgumentParser(prog="wlkmn", description="WLKMN Studio — Walkman mod suite (beta)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(func=cmd_list)
    sub.add_parser("detect").set_defaults(func=cmd_detect)
    sub.add_parser("monitor").set_defaults(func=cmd_monitor)
    sp = sub.add_parser("shot", help="capture the live screen (framebuffer) to a PNG")
    sp.add_argument("out", nargs="?", help="output path (default: wlkmn_shot.png in the system temp dir)")
    sp.set_defaults(func=cmd_shot)
    sub.add_parser("revert-all").set_defaults(func=cmd_revert_all)
    for name, fn in (("preview", cmd_preview), ("apply", cmd_apply)):
        sp = sub.add_parser(name)
        sp.add_argument("mod", choices=list(REGISTRY))
        sp.add_argument("opt", nargs="*", help="key=value config options")
        sp.set_defaults(func=fn)
    sp = sub.add_parser("revert")
    sp.add_argument("mod", choices=list(REGISTRY))
    sp.set_defaults(func=cmd_revert)
    sp = sub.add_parser("apply-profile")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_apply_profile)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
