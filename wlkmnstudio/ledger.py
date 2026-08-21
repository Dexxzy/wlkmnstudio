"""Backup ledger. Before any mod writes, its targets are backed up here; 'revert' restores them.
One backup per target key (won't clobber a good backup with a modified file on re-runs)."""
import json, os, time
from . import device


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
        p = self._bak_path(key)
        open(p, "wb").write(data)
        self.entries.append({"key": key, "kind": "file", "remote": remote,
                             "backup": p, "md5": device.md5_bytes(data), "ts": time.time()})
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
                    device.install_file(data, e["remote"])
                else:
                    device.write_partition(data, e["dev"])
                return True
        return False

    def restore_all(self):
        for e in list(self.entries):
            self.restore(e["key"])
