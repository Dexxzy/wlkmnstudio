"""Read-only reader for Sony's media database (genesys-db) at /db/MTPDB.dat — a SQLite file.
Used by the Library Stats mod. Opens a pulled copy from bytes; never writes to the device."""
import collections
import os
import sqlite3
import tempfile

AUDIO_EXTS = {"flac", "mp3", "wav", "dsf", "dff", "aif", "aiff", "m4a", "aac",
              "alac", "ogg", "oga", "wma", "ape", "mp4", "mqa"}


def _one(c, sql, default=0):
    try:
        r = c.execute(sql).fetchone()
        return r[0] if r and r[0] is not None else default
    except sqlite3.Error:
        return default


def stats(db_bytes):
    """Return a dict of library statistics from MTPDB.dat bytes. Object files are object_type=2;
    formats come from the filename extension (robust across Sony's internal format codes)."""
    fd, p = tempfile.mkstemp(suffix=".mtpdb")
    os.close(fd)
    with open(p, "wb") as fh:
        fh.write(db_bytes)
    try:
        c = sqlite3.connect(p)
        by_ext = collections.Counter()
        audio_bytes = 0
        for fn, fs in c.execute(
                "select filename, filesize from object_body "
                "where object_type=2 and filename is not null"):
            ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else "(none)"
            by_ext[ext] += 1
            if ext in AUDIO_EXTS and fs:
                audio_bytes += fs
        tracks = sum(n for e, n in by_ext.items() if e in AUDIO_EXTS)
        storage = dict(c.execute(
            "select storage_no, count(*) from object_body where object_type=2 group by storage_no"))
        return {
            "tracks": tracks,
            "by_format": dict(by_ext.most_common()),
            "hi_res": _one(c, "select count(*) from object_body where is_high_resolution=1"),
            "audio_bytes": audio_bytes,
            "total_bytes": _one(c, "select coalesce(sum(filesize),0) from object_body where object_type=2"),
            "artists": _one(c, "select count(*) from artists"),
            "album_artists": _one(c, "select count(*) from albumartists"),
            "albums": _one(c, "select count(*) from albums"),
            "genres": _one(c, "select count(*) from genres"),
            "composers": _one(c, "select count(*) from composers"),
            "year_min": _one(c, "select min(value) from releaseyears where value between 1900 and 2100", None),
            "year_max": _one(c, "select max(value) from releaseyears where value between 1900 and 2100", None),
            "storage": {int(k): v for k, v in storage.items()},
        }
    finally:
        try:
            c.close()
        except Exception:
            pass
        os.remove(p)


def duplicates(db_bytes, min_bytes=200000):
    """Find likely duplicate tracks: same title AND identical file size (two different songs almost
    never share both). Returns (groups, wasted_bytes) where groups = [(title, count, filesize), ...]
    sorted by wasted space. Read-only — reports; deletion is left to the user."""
    fd, p = tempfile.mkstemp(suffix=".mtpdb")
    os.close(fd)
    with open(p, "wb") as fh:
        fh.write(db_bytes)
    try:
        c = sqlite3.connect(p)
        rows = c.execute(
            "select title, filesize, count(*) n from object_body "
            "where object_type=2 and title is not null and filesize > ? "
            "group by lower(title), filesize having n > 1 order by (n-1)*filesize desc",
            (min_bytes,)).fetchall()
        groups = [(t, n, fs) for (t, fs, n) in rows]
        wasted = sum((n - 1) * fs for (_, n, fs) in groups)
        return groups, wasted
    finally:
        try:
            c.close()
        except Exception:
            pass
        os.remove(p)


def human_bytes(b):
    return "%.1f GB" % (b / 1e9) if b >= 1e9 else "%.0f MB" % (b / 1e6)
