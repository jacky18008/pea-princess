"""Freeze and verify the exact public pea-princess ZIP used by the local lab.

No network, model calls or archive execution. Public ZIP entries become immutable
bytes under skills/pea-princess; host implementation imports remain separate.
artifact_info(root) returns a compact verified identity; skill_root(root) returns
the actor's package directory. Development fallback is explicit and unavailable
to frozen runtimes, including runtimes whose public manifest is missing/broken.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata
import zipfile


NAME = "pea-princess"
SKILL_PATH = "skills/pea-princess"
ARCHIVE_PATH = "artifacts/pea-princess-skill.zip"
MANIFEST = "runtime-manifest.json"
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_ENTRIES = 2048
MAX_TREE_ENTRIES = 8192


class PublicSkillError(ValueError):
    pass


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _regular(path):
    for component in (path, *path.parents):
        if component.is_symlink():
            raise PublicSkillError("public skill paths cannot traverse symbolic links")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise PublicSkillError("public skill input must be an independent regular file")
    return info


def _read(path, limit, private=False):
    path = Path(path)
    _regular(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise PublicSkillError("public skill file exceeds its limit or is not regular")
        if private and (before.st_uid != os.getuid() or stat.S_IMODE(before.st_mode) != 0o400):
            raise PublicSkillError("frozen public skill files must remain private and immutable")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        observed = _signature(before)
        if len(raw) > limit or len(raw) != before.st_size or observed != _signature(os.fstat(fd)) or observed != _signature(_regular(path)):
            raise PublicSkillError("public skill file changed while being read")
        return raw, observed
    finally:
        os.close(fd)


def _identity(raw):
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as error:
        raise PublicSkillError("public SKILL.md must be UTF-8") from error
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise PublicSkillError("public SKILL.md must declare its pea-princess identity")
    end = lines.index("---", 1)
    names = [line for line in lines[1:end] if re.match(r"^name\s*:", line)]
    if len(names) != 1 or not re.fullmatch(r"name\s*:\s*(?:pea-princess|\"pea-princess\"|'pea-princess')\s*", names[0]):
        raise PublicSkillError("public SKILL.md name must be exactly pea-princess")


def _entry(info):
    name = info.filename
    if name != info.orig_filename or not isinstance(name, str) or len(name.encode("utf-8")) > 1024:
        raise PublicSkillError("invalid or oversized public ZIP path")
    if any(ord(char) < 32 or 127 <= ord(char) <= 159 or char in "\\:" for char in name):
        raise PublicSkillError("unsafe public ZIP path")
    directory = name.endswith("/")
    clean = name[:-1] if directory else name
    path = PurePosixPath(clean)
    if path.is_absolute() or str(path) != clean or ".." in path.parts or not path.parts or path.parts[0] != NAME or len(path.parts) > 16:
        raise PublicSkillError("public ZIP entries must stay inside pea-princess/")
    if any(part in ("", ".", "..") or part.endswith((".", " ")) for part in path.parts):
        raise PublicSkillError("unsafe public ZIP path component")
    if len(path.parts) == 1 and not directory:
        raise PublicSkillError("the public ZIP root must be a directory")
    mode = (info.external_attr >> 16) & 0xFFFF
    kind = stat.S_IFMT(mode)
    if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or (kind == stat.S_IFDIR and not directory) or (kind == stat.S_IFREG and directory):
        raise PublicSkillError("public ZIP entries must be regular files or directories; symlinks are forbidden")
    if info.external_attr & 0x10 and not directory:
        raise PublicSkillError("public ZIP directory attributes disagree")
    if info.flag_bits & 1 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise PublicSkillError("encrypted or unsupported public ZIP compression")
    if info.file_size < 0 or info.file_size > MAX_FILE_BYTES or (directory and info.file_size):
        raise PublicSkillError("public ZIP entry exceeds the file limit")
    return str(path), directory


def _unpack(raw):
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise PublicSkillError("public ZIP exceeds the archive limit")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > MAX_ENTRIES or sum(item.file_size for item in entries) > MAX_TOTAL_BYTES:
                raise PublicSkillError("public ZIP exceeds its entry or expanded-byte limit")
            seen, nodes, files, directories = set(), {}, {}, set()
            checked = []
            for info in entries:
                name, directory = _entry(info)
                if name in seen:
                    raise PublicSkillError("duplicate public ZIP path")
                seen.add(name)
                parts = PurePosixPath(name).parts
                for depth in range(1, len(parts) + 1):
                    component = "/".join(parts[:depth])
                    is_directory = depth < len(parts) or directory
                    key = unicodedata.normalize("NFC", component).casefold()
                    previous = nodes.get(key)
                    if previous is not None and previous != (component, is_directory):
                        raise PublicSkillError("public ZIP contains a case, Unicode or file/directory collision")
                    nodes[key] = (component, is_directory)
                    if len(nodes) > MAX_TREE_ENTRIES:
                        raise PublicSkillError("public ZIP contains too many directory components")
                    if is_directory and depth > 1:
                        directories.add("/".join(parts[1:depth]))
                checked.append((info, name, directory))
            for info, name, directory in checked:
                if directory:
                    continue
                with archive.open(info, "r") as stream:
                    body = stream.read(MAX_FILE_BYTES + 1)
                if len(body) != info.file_size or len(body) > MAX_FILE_BYTES:
                    raise PublicSkillError("public ZIP entry size differs from its directory")
                files[name[len(NAME) + 1:]] = body
    except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, NotImplementedError, UnicodeError) as error:
        raise PublicSkillError("cannot read the public skill ZIP") from error
    if "SKILL.md" not in files:
        raise PublicSkillError("public skill ZIP is missing SKILL.md")
    _identity(files["SKILL.md"])
    return files, directories


def load_archive(path):
    """Read one selected archive once, validating stable bytes and all entries."""
    try:
        path = Path(os.path.abspath(str(Path(path).expanduser())))
        raw, observed = _read(path, MAX_ARCHIVE_BYTES)
        files, directories = _unpack(raw)
        identity = {"schema_version": 1, "name": NAME, "mode": "public_archive",
                    "skill_path": SKILL_PATH, "archive_path": ARCHIVE_PATH,
                    "archive_sha256": _sha(raw), "archive_bytes": len(raw),
                    "skill_sha256": _sha(files["SKILL.md"]), "file_count": len(files),
                    "files": {name: {"sha256": _sha(body), "bytes": len(body)} for name, body in sorted(files.items())}}
        return {"source": path, "observed": observed, "raw": raw,
                "files": files, "directories": directories, "identity": identity}
    except (OSError, TypeError, UnicodeError, RuntimeError) as error:
        raise PublicSkillError("cannot load selected public skill ZIP: " + str(error)) from error


def verify_source(bundle):
    """Second freeze pass: never publish a snapshot selected from changing bytes."""
    try:
        raw, observed = _read(bundle["source"], MAX_ARCHIVE_BYTES)
        if observed != bundle["observed"] or raw != bundle["raw"]:
            raise PublicSkillError("public skill archive changed during freeze")
    except OSError as error:
        raise PublicSkillError("public skill archive changed during freeze") from error


def _write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fchmod(fd, 0o400)
        os.fsync(fd)
    finally:
        os.close(fd)


def install_archive(bundle, root):
    """Extract prevalidated bytes into an unpublished, caller-owned staging root."""
    root = Path(root)
    destination = root / SKILL_PATH
    if destination.exists() or destination.is_symlink():
        raise PublicSkillError("public skill extraction destination already exists")
    destination.mkdir(parents=True, mode=0o700)
    for name in sorted(bundle["directories"]):
        (destination / name).mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, raw in bundle["files"].items():
        _write(destination / name, raw)
    _write(root / ARCHIVE_PATH, bundle["raw"])
    for name in sorted(bundle["directories"], key=lambda value: len(PurePosixPath(value).parts), reverse=True):
        (destination / name).chmod(0o500)
    destination.chmod(0o500)
    return copy.deepcopy(bundle["identity"])


def _json(raw):
    def unique(pairs):
        value = {}
        for name, item in pairs:
            if name in value:
                raise PublicSkillError("duplicate runtime manifest field")
            value[name] = item
        return value
    def invalid(_):
        raise PublicSkillError("invalid runtime manifest number")
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise PublicSkillError("invalid runtime manifest") from error


def _tree(root):
    """Enumerate only the bounded extracted package, refusing all link aliases."""
    files, directories = set(), set()
    count = 0
    for folder, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(folder) / name
            count += 1
            if count > MAX_TREE_ENTRIES:
                raise PublicSkillError("frozen public skill tree exceeds its entry limit")
            info = path.lstat()
            relative = str(path.relative_to(root))
            if stat.S_ISDIR(info.st_mode):
                directories.add(relative)
            elif stat.S_ISREG(info.st_mode):
                files.add(relative)
            else:
                raise PublicSkillError("frozen public skill tree contains a symbolic link or special file")
    return files, directories


def artifact_info(root):
    """Verify the exact frozen public archive/tree, then return compact identity."""
    try:
        root = Path(root).resolve(strict=True)
        manifest_path = root / MANIFEST
        frozen = (manifest_path.exists() or manifest_path.is_symlink()
                  or (root / SKILL_PATH).exists() or (root / SKILL_PATH).is_symlink()
                  or (root / ARCHIVE_PATH).exists() or (root / ARCHIVE_PATH).is_symlink()
                  or (root.parent.name == "runtime" and root.parent.parent.name == ".pea-playground"))
        if not frozen:
            path = root / "skills/vet-flat"
            raw, _ = _read(path / "SKILL.md", MAX_FILE_BYTES)
            _identity(raw)
            files, _ = _tree(path)
            return {"name": NAME, "kind": "development", "sha256": None,
                    "file_count": len(files), "skill_sha256": _sha(raw), "path": str(path), "archive_path": None}
        raw, _ = _read(manifest_path, MAX_FILE_BYTES, private=True)
        manifest = _json(raw)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("public_skill"), dict):
            raise PublicSkillError("frozen runtime has no public skill archive identity; restart through start_playground.py")
        identity = manifest["public_skill"]
        raw, _ = _read(root / ARCHIVE_PATH, MAX_ARCHIVE_BYTES, private=True)
        files, directories = _unpack(raw)
        expected = {"schema_version": 1, "name": NAME, "mode": "public_archive",
                    "skill_path": SKILL_PATH, "archive_path": ARCHIVE_PATH,
                    "archive_sha256": _sha(raw), "archive_bytes": len(raw),
                    "skill_sha256": _sha(files["SKILL.md"]), "file_count": len(files),
                    "files": {name: {"sha256": _sha(body), "bytes": len(body)} for name, body in sorted(files.items())}}
        if json.dumps(identity, sort_keys=True, separators=(",", ":")) != json.dumps(expected, sort_keys=True, separators=(",", ":")):
            raise PublicSkillError("frozen public skill manifest differs from its retained ZIP")
        path = root / SKILL_PATH
        if path.is_symlink() or not path.is_dir():
            raise PublicSkillError("frozen public skill directory is missing or unsafe")
        actual_files, actual_dirs = _tree(path)
        if actual_files != set(files) or actual_dirs != directories:
            raise PublicSkillError("frozen public skill tree is not exactly the selected ZIP")
        for name, original in files.items():
            retained, _ = _read(path / name, MAX_FILE_BYTES, private=True)
            if retained != original:
                raise PublicSkillError("frozen public skill file differs from its ZIP: " + name)
        return {"name": NAME, "kind": "public_zip", "sha256": expected["archive_sha256"],
                "file_count": len(files), "skill_sha256": expected["skill_sha256"],
                "path": str(path), "archive_path": str(root / ARCHIVE_PATH)}
    except (OSError, TypeError, UnicodeError, RuntimeError) as error:
        raise PublicSkillError("cannot verify public skill artifact: " + str(error)) from error


def skill_root(root):
    return Path(artifact_info(root)["path"])
