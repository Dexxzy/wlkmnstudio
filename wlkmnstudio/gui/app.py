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
ACCEPT_FLAG = os.path.expanduser("~/.wlkmnstudio/accepted")

# Dark palette with high-contrast (white) text — the default ttk 'aqua'/'default' themes render
# low-contrast gray-on-white that's hard to read, so we force 'clam' + these colors everywhere.
BG    = "#1e1f22"   # window background
BG2   = "#2a2c30"   # inputs / cards / buttons
BG3   = "#141518"   # log wells
BORDER = "#3a3d42"
FG    = "#f5f6f7"   # primary text — near-white, the main readability fix
SUB   = "#c7ccd4"   # secondary text (still light, readable on dark)
MUTED = "#9aa0a8"   # de-emphasized meta
ACC   = "#4da3ff"
OK    = "#4ade80"
ERR   = "#ff6b6b"

RISK_TEXT = (
    "WLKMN Studio modifies system files and partitions on your rooted Sony Walkman. "
    "Flashing can bootloop or otherwise damage your device.\n\n"
    "Every change is backed up and md5-verified and can be reverted from within the app — but "
    "recovery may still require reinstalling Walkman One, and some actions carry inherent risk.\n\n"
    "This software is provided AS IS, with NO WARRANTY. You use it entirely AT YOUR OWN RISK. "
    "The authors accept NO liability for any damage, data loss, or bricking.\n\n"
    "It requires Walkman One firmware on a rooted device and is not affiliated with or endorsed by Sony.\n\n"
    "By continuing you confirm that you understand these risks and accept full responsibility."
)


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
        self.withdraw()          # stay hidden until the risk agreement is accepted
        self.title("WLKMN Studio — beta")
        self.geometry("940x680")
        self._apply_theme()
        self.dev = {"connected": False}
        self.ledger = ledger.Ledger(BACKUP_DIR)
        self.ctx = Context(self.ledger)
        self.mods = [cls() for cls in REGISTRY.values()]
        self.vars = {}          # mod.id -> {field: tk var}
        self.choicemap = {}     # (mod.id, field) -> {label: value}
        self.q = queue.Queue()
        self._build()
        self.declined = not self._accept_risk()   # modal gate; deiconifies on accept
        if self.declined:
            self.after(0, self.destroy)
            return
        self.after(150, self._drain)
        self.refresh_device()

    def _apply_theme(self):
        """Dark theme with white text. ttk's macOS 'aqua' theme ignores background/foreground on
        most widgets, so switch to 'clam' (fully colorable) and set high-contrast colors app-wide."""
        self.configure(bg=BG)
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", background=BG, foreground=FG, fieldbackground=BG2,
                     bordercolor=BORDER, lightcolor=BG2, darkcolor=BG2, troughcolor=BG2)
        st.configure("TFrame", background=BG)
        st.configure("TLabel", background=BG, foreground=FG)
        st.configure("TLabelframe", background=BG, bordercolor=BORDER)
        st.configure("TLabelframe.Label", background=BG, foreground=SUB)
        st.configure("TButton", background=BG2, foreground=FG, bordercolor=BORDER,
                     focuscolor=BG, padding=(10, 5))
        st.map("TButton", background=[("active", BORDER), ("pressed", BORDER)],
               foreground=[("disabled", "#666a70")])
        # recovery button: reddish so it reads as the emergency action
        st.configure("Danger.TButton", background="#5a2530", foreground="#ffdada")
        st.map("Danger.TButton", background=[("active", "#7a2f3e"), ("pressed", "#7a2f3e")])
        st.configure("TCheckbutton", background=BG, foreground=FG,
                     indicatorbackground=BG2, indicatorforeground=FG, bordercolor=BORDER)
        st.map("TCheckbutton", background=[("active", BG)], foreground=[("disabled", MUTED)],
               indicatorbackground=[("selected", ACC), ("active", "#33363c")],
               indicatorforeground=[("selected", "#0b0c0e")])
        st.configure("TNotebook", background=BG, bordercolor=BORDER)
        st.configure("TNotebook.Tab", background=BG2, foreground=SUB, padding=(12, 5))
        st.map("TNotebook.Tab", background=[("selected", BG)], foreground=[("selected", FG)])
        st.configure("TEntry", fieldbackground=BG2, foreground=FG, insertcolor=FG, bordercolor=BORDER)
        st.map("TEntry", fieldbackground=[("readonly", BG2)])
        st.configure("TCombobox", fieldbackground=BG2, foreground=FG, background=BG2,
                     arrowcolor=FG, bordercolor=BORDER)
        st.map("TCombobox", fieldbackground=[("readonly", BG2)], foreground=[("readonly", FG)],
               selectbackground=[("readonly", BG2)], selectforeground=[("readonly", FG)])
        # popup listbox of comboboxes (a Tk, not ttk, widget)
        self.option_add("*TCombobox*Listbox.background", BG2)
        self.option_add("*TCombobox*Listbox.foreground", FG)
        self.option_add("*TCombobox*Listbox.selectBackground", ACC)

    def _accept_risk(self):
        """Modal risk agreement shown before the app is usable. Remembered after first accept.
        Returns True if accepted, False if the user quit."""
        if os.path.exists(ACCEPT_FLAG):
            self.deiconify()
            return True
        dlg = tk.Toplevel(self)
        dlg.title("WLKMN Studio — Risk Agreement")
        dlg.geometry("560x460")
        dlg.transient(self)
        dlg.resizable(False, False)
        # NOTE: the main window is withdrawn here, and a Toplevel transient to a *withdrawn* parent
        # never maps on macOS (winfo_viewable == 0) — the disclaimer would be invisible. Force it to
        # map + raise before grabbing (grab_set on an unmapped window is also unreliable).
        result = {"ok": False}
        dlg.configure(bg=BG)
        ttk.Label(dlg, text="Before you continue", font=("", 15, "bold")).pack(pady=(16, 4))
        ttk.Label(dlg, text="Read and accept the risk to use WLKMN Studio.",
                  foreground=SUB).pack()
        body = tk.Text(dlg, wrap="word", height=14, relief="flat", padx=10, pady=8,
                       bg=BG2, fg=FG, insertbackground=FG, highlightthickness=0)
        body.insert("1.0", RISK_TEXT)
        body.configure(state="disabled")
        body.pack(padx=16, pady=10, fill="both", expand=True)
        agree = tk.BooleanVar(value=False)
        ttk.Checkbutton(dlg, text="I understand and accept the risk", variable=agree).pack()
        btns = ttk.Frame(dlg)
        btns.pack(pady=12)

        def accept():
            if not agree.get():
                messagebox.showwarning("Please confirm", "Tick the box to accept the risk.", parent=dlg)
                return
            try:
                os.makedirs(os.path.dirname(ACCEPT_FLAG), exist_ok=True)
                open(ACCEPT_FLAG, "w").write("accepted\n")
            except OSError:
                pass
            result["ok"] = True
            dlg.destroy()

        def quit_():
            dlg.destroy()

        ttk.Button(btns, text="Quit", command=quit_).pack(side="left", padx=8)
        ttk.Button(btns, text="I Accept — Continue", command=accept).pack(side="left", padx=8)
        dlg.protocol("WM_DELETE_WINDOW", quit_)
        # force the dialog to actually appear (see NOTE above), then make it modal
        dlg.deiconify()
        dlg.lift()
        dlg.attributes("-topmost", True)
        dlg.update_idletasks()
        dlg.update()
        dlg.after(300, lambda: dlg.attributes("-topmost", False))
        dlg.focus_force()
        try:
            dlg.grab_set()
        except tk.TclError:
            pass
        self.wait_window(dlg)
        if result["ok"]:
            self.deiconify()
        return result["ok"]

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
        ttk.Button(top, text="🚑 Bootloop Recovery", style="Danger.TButton",
                   command=self._recovery_dialog).pack(side="left", padx=16)
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
        self.log = tk.Text(logf, height=7, wrap="word", bg=BG3, fg=FG,
                           insertbackground=FG, relief="flat", highlightthickness=0)
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
        ttk.Label(f, text=mod.description, wraplength=880, foreground=SUB).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Label(f, text=f"[{mod.category} · risk {mod.risk} · {mod.status}]",
                  foreground=MUTED).grid(row=1, column=0, columnspan=3, sticky="w")
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
            self.status.configure(text="⚠ no device — connect USB + enable debugging", foreground=ERR)
        else:
            root = "root ✓" if d.get("root") else "NOT root ✗"
            wm1 = "Walkman One ✓" if d.get("walkman_one") else "WM1? (unverified)"
            col = OK if d.get("root") else ERR
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

    # ---------- bootloop recovery ----------
    def _recovery_source(self):
        """Best known-good player-app backup to restore: the most recent ledger backup for the
        player app whose .bak file still exists (that's the app as it was right before the last
        flash — the good one)."""
        cands = [e for e in self.ledger.entries
                 if e.get("remote") == device.PLAYER_APP and os.path.exists(e.get("backup", ""))]
        cands.sort(key=lambda e: e.get("ts", 0), reverse=True)
        return cands[0]["backup"] if cands else ""

    def _recovery_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Bootloop Recovery")
        dlg.geometry("640x560")
        dlg.configure(bg=BG)
        dlg.transient(self)
        ttk.Label(dlg, text="🚑  Bootloop Recovery", font=("", 16, "bold")).pack(pady=(14, 2))
        ttk.Label(dlg, text="Walkman stuck rebooting after a theme or flash? This catches it and "
                            "restores a good player app.", foreground=SUB, wraplength=580,
                  justify="center").pack(pady=(0, 8))
        info = (
            "How it works\n"
            "1.  Plug the Walkman into USB and leave it powered — it will keep rebooting; that's fine.\n"
            "2.  This grabs the brief moment adb sees the device during each reboot.\n"
            "3.  It restores a known-good HgrmMediaPlayerApp with the correct 755 root:root perms —\n"
            "     a restore that loses the execute bit is itself the usual cause of the loop.\n"
            "4.  It stops automatically once the device stays up.\n\n"
            "If the loop was caused by something other than a UI/theme mod (splash, boot animation, "
            "font), use Revert All once the device is back."
        )
        body = tk.Text(dlg, height=10, wrap="word", bg=BG2, fg=FG, relief="flat",
                       padx=10, pady=8, highlightthickness=0)
        body.insert("1.0", info)
        body.configure(state="disabled")
        body.pack(fill="x", padx=16)

        srcf = ttk.Frame(dlg)
        srcf.pack(fill="x", padx=16, pady=(8, 4))
        ttk.Label(srcf, text="Good app:").pack(side="left")
        src_var = tk.StringVar(value=self._recovery_source())
        ttk.Entry(srcf, textvariable=src_var, width=46).pack(side="left", padx=6)

        def pick():
            p = filedialog.askopenfilename(parent=dlg,
                                           title="Select a known-good HgrmMediaPlayerApp",
                                           filetypes=[("All files", "*.*")])
            if p:
                src_var.set(p)
        ttk.Button(srcf, text="Browse…", command=pick).pack(side="left")

        rlog = tk.Text(dlg, height=9, wrap="word", bg=BG3, fg=FG, relief="flat",
                       padx=8, pady=6, highlightthickness=0)
        rlog.pack(fill="both", expand=True, padx=16, pady=8)

        def rappend(msg):
            def _do():
                try:
                    rlog.insert("end", str(msg) + "\n"); rlog.see("end")
                except tk.TclError:
                    pass
            try:
                dlg.after(0, _do)
            except tk.TclError:
                pass

        btns = ttk.Frame(dlg)
        btns.pack(pady=(0, 12))
        start_btn = ttk.Button(btns, text="Start Recovery", style="Danger.TButton")

        def start():
            src = src_var.get().strip()
            if not src or not os.path.exists(src):
                messagebox.showwarning("No source app",
                                       "Pick a known-good HgrmMediaPlayerApp file to restore.\n"
                                       "(Your backups are in ~/.wlkmnstudio/backups)", parent=dlg)
                return
            start_btn.configure(state="disabled")

            def work():
                try:
                    device.emergency_restore_player(src, on_log=rappend)
                except Exception as e:
                    rappend(f"ERROR: {e}")
                try:
                    dlg.after(0, lambda: start_btn.configure(state="normal"))
                except tk.TclError:
                    pass
                self.refresh_device()
            threading.Thread(target=work, daemon=True).start()

        start_btn.configure(command=start)
        start_btn.pack(side="left", padx=6)
        ttk.Button(btns, text="Close", command=dlg.destroy).pack(side="left", padx=6)

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
    app = App()
    if getattr(app, "declined", False):
        return                       # user did not accept the risk agreement
    app.mainloop()


if __name__ == "__main__":
    main()
