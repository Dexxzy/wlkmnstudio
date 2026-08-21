from ..module import Mod, register
from .. import device


@register
class StorageInfo(Mod):
    id = "storage_info"
    name = "Storage Info"
    category = "QOL"
    status = "built"
    readonly = True
    description = ("Free space on internal / contents / data, the media-DB size, and how much macOS/"
                   "Windows junk is sitting in /contents. The genesys-db rebuild gets slow when storage "
                   "is full, so this is the first thing to check for boot-time slowness.")

    def preview(self, config, ctx):
        df = device.shell("df /contents /data /system 2>/dev/null").strip()
        junk = device.shell('busybox find /contents -name "._*" 2>/dev/null | busybox wc -l').strip()
        db = device.shell('busybox ls -la $(busybox find / -maxdepth 3 -iname "MTPDB.dat" 2>/dev/null | head -1) 2>/dev/null').strip()
        return {"kind": "text", "data": f"{df}\n\nmedia DB: {db or 'MTPDB.dat not found'}\n"
                                        f"AppleDouble junk files in /contents: {junk}"}
