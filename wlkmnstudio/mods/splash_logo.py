import io
from PIL import Image
from ..module import Mod, register
from .. import device
from ..formats import mtklogo
from ..util import hex2rgb


@register
class SplashLogo(Mod):
    id = "splash_logo"
    name = "Power-on Splash"
    category = "Theme"
    description = "Replace the orange WALKMAN power-on logo (logo partition) with your own."
    risk = "med"
    status = "built"
    DEV = "/dev/block/mmcblk0p12"

    def inputs(self):
        return [
            {"name": "logo", "type": "file", "label": "Logo (PNG, transparent)", "accept": ".png"},
            {"name": "width", "type": "int", "label": "Width (px)", "default": 244},
            {"name": "bg", "type": "color", "label": "Background", "default": "#000000"},
        ]

    def _build(self, config, ctx):
        stock = ctx.stock_logo()
        if not config.get("logo"):
            raise ValueError("Select a logo PNG first.")
        logo = Image.open(config["logo"])
        img0 = mtklogo.build_splash(logo, int(config.get("width", 244)), hex2rgb(config.get("bg", "#000000")))
        new = mtklogo.replace_img0(stock, img0)
        if not mtklogo.verify_rebuild(stock, new):
            raise RuntimeError("logo partition rebuild failed verification — aborting")
        return new

    def preview(self, config, ctx):
        try:
            img = mtklogo.decode_img(self._build(config, ctx), 0)
        except ValueError as e:
            return {"kind": "text", "data": str(e)}
        b = io.BytesIO(); img.resize((240, 427)).save(b, "PNG")
        return {"kind": "image", "data": b.getvalue()}

    def apply(self, config, ctx):
        new = self._build(config, ctx)
        ctx.ledger.backup_partition(self.id, self.DEV, mtklogo.PART_SIZE)
        md5 = device.write_partition(new, self.DEV)
        return f"splash flashed to {self.DEV} (md5 {md5[:8]}…) — reboot to see it"

    def revert(self, ctx):
        ctx.ledger.restore(self.id)
