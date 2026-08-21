"""WLKMN Studio CLI — headless/scriptable front-end over the same engine as the GUI.

    wlkmn list                       # all modules, grouped
    wlkmn detect                     # device / root / Walkman One status
    wlkmn monitor                    # live BT codec/RTP read
    wlkmn shot [out.png]             # grab the live screen
    wlkmn preview <mod> [k=v ...]    # dry-run (no writes)
    wlkmn apply   <mod> [k=v ...]    # back up + flash   (-y to skip the prompt)
    wlkmn revert  <mod>              # restore that mod from the backup ledger
    wlkmn revert-all                 # restore everything
    wlkmn apply-profile <p.json>     # apply a saved profile

Flashing modifies system files on a rooted device and can bootloop it. Every write is
backed up and md5-verified; `revert` restores it. First `apply` shows a one-time risk
notice — accept it interactively or pass --accept-risk (e.g. for scripts).
"""
import argparse
import os
import sys
import tempfile

from . import device, ledger, profiles, monitor, disclaimer
from .module import Context, REGISTRY
from . import mods  # noqa: F401  (registers the mods)

BACKUP_DIR = os.path.expanduser("~/.wlkmnstudio/backups")

CATEGORY_ORDER = ["Theme", "Audio", "QOL", "System"]


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
        sys.exit("✗ no device on adb — plug the Walkman in over USB (do NOT enable USB Mass Storage). "
                 "It must be running Walkman One (that's what enables the connection). Then `wlkmn detect`.")
    if not d.get("root"):
        sys.exit("✗ device is not rooted (adb shell id must be uid=0). WLKMN Studio needs Walkman One + root.")
    return d


def _first_line(text):
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if ln:
            return ln
    return ""


def _ensure_accepted(assume):
    """Show the one-time risk notice before the first flashing action. `assume` short-circuits
    it (from -y / --accept-risk) so scripts aren't blocked."""
    if disclaimer.accepted():
        return
    print("\n" + "=" * 68)
    print("  WLKMN Studio — RISK NOTICE (shown once)")
    print("=" * 68)
    for para in disclaimer.RISK_TEXT.split("\n\n"):
        print("  " + para.replace("\n", "\n  "))
        print()
    print("=" * 68)
    if assume:
        print("  Accepted via --accept-risk / -y.\n")
        disclaimer.mark_accepted()
        return
    if not sys.stdin.isatty():
        sys.exit("  Refusing to flash non-interactively without acceptance. Re-run with --accept-risk.")
    ans = input("  Type 'yes' to accept and continue: ").strip().lower()
    if ans not in ("y", "yes"):
        sys.exit("  Not accepted — nothing was changed.")
    disclaimer.mark_accepted()
    print()


def _confirm(prompt, assume):
    if assume:
        return True
    if not sys.stdin.isatty():
        return True                       # piped/scripted without -y still proceeds (accept gate already passed)
    return input(prompt + " [y/N] ").strip().lower() in ("y", "yes")


def cmd_list(a):
    by_cat = {}
    for m in REGISTRY.values():
        by_cat.setdefault(m.category, []).append(m)
    order = CATEGORY_ORDER + [c for c in by_cat if c not in CATEGORY_ORDER]
    total = 0
    for cat in order:
        if cat not in by_cat:
            continue
        print(f"\n{cat}")
        for m in by_cat[cat]:
            total += 1
            tag = " [read-only]" if getattr(m, "readonly", False) else f"  risk={m.risk}"
            print(f"  {m.id:16}{tag:14} {m.name}")
            desc = _first_line(m.description)
            if desc:
                if len(desc) > 96:
                    desc = desc[:95].rstrip() + "…"
                print(f"      {desc}")
    print(f"\n{total} modules. Use: wlkmn preview <id> … / wlkmn apply <id> …")


def cmd_detect(a):
    d = device.detect()
    if not d.get("connected"):
        print("  no device on adb (plug the Walkman in over USB; do NOT enable USB Mass Storage)")
        return
    root = "root ✓" if d.get("root") else "NOT root ✗"
    wm1 = "Walkman One ✓" if d.get("walkman_one") else "WM1? unverified"
    print(f"  {d.get('model','?')}  ·  {root}  ·  {wm1}  ·  serial {d.get('serial','?')}")


def cmd_monitor(a):
    _require_device()
    print(monitor.format_status(monitor.bt_status()))


