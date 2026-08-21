# Contributing to WLKMN Studio

Thanks for wanting to help! This is a tool that flashes system files on a rooted Sony Walkman, so
**safety is the whole point** — every mod backs up its target, md5-verifies its write, and can be
reverted. Keep that contract intact and you can't go too far wrong.

## Dev setup
```bash
git clone https://github.com/Dexxzy/wlkmnstudio.git
cd wlkmnstudio
python -m pip install -r requirements.txt
python tests/test_engine.py     # should print "ALL ENGINE TESTS PASSED"
python run.py                   # launch the GUI
```
The engine tests are pure format/codec/patch logic — **no device, adb, or Tk needed** — so they run
in CI and locally without a Walkman plugged in. Please keep them passing.

## How the code is laid out
- **`wlkmnstudio/formats/`** — the reverse-engineered codecs and binpatch builders (boot animation,
  MTK logo, fonts, the `viewstyle` QML palette rewriter, the `mediastore` Fast Boot patch). Pure
  functions on `bytes` → `bytes`; this is what the tests cover.
- **`wlkmnstudio/module.py`** — the `Mod` base class + registry. Every mod is a small class with
  `inputs()` / `preview()` / `apply()` / `revert()`, sharing one device engine and a backup ledger.
- **`wlkmnstudio/mods/`** — one file per mod; importing it registers the mod via `@register`.
- **`wlkmnstudio/device.py`** — the adb wrapper (partition dd-staging, `install_file`, framebuffer
  screenshot, md5 everywhere). `wlkmnstudio/adb_setup.py` finds/auto-downloads adb.
- **`wlkmnstudio/gui/app.py`** + **`cli.py`** — the two front-ends over the same engine.

## Adding a mod
1. Put the byte-level logic in `wlkmnstudio/formats/` as pure functions and **add a test** in
   `tests/test_engine.py` (golden bytes are ideal — see `test_fast_boot_patch`).
2. Add `wlkmnstudio/mods/your_mod.py`:
   ```python
   from ..module import Mod, register
   from .. import device

   @register
   class YourMod(Mod):
       id = "your_mod"; name = "Your Mod"; category = "Theme"  # Theme|Audio|QOL|System
       risk = "low"                                            # low|med|high
       description = "One clear sentence about what it does."
       def inputs(self): return [ ... ]                        # UI fields (see other mods)
       def apply(self, config, ctx):
           data = device.pull_file(TARGET)                     # pull the ORIGINAL
           new  = build(data, config)                          # your format function
           ctx.ledger.backup_file(self.id, TARGET)             # back up BEFORE writing
           device.install_file(new, TARGET, mode="755")        # writes + md5-verifies
           return "done — reboot to see it"
       def revert(self, ctx): ctx.ledger.restore(self.id)
   ```
3. Register it in `wlkmnstudio/mods/__init__.py`.

**The rules that keep it safe:** always `backup_file` *before* `install_file`; always restore the
**original file mode** (executables under `/bin/` must be `755` — restoring the player app as `644`
drops the execute bit and bootloops); and **verify the target before patching** — read the exact bytes
you expect and `raise` if they aren't there, so an unrecognized build aborts instead of getting a bad
write. See `adding-firmware` below for the pattern.

## Adding another firmware / model to a binpatch mod
The binpatch mods (Fast Boot, the audio patches) are **md5-gated**: they only touch a build they
recognize, and abort cleanly otherwise. To add support for a new Walkman One build:

1. Pull the target from the new device, e.g.
   `adb pull /system/vendor/sony/lib/libMediaStoreService.so` and `md5sum` it.
2. Re-do the analysis for that build (Ghidra headless + the capstone helpers documented in
   `../NOTES.md`) to find the same anchors — for Fast Boot that's the crawl call site, a `.text` code
   cave, the crawl function, and the `unlink` PLT stub (all as **file offsets**).
3. Add a row to `KNOWN_BUILDS` in `wlkmnstudio/formats/mediastore.py` keyed by that md5, and a golden
   test if you can. That's it — everything else (build, install, revert) is shared.

If you don't want to reverse anything, opening an issue with your device model + the md5 of the target
file is genuinely useful.

## Pull requests
- Keep the tests green (`python tests/test_engine.py`); CI runs them on 3.10 / 3.12 / 3.13.
- Match the surrounding style (it's plain, comment-light-but-purposeful stdlib Python).
- If a mod writes to the device, test the **apply → reboot → revert** loop on real hardware and say so
  in the PR. When in doubt, mark it higher risk.
