import re
from ..module import Mod, register
from .. import device
from ..formats import viewstyle

APP = "/system/vendor/sony/bin/HgrmMediaPlayerApp"

# level -> (x divisor, y divisor). duration = distance / divisor, so HIGHER divisor = FASTER scroll.
# keep x != y within a level so the find-strings stay unambiguous on re-apply.
LEVELS = {
    "slower":  ("2.0", "2.5"),
    "normal":  ("3.1", "3.9"),   # stock
    "faster":  ("4.5", "5.5"),
    "fastest": ("6.0", "7.0"),
}
X_RE = re.compile(rb"targetX\) / (\d\.\d)")
Y_RE = re.compile(rb"targetY\) / (\d\.\d)")


@register
class MarqueeSpeed(Mod):
    id = "marquee_speed"
    name = "Marquee Scroll Speed"
    category = "Theme"
    risk = "med"
    status = "built"
    description = ("Change how fast long titles scroll (the marquee) in the player. Edits the two "
                   "scroll-speed divisors in the app's QML — higher = faster. Small, reversible value "
                   "swap (proven method, not the bootloop-prone stuff). Reboot / restart the player to "
                   "see it.")

    def inputs(self):
        return [{"name": "speed", "type": "choice", "label": "Scroll speed", "default": "normal",
                 "options": [("slower", "Slower"), ("normal", "Normal (stock)"),
                             ("faster", "Faster"), ("fastest", "Fastest")]}]

    def _current(self, data):
        for _, _, out in viewstyle.iter_blobs(data):
            mx = X_RE.search(out)
            if mx:
                my = Y_RE.search(out)
                return mx.group(1).decode(), (my.group(1).decode() if my else None)
        return None, None

    def _plan(self, data, level):
        tx, ty = LEVELS[level]
        cx, cy = self._current(data)
        if cx is None:
            raise RuntimeError("marquee speed site not found — app build differs")
        sm = {}
        if cx != tx:
            sm["/ %s" % cx] = "/ %s" % tx
        if cy and cy != ty:
            sm["/ %s" % cy] = "/ %s" % ty
        return sm, (cx, cy), (tx, ty)

    def preview(self, config, ctx):
        sm, cur, tgt = self._plan(device.pull_file(APP), config.get("speed", "normal"))
        if not sm:
            return {"kind": "text", "data": "Marquee already at that speed (X=%s Y=%s)." % cur}
        return {"kind": "text", "data": "marquee speed  X %s→%s   Y %s→%s   (higher = faster; reboot "
                "to see it)" % (cur[0], tgt[0], cur[1], tgt[1])}

    def apply(self, config, ctx):
        data = device.pull_file(APP)
        sm, cur, tgt = self._plan(data, config.get("speed", "normal"))
        if not sm:
            return "Marquee already at that speed — nothing to do."
        new, stats = viewstyle.patch(data, strmap=sm)
        ctx.ledger.backup_file(self.id, APP)
        device.install_file(new, APP, mode="755")
        return ("Marquee speed set (X=%s Y=%s) across %d blob(s). Reboot / restart the player." %
                (tgt[0], tgt[1], stats["blobs"]))

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
