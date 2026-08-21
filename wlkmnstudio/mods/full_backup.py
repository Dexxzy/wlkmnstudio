import os, time
from ..module import Mod, register
from .. import device

# (kind, remote_path[, size]) — every target any mod can touch
TARGETS = [
    ("file", "/system/media/bootanimation.zip"),
    ("partition", "/dev/block/mmcblk0p12", 0x300000),
    ("file", "/system/bin/mtkbt"),
    ("file", "/system/vendor/sony/bin/HgrmMediaPlayerApp"),
    ("file", "/contents/CFW/settings.txt"),
] + [("file", f"/system/vendor/sony/lib/fonts/{f}") for f in
     ("SST-Roman.otf", "SST-Bold.otf", "SST-Light.otf",
      "SSTUI-Roman.ttf", "SSTUI-Bold.ttf", "SSTUI-Light.ttf")]


@register
class FullBackup(Mod):
    id = "full_backup"
    name = "Full Backup"
    category = "System"
    description = ("Snapshot every mod-touchable target (boot animation, logo partition, mtkbt, the UI "
                   "app, fonts, WM1 settings) to your computer, so you always have a complete revert "
                   "set. Read-only — only pulls from the device.")
    status = "built"
    readonly = True

    def preview(self, config, ctx):
        out = os.path.expanduser(f"~/.wlkmnstudio/snapshots/{time.strftime('%Y%m%d-%H%M%S')}")
        os.makedirs(out, exist_ok=True)
        done, total = [], 0
        for t in TARGETS:
            try:
                if t[0] == "file":
                    data = device.pull_file(t[1])
                    name = t[1].strip("/").replace("/", "_")
                else:
                    data = device.read_partition(t[1], t[2])
                    name = "logo_partition_mmcblk0p12.bin"
                open(os.path.join(out, name), "wb").write(data)
                total += len(data)
                done.append(f"  {name}  ({len(data)//1024} KB)")
            except Exception as e:
                done.append(f"  {t[1]}  — SKIPPED ({e})")
        return {"kind": "text", "data": f"snapshot → {out}  ({total//1024//1024} MB)\n" + "\n".join(done)}
