from ..module import Mod, register
from .. import device
from ..formats import mtpdb

DB = "/db/MTPDB.dat"


@register
class FindDuplicates(Mod):
    id = "find_duplicates"
    name = "Find Duplicates"
    category = "QOL"
    status = "built"
    readonly = True
    description = ("Read-only scan of your media database for likely duplicate tracks — same title AND "
                   "identical file size (e.g. the same song copied to both internal storage and the SD "
                   "card). Reports the groups and the space they waste; deletion is left to you.")

    def preview(self, config, ctx):
        groups, wasted = mtpdb.duplicates(device.pull_file(DB))
        if not groups:
            return {"kind": "text", "data": "No duplicate tracks found. Nice, clean library."}
        head = "Found %d duplicated track(s), wasting %s:\n" % (len(groups), mtpdb.human_bytes(wasted))
        rows = ["  %2d× %-40s %s" % (n, (t[:40]), mtpdb.human_bytes(fs))
                for (t, n, fs) in groups[:25]]
        more = "" if len(groups) <= 25 else "\n  … and %d more" % (len(groups) - 25)
        return {"kind": "text", "data": head + "\n".join(rows) + more}
