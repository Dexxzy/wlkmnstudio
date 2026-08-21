"""Backup ledger. Before any mod writes, its targets are backed up here; 'revert' restores them.
One backup per target key (won't clobber a good backup with a modified file on re-runs)."""
import json, os, time
from . import device


def _default_mode(remote):
    """Best-guess original mode when it wasn't recorded: executables under a bin/ dir are 755,
    everything else 644. Prevents a revert from bricking by dropping the execute bit."""
    return "755" if "/bin/" in remote else "644"


class Ledger:
    def __init__(self, backup_dir):
        self.dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
        self.path = os.path.join(backup_dir, "ledger.json")
        self.entries = json.load(open(self.path)) if os.path.exists(self.path) else []

    def _save(self):
        json.dump(self.entries, open(self.path, "w"), indent=2)

    def has(self, key):
        return any(e["key"] == key for e in self.entries)

    def _bak_path(self, key):
        return os.path.join(self.dir, key.replace("/", "_") + ".bak")

    def backup_file(self, key, remote):
        if self.has(key):
            return
        data = device.pull_file(remote)
        # record the ORIGINAL mode so restore puts it back exactly. Restoring an executable (the
        # player app) as 644 drops the execute bit → hagodaemon can't launch it → bootloop.
        mode = device.stat_mode(remote) or _default_mode(remote)
        p = self._bak_path(key)
        open(p, "wb").write(data)
        self.entries.append({"key": key, "kind": "file", "remote": remote, "backup": p,
                             "md5": device.md5_bytes(data), "mode": mode, "ts": time.time()})
        self._save()

    def backup_partition(self, key, dev, size):
        if self.has(key):
            return
        data = device.read_partition(dev, size)
        p = self._bak_path(key)
        open(p, "wb").write(data)
        self.entries.append({"key": key, "kind": "partition", "dev": dev,
                             "backup": p, "md5": device.md5_bytes(data), "ts": time.time()})
        self._save()

    def restore(self, key):
        for e in self.entries:
            if e["key"] == key:
                data = open(e["backup"], "rb").read()
                if e["kind"] == "file":
                    # use the saved original mode; fall back for older ledger entries with no mode
                    mode = e.get("mode") or _default_mode(e["remote"])
                    device.install_file(data, e["remote"], mode=mode)
                else:
                    device.write_partition(data, e["dev"])
                return True
        return False

    def restore_all(self):
        for e in list(self.entries):
            self.restore(e["key"])
