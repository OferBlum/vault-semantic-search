"""Folder boundary for the semantic index — the only module that touches vault files.

An allowlist, not a denylist: only top-level markdown directly under FOLDERS is
considered, so `raw/`, `.backup/` and every other folder (the private one included)
are never listed or opened, and this module never needs to know their names.
Symlinked paths are refused, and every read opens each path component with
O_NOFOLLOW so a link swapped in mid-read cannot redirect it.

The frontmatter parser is a trimmed copy of okf.py's split_header: a malformed
header reads as {} and the file is still indexed by its body.
"""
import os, re, stat, unicodedata
from pathlib import Path, PurePosixPath

import yaml

# Vault root: from VAULT_ROOT (for tests), or two levels above scripts/.
VAULT = Path(os.environ.get("VAULT_ROOT") or Path(__file__).resolve().parents[2])

# The allowlist. Nothing outside these folders is read or scanned.
FOLDERS = ('7 - Wikipedia', '2 - Notes', '1 - Topics')

# Generated files (`_cache.md`, `_index.md`, ...) are out of scope.
SYSTEM_PREFIX = '_'


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def rel(path):
    return nfc(str(Path(path).relative_to(VAULT)))


# ---------- no-follow reading ----------

def has_symlink(path):
    """A symlink anywhere on the path, or a path that can't be inspected, counts as one."""
    p = Path(os.path.abspath(path))
    for item in reversed((p, *p.parents)):
        try:
            if item.is_symlink():
                return True
        except OSError:
            return True
    return False


def read_text(path):
    """Text of a regular file, opening every path component with O_NOFOLLOW."""
    p = Path(os.path.abspath(path))
    flags = os.O_RDONLY | os.O_NOFOLLOW
    dir_fd = os.open(p.anchor, flags | os.O_DIRECTORY)
    try:
        for part in p.parts[1:-1]:
            next_fd = os.open(part, flags | os.O_DIRECTORY, dir_fd=dir_fd)
            os.close(dir_fd)
            dir_fd = next_fd
        fd = os.open(p.name, flags | os.O_NONBLOCK, dir_fd=dir_fd)
        with os.fdopen(fd, 'rb') as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
                raise OSError(f'not a regular file: {p.name}')
            return f.read().decode('utf-8-sig').replace('\r\n', '\n')
    finally:
        os.close(dir_fd)


# ---------- frontmatter ----------

HEADER_FENCE = re.compile(r'\A---[ \t]*\n(.*?)^---[ \t]*(?:\n|\Z)', re.S | re.M)

# Obsidian writes bare values YAML misreads: [[link]] parses as a nested list and #tag as a
# comment. Quote them before parsing.
_UNSAFE = re.compile(r'^(\s*(?:[^:\n]+:|-)[ \t]+)((?:\[\[|#).*)$')


def _quote_unsafe(text):
    out = []
    for line in text.splitlines():
        m = _UNSAFE.match(line)
        if m:
            val = m.group(2).rstrip()
            line = m.group(1) + '"' + val.replace("\\", "\\\\").replace('"', '\\"') + '"'
        out.append(line)
    return "\n".join(out)


def split_header(text):
    """(meta, body). A valid header is stripped from the body; a malformed one reads as {}."""
    m = HEADER_FENCE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(_quote_unsafe(m.group(1)))
    except (yaml.YAMLError, RecursionError, ValueError):
        return {}, text
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        return {}, text
    return {nfc(str(k)): v for k, v in meta.items()}, text[m.end():]


# ---------- the boundary ----------

def _relative_path(rel):
    if not isinstance(rel, str) or not rel or '\\' in rel:
        return None
    p = PurePosixPath(rel)
    if (p.is_absolute() or len(p.parts) != 2 or p.as_posix() != rel
            or p.parts[0] not in FOLDERS or not rel.endswith('.md')
            or p.name.startswith(SYSTEM_PREFIX)):
        return None
    return VAULT / rel


def cache_permitted(rel):
    """Boundary check for a path stored in the index; the source may since have been deleted.

    A genuinely absent regular path is safe to retain until the next update.
    """
    path = _relative_path(rel)
    if path is None:
        return False
    try:
        return not has_symlink(path) and (not path.exists() or path.is_file())
    except OSError:
        return False


def permitted(rel):
    """True only for an existing, non-symlinked source inside the boundary."""
    path = _relative_path(rel)
    if path is None:
        return False
    try:
        return not has_symlink(path) and path.is_file()
    except OSError:
        return False


def sources():
    """(rel, path) for every file inside the boundary. Lists only the allowed folders."""
    for folder in FOLDERS:
        root = VAULT / folder
        if has_symlink(root) or not root.is_dir():
            continue
        for path in sorted(root.glob('*.md')):
            rel = f'{folder}/{nfc(path.name)}'
            if permitted(rel):
                yield rel, path


def read(rel):
    """(meta, body) for a permitted file, or None."""
    if not permitted(rel):
        return None
    try:
        return split_header(read_text(VAULT / rel))
    except (OSError, UnicodeError):
        return None
