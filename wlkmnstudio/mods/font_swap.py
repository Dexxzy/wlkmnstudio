from ..module import Mod, register
from .. import device
from ..formats import fonts


@register
class FontSwap(Mod):
    id = "font_swap"
    name = "UI Font"
    category = "Theme"
    description = "Swap the UI font (SST / SST UI families) for a bundled or uploaded typeface."
    risk = "low"
    status = "built"

    def inputs(self):
        return [
            {"name": "regular", "type": "file", "label": "Font — Regular (TTF/OTF or variable)", "accept": ".ttf,.otf"},
            {"name": "bold", "type": "file", "label": "Font — Bold (optional)", "accept": ".ttf,.otf", "optional": True},
            {"name": "light", "type": "file", "label": "Font — Light (optional)", "accept": ".ttf,.otf", "optional": True},
        ]

    def _build(self, config, ctx):
        reg = config.get("regular")
        if not reg:
            raise ValueError("a Regular font is required")
        fw = {400: open(reg, "rb").read()}
        fw[700] = open(config["bold"], "rb").read() if config.get("bold") else fw[400]
        fw[300] = open(config["light"], "rb").read() if config.get("light") else fw[400]
        stock = {fn: ctx.stock_font(fn) for fn in fonts.STOCK_FILES}
        return fonts.build_font_set(fw, stock)

    def apply(self, config, ctx):
        out = self._build(config, ctx)
        for fn, data in out.items():
            ctx.ledger.backup_file("font:" + fn, fonts.FONT_DIR + "/" + fn)
            device.install_file(data, fonts.FONT_DIR + "/" + fn)
        return f"installed {len(out)} font files as SST/SST UI — reboot to apply"

    def revert(self, ctx):
        for fn in fonts.STOCK_FILES:
            ctx.ledger.restore("font:" + fn)
