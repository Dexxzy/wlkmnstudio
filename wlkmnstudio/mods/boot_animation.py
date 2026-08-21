from PIL import Image
from ..module import Mod, register
from .. import device
from ..formats import bootanim
from ..util import hex2rgb


@register
class BootAnimation(Mod):
    id = "boot_animation"
    name = "Boot Animation"
    category = "Theme"
    description = "Replace the boot animation with your own GIF, or the WLKMN squish→waves intro."
    risk = "low"
    status = "built"
    REMOTE = "/system/media/bootanimation.zip"

    def inputs(self):
        return [
            {"name": "mode", "type": "choice", "label": "Source", "default": "gif",
             "options": [("gif", "Upload a GIF"), ("logo_waves", "Logo → waves")]},
            {"name": "gif", "type": "file", "label": "GIF file", "accept": ".gif", "when": {"mode": "gif"}},
            {"name": "logo", "type": "file", "label": "Logo (PNG)", "accept": ".png", "when": {"mode": "logo_waves"}},
            {"name": "accent", "type": "color", "label": "Accent", "default": "#cc516c", "when": {"mode": "logo_waves"}},
            {"name": "bg", "type": "color", "label": "Background", "default": "#000000"},
            {"name": "width", "type": "int", "label": "Logo width (px)", "default": 244, "when": {"mode": "logo_waves"}},
        ]

    def _build_zip(self, config, ctx):
        stock = ctx.stock_bootanim()
        bg = hex2rgb(config.get("bg", "#000000"))
        if config.get("mode", "gif") == "gif":
            if not config.get("gif"):
                raise ValueError("Select a GIF file first.")
            return bootanim.build_from_gif(stock, config["gif"], bg)
        if not config.get("logo"):
            raise ValueError("Select a logo PNG first.")
        logo = Image.open(config["logo"])
        return bootanim.build_from_logo(stock, logo, hex2rgb(config.get("accent", "#cc516c")),
                                        bg, int(config.get("width", 244)))

    def preview(self, config, ctx):
        try:
            return {"kind": "gif", "data": bootanim.preview_gif(self._build_zip(config, ctx))}
        except ValueError as e:
            return {"kind": "text", "data": str(e)}

    def apply(self, config, ctx):
        zip_bytes = self._build_zip(config, ctx)
        ctx.ledger.backup_file(self.id, self.REMOTE)
        md5 = device.install_file(zip_bytes, self.REMOTE)
        return f"boot animation flashed ({len(zip_bytes)//1024//1024}MB, md5 {md5[:8]}…) — reboot to see it"

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
