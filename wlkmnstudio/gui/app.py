"""WLKMN Studio — native tkinter GUI (beta). Sketch is fine.

Device tab shows connection/root/WM1. Each mod gets a tab built from mod.inputs(): file pickers,
color swatches, dropdowns. Preview renders in-window (animated GIF for the boot animation). Apply and
Revert run on a worker thread; a shared log shows progress. Every write is backed up + md5-verified
by the engine.
"""
import os, io, threading, queue, traceback
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from PIL import Image, ImageTk, ImageSequence

from .. import device, ledger, profiles
from ..module import Context, REGISTRY
from .. import mods as _mods  # noqa: F401  (registers the mods)

BACKUP_DIR = os.path.expanduser("~/.wlkmnstudio/backups")


class ImageView(ttk.Label):
    """Shows a static PIL image, or animates a GIF given as bytes."""
    def __init__(self, master):
        super().__init__(master, anchor="center")
        self._frames = []
        self._i = 0
        self._job = None

    def _stop(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def show_image_bytes(self, data):
        self._stop()
        im = Image.open(io.BytesIO(data))
        self._tk = ImageTk.PhotoImage(im)
        self.configure(image=self._tk, text="")

    def show_gif_bytes(self, data):
        self._stop()
        im = Image.open(io.BytesIO(data))
        self._frames = [ImageTk.PhotoImage(f.convert("RGB")) for f in ImageSequence.Iterator(im)]
        self._i = 0
        self._animate()

    def _animate(self):
        if not self._frames:
            return
        self.configure(image=self._frames[self._i], text="")
        self._i = (self._i + 1) % len(self._frames)
        self._job = self.after(40, self._animate)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WLKMN Studio — beta")
        self.geometry("940x680")
        self.dev = {"connected": False}
        self.ledger = ledger.Ledger(BACKUP_DIR)
        self.ctx = Context(self.ledger)
        self.mods = [cls() for cls in REGISTRY.values()]
        self.vars = {}          # mod.id -> {field: tk var}
        self.choicemap = {}     # (mod.id, field) -> {label: value}
        self.q = queue.Queue()
        self._build()
        self.after(150, self._drain)
        self.refresh_device()

    # ---------- UI ----------
    CATEGORY_ORDER = ["Theme", "Audio", "QOL", "System"]

    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        self._logo_img = self._load_logo(height=26)
        if self._logo_img is not None:
            ttk.Label(top, image=self._logo_img).pack(side="left", padx=(0, 12))
        self.status = ttk.Label(top, text="scanning for device…", font=("", 12, "bold"))
        self.status.pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh_device).pack(side="right")
        ttk.Button(top, text="Screenshot", command=self._screenshot).pack(side="right", padx=4)
        ttk.Button(top, text="Revert All", command=self._revert_all).pack(side="right")
        ttk.Button(top, text="Load Profile", command=self._load_profile).pack(side="right", padx=4)
        ttk.Button(top, text="Save Profile", command=self._save_profile).pack(side="right")

        # top-level tabs = categories; each holds a sub-notebook of its mods (17 flat tabs is too many)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8)
        cats = {}
        for mod in self.mods:
            cats.setdefault(mod.category, []).append(mod)
        ordered = self.CATEGORY_ORDER + [c for c in cats if c not in self.CATEGORY_ORDER]
        for cat in ordered:
            if cat not in cats:
                continue
            sub = ttk.Notebook(self.nb)
            for mod in cats[cat]:
                sub.add(self._mod_tab(mod, sub), text=mod.name)
            self.nb.add(sub, text=f"{cat} ({len(cats[cat])})")

        logf = ttk.LabelFrame(self, text="Log", padding=4)
        logf.pack(fill="x", padx=8, pady=6)
        self.log = tk.Text(logf, height=7, wrap="word")
        self.log.pack(fill="x")
        self._log("WLKMN Studio beta. Connect a Walkman One device with USB debugging + root.")

    def _load_logo(self, height=26):
        try:
            p = os.path.join(os.path.dirname(__file__), "..", "assets", "img", "wlkmn.png")
            im = Image.open(p)
            w = max(1, int(im.width * height / im.height))
            return ImageTk.PhotoImage(im.resize((w, height), Image.LANCZOS))
        except Exception:
            return None

    def _mod_tab(self, mod, parent):
        f = ttk.Frame(parent, padding=10)
        ttk.Label(f, text=mod.description, wraplength=880, foreground="#555").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Label(f, text=f"[{mod.category} · risk {mod.risk} · {mod.status}]",
                  foreground="#999").grid(row=1, column=0, columnspan=3, sticky="w")
        self.vars[mod.id] = {}
        r = 2
        for fld in mod.inputs():
            r += 1
            ttk.Label(f, text=fld["label"]).grid(row=r, column=0, sticky="w", pady=3)
            self._field_widget(f, mod, fld, r)
        btns = ttk.Frame(f)
        btns.grid(row=r + 1, column=0, columnspan=3, sticky="w", pady=10)
        if getattr(mod, "readonly", False):
            ttk.Button(btns, text="Read", command=lambda m=mod: self._run(self._preview, m)).pack(side="left")
        else:
            ttk.Button(btns, text="Preview", command=lambda m=mod: self._run(self._preview, m)).pack(side="left")
            ttk.Button(btns, text="Apply", command=lambda m=mod: self._apply(m)).pack(side="left", padx=6)
            ttk.Button(btns, text="Revert", command=lambda m=mod: self._run(self._revert, m)).pack(side="left")
        view = ImageView(f)
        view.grid(row=r + 2, column=0, columnspan=3, pady=8)
        self.vars[mod.id]["_view"] = view
        return f

    def _field_widget(self, parent, mod, fld, r):
        t = fld["type"]
        if t == "file":
            v = tk.StringVar()
            e = ttk.Entry(parent, textvariable=v, width=52)
            e.grid(row=r, column=1, sticky="w")
            ttk.Button(parent, text="Browse…",
                       command=lambda vv=v, fl=fld: self._pick_file(vv, fl)).grid(row=r, column=2, padx=4)
        elif t == "color":
            v = tk.StringVar(value=fld.get("default", "#000000"))
            e = ttk.Entry(parent, textvariable=v, width=12)
            e.grid(row=r, column=1, sticky="w")
            ttk.Button(parent, text="Pick…",
                       command=lambda vv=v: self._pick_color(vv)).grid(row=r, column=2, padx=4, sticky="w")
        elif t == "choice":
            labels = [lbl for _, lbl in fld["options"]]
            self.choicemap[(mod.id, fld["name"])] = {lbl: val for val, lbl in fld["options"]}
            default_label = next(lbl for val, lbl in fld["options"] if val == fld.get("default"))
            v = tk.StringVar(value=default_label)
            ttk.Combobox(parent, textvariable=v, values=labels, state="readonly",
                         width=24).grid(row=r, column=1, sticky="w")
        else:  # int / text
            v = tk.StringVar(value=str(fld.get("default", "")))
            ttk.Entry(parent, textvariable=v, width=12).grid(row=r, column=1, sticky="w")
        self.vars[mod.id][fld["name"]] = v

    def _pick_file(self, var, fld):
        exts = fld.get("accept", "").split(",")
        types = [("Accepted", " ".join("*" + e for e in exts))] if exts and exts[0] else [("All", "*.*")]
        p = filedialog.askopenfilename(filetypes=types + [("All files", "*.*")])
        if p:
            var.set(p)

    def _pick_color(self, var):
        rgb, hx = colorchooser.askcolor(color=var.get())
        if hx:
            var.set(hx)

    # ---------- config ----------
    def _config(self, mod):
        cfg = {}
        for fld in mod.inputs():
            v = self.vars[mod.id][fld["name"]].get()
            if fld["type"] == "choice":
                v = self.choicemap[(mod.id, fld["name"])][v]
            elif fld["type"] == "int":
                v = int(v) if str(v).strip() else fld.get("default")
            elif fld["type"] == "file" and not v:
                continue
            cfg[fld["name"]] = v
        return cfg

    # ---------- device ----------
    def refresh_device(self):
        def work():
            try:
                d = device.detect()
            except Exception as e:
                d = {"connected": False, "error": str(e)}
            self.q.put(("device", d))
        threading.Thread(target=work, daemon=True).start()

    def _set_status(self, d):
        self.dev = d
        if not d.get("connected"):
            self.status.configure(text="⚠ no device — connect USB + enable debugging", foreground="#b00")
        else:
            root = "root ✓" if d.get("root") else "NOT root ✗"
            wm1 = "Walkman One ✓" if d.get("walkman_one") else "WM1? (unverified)"
            col = "#070" if d.get("root") else "#b00"
            self.status.configure(text=f"{d.get('model','?')}  ·  {root}  ·  {wm1}", foreground=col)

    # ---------- actions (threaded) ----------
    def _ready(self):
        if not (self.dev.get("connected") and self.dev.get("root")):
            messagebox.showwarning("Not ready", "Need a connected, rooted device.")
            return False
        return True

    def _apply(self, mod):
        if not self._ready():
            return
        if not messagebox.askyesno("Apply " + mod.name,
                                   f"Flash '{mod.name}' to the device?\nOriginal is backed up first."):
            return
        self._run(lambda m: self._log(m.apply(self._config(m), self.ctx)), mod, verb="Applying")

    def _preview(self, mod):
        pv = mod.preview(self._config(mod), self.ctx)
        if not pv:
            self._log(f"{mod.name}: no preview")
            return
        self.q.put(("preview", (mod.id, pv)))

    def _revert(self, mod):
        mod.revert(self.ctx)
        self._log(f"{mod.name}: reverted from backup ledger")

    # ---------- profiles ----------
    def _all_configs(self):
        return {m.id: self._config(m) for m in self.mods}

    def _save_profile(self):
        p = filedialog.asksaveasfilename(defaultextension=".json",
                                         filetypes=[("WLKMN profile", "*.json")])
        if not p:
            return
        with open(p, "w") as f:
            f.write(profiles.dump(self._all_configs(), name=os.path.basename(p)))
        self._log(f"saved profile → {p}")

    def _load_profile(self):
        p = filedialog.askopenfilename(filetypes=[("WLKMN profile", "*.json"), ("All", "*.*")])
        if not p:
            return
        mods_cfg, name = profiles.load(open(p).read())
        for mid, cfg in mods_cfg.items():
            if mid not in self.vars:
                continue
            mod = next(m for m in self.mods if m.id == mid)
            for fld in mod.inputs():
                if fld["name"] not in cfg:
                    continue
                val = cfg[fld["name"]]
                if fld["type"] == "choice":
                    inv = {v: k for k, v in self.choicemap[(mid, fld["name"])].items()}
                    val = inv.get(val, val)
                self.vars[mid][fld["name"]].set(str(val))
        self._log(f"loaded profile '{name}'")

    def _revert_all(self):
        if not self._ready():
            return
        if not messagebox.askyesno("Revert All",
                                   "Restore ALL modified files/partitions from their backups?"):
            return
        self._log("Reverting all mods…")

        def work():
            try:
                self.ledger.restore_all()
                self.q.put(("log", "reverted all mods from the backup ledger"))
            except Exception as e:
                self.q.put(("log", f"ERROR (revert all): {e}"))
        threading.Thread(target=work, daemon=True).start()

    # ---------- live screenshot ----------
    def _screenshot(self):
        if not self.dev.get("connected"):
            messagebox.showwarning("No device", "Connect a device first.")
            return
        self._log("capturing screen…")

        def work():
            try:
                png = device.screenshot()
                self.q.put(("shot", png))
            except Exception as e:
                self.q.put(("log", f"screenshot failed: {e}"))
        threading.Thread(target=work, daemon=True).start()

    def _show_shot(self, png):
        im = Image.open(io.BytesIO(png))
        scale = min(1.0, 420 / im.width)          # fit a comfortable popup width
        if scale < 1.0:
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        win = tk.Toplevel(self)
        win.title("Live screen")
        photo = ImageTk.PhotoImage(im)
        lbl = ttk.Label(win, image=photo)
        lbl.image = photo                          # keep a reference
        lbl.pack(padx=6, pady=6)

        def save():
            p = filedialog.asksaveasfilename(defaultextension=".png",
                                             filetypes=[("PNG", "*.png")])
            if p:
                with open(p, "wb") as fh:
                    fh.write(png)
                self._log(f"screenshot saved → {p}")
        ttk.Button(win, text="Save PNG…", command=save).pack(pady=(0, 8))
        self._log("screenshot captured")

    def _run(self, fn, mod, verb="Working"):
        self._log(f"{verb}: {mod.name}…")

        def work():
            try:
                fn(mod)
            except Exception as e:
                self.q.put(("log", f"ERROR ({mod.name}): {e}"))
                self.q.put(("log", traceback.format_exc().splitlines()[-1]))
        threading.Thread(target=work, daemon=True).start()

    # ---------- queue pump ----------
    def _drain(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "device":
                    self._set_status(payload)
                elif kind == "log":
                    self._log(payload)
                elif kind == "shot":
                    self._show_shot(payload)
                elif kind == "preview":
                    mid, pv = payload
                    view = self.vars[mid]["_view"]
                    if pv["kind"] == "gif":
                        view.show_gif_bytes(pv["data"]); self._log("preview rendered")
                    elif pv["kind"] == "image":
                        view.show_image_bytes(pv["data"]); self._log("preview rendered")
                    else:  # text
                        self._log(pv["data"])
        except queue.Empty:
            pass
        try:
            self.after(150, self._drain)
        except tk.TclError:
            pass  # window closing

    def _log(self, msg):
        self.log.insert("end", str(msg) + "\n")
        self.log.see("end")


def main():
    # macOS system Python 3.9 ships Tk 8.5, which renders BLANK windows on modern macOS. Fail loudly
    # with a fix instead of showing an empty window.
    if float(tk.TkVersion) < 8.6:
        import sys
        sys.stderr.write(
            "\nWLKMN Studio needs Tk 8.6+ — you have Tk %s, which shows blank windows on macOS.\n"
            "The macOS system Python (/usr/bin/python3) ships the broken Tk 8.5. Use a modern Python:\n"
            "  • Homebrew:  brew install python@3.13 python-tk@3.13   then run with python3.13\n"
            "  • or install Python from python.org (bundles a working Tk)\n\n" % tk.TkVersion)
        sys.exit(1)
    App().mainloop()


if __name__ == "__main__":
    main()
