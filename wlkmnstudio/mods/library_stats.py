from ..module import Mod, register
from .. import device
from ..formats import mtpdb

DB = "/db/MTPDB.dat"


@register
class LibraryStats(Mod):
    id = "library_stats"
    name = "Library Stats"
    category = "QOL"
    status = "built"
    readonly = True
    description = ("Read-only summary of your media library from the on-device database "
                   "(/db/MTPDB.dat): track count and formats, hi-res tracks, artists / albums / genres, "
                   "total size, year range, and the internal-vs-SD-card split. Nothing is written.")

    def preview(self, config, ctx):
        s = mtpdb.stats(device.pull_file(DB))
        gb = mtpdb.human_bytes
        fmts = ", ".join("%s %d" % (e, n) for e, n in s["by_format"].items()
                         if e in mtpdb.AUDIO_EXTS) or "—"
        internal = sum(v for k, v in s["storage"].items() if k != 2)
        sd = s["storage"].get(2, 0)
        rows = [
            "Tracks        %d   (%s)" % (s["tracks"], fmts),
            "Hi-Res        %d" % s["hi_res"],
            "Size          %s audio  ·  %s total (incl. art)" % (gb(s["audio_bytes"]), gb(s["total_bytes"])),
            "Artists       %d   (album artists %d)" % (s["artists"], s["album_artists"]),
            "Albums        %d" % s["albums"],
            "Genres        %d   ·  Composers %d" % (s["genres"], s["composers"]),
        ]
        if s["year_min"] and s["year_max"]:
            rows.append("Years         %s – %s" % (s["year_min"], s["year_max"]))
        rows.append("Storage       internal %d  ·  SD card %d" % (internal, sd))
        return {"kind": "text", "data": "Media library\n" + "\n".join("  " + r for r in rows)}