def cmd_preview(a):
    pv = REGISTRY[a.mod]().preview(_opts(a.opt), _ctx())
    if not pv:
        print("(no preview for this mod)")
    elif pv["kind"] == "text":
        print(pv["data"])
    else:
        ext = "gif" if pv["kind"] == "gif" else "png"
        out = os.path.join(tempfile.gettempdir(), f"wlkmn_preview_{a.mod}.{ext}")
        with open(out, "wb") as f:
            f.write(pv["data"])
        print(f"preview written → {out}  (open it to see what would be flashed)")


def cmd_apply(a):
    _require_device()
    mod = REGISTRY[a.mod]()
    if getattr(mod, "readonly", False):
        sys.exit(f"'{mod.id}' is read-only — use `wlkmn preview {mod.id}` instead.")
    _ensure_accepted(a.yes)
    print(f"→ {mod.name}  (risk={mod.risk})")
    desc = _first_line(mod.description)
    if desc:
        print(f"  {desc}")
    print(f"  {disclaimer.SHORT}")
    if not _confirm(f"  Apply '{mod.id}' to the device?", a.yes):
        sys.exit("  cancelled — nothing changed.")
    print("  " + mod.apply(_opts(a.opt), _ctx()))
    print(f"  ✓ done. Reboot to see it (`wlkmn apply reboot_util` or power-cycle).  "
          f"Undo: `wlkmn revert {mod.id}`")


def cmd_revert(a):
    REGISTRY[a.mod]().revert(_ctx())
    print(f"✓ reverted {a.mod} from the backup ledger. Reboot to apply the restore.")


def cmd_revert_all(a):
    if not _confirm("Restore ALL modified files/partitions from their backups?", a.yes):
        sys.exit("cancelled.")
    _ctx().ledger.restore_all()
    print("✓ reverted all mods from the backup ledger. Reboot to apply.")


def cmd_shot(a):
    _require_device()
    out = a.out or os.path.join(tempfile.gettempdir(), "wlkmn_shot.png")
    device.screenshot(out)
    print("screenshot saved →", out)


def cmd_apply_profile(a):
    _require_device()
    mods_cfg, name = profiles.load(open(a.file).read())
    appliable = [mid for mid in mods_cfg if mid in REGISTRY and not REGISTRY[mid].readonly]
    _ensure_accepted(a.yes)
    print(f"profile '{name}' — will apply {len(appliable)} mods: {', '.join(appliable)}")
    if not _confirm("Apply all of them now?", a.yes):
        sys.exit("cancelled.")
    ctx = _ctx()
    for mid in appliable:
        print(" -", REGISTRY[mid]().apply(mods_cfg[mid], ctx))
    print("✓ profile applied. Reboot to see it.")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="wlkmn", description="WLKMN Studio — Sony Walkman mod suite (beta). Flashes a rooted "
        "Walkman One device; every change is backed up and revertible.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list all modules, grouped by category").set_defaults(func=cmd_list)
    sub.add_parser("detect", help="show device / root / Walkman One status").set_defaults(func=cmd_detect)
    sub.add_parser("monitor", help="live BT codec / RTP read").set_defaults(func=cmd_monitor)
    sp = sub.add_parser("shot", help="capture the live screen (framebuffer) to a PNG")
    sp.add_argument("out", nargs="?", help="output path (default: wlkmn_shot.png in the temp dir)")
    sp.set_defaults(func=cmd_shot)

    sp = sub.add_parser("preview", help="dry-run a mod (no device writes)")
    sp.add_argument("mod", choices=list(REGISTRY))
    sp.add_argument("opt", nargs="*", help="key=value config options")
    sp.set_defaults(func=cmd_preview)

    sp = sub.add_parser("apply", help="back up + flash a mod")
    sp.add_argument("mod", choices=list(REGISTRY))
    sp.add_argument("opt", nargs="*", help="key=value config options")
    sp.add_argument("-y", "--yes", action="store_true", help="skip the confirm prompt")
    sp.add_argument("--accept-risk", dest="yes", action="store_true",
                    help="accept the one-time risk notice non-interactively")
    sp.set_defaults(func=cmd_apply)

    sp = sub.add_parser("revert", help="restore a mod from its backup")
    sp.add_argument("mod", choices=list(REGISTRY))
    sp.set_defaults(func=cmd_revert)

    sp = sub.add_parser("revert-all", help="restore everything from the backup ledger")
    sp.add_argument("-y", "--yes", action="store_true", help="skip the confirm prompt")
    sp.set_defaults(func=cmd_revert_all)

    sp = sub.add_parser("apply-profile", help="apply a saved profile of mods")
    sp.add_argument("file")
    sp.add_argument("-y", "--yes", action="store_true", help="skip prompts")
    sp.add_argument("--accept-risk", dest="yes", action="store_true", help=argparse.SUPPRESS)
    sp.set_defaults(func=cmd_apply_profile)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
