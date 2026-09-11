"""Bounded private snapshots of files deliberately supplied to the local lab.

Standard library only; no shell evaluation, network access or model calls.
AttachmentStore(root).ingest({"path": "/chosen/file.pdf"}) also accepts an
upload object with exactly ``name`` and ``content_base64``. resolve(ids) checks
snapshots; materialize(ids, destination) creates verified private actor copies.
Names and original paths are evidence text, never executable instructions.
These checks detect corruption; they are not authentication against the OS user.
"""
import base64
import binascii
from contextlib import contextmanager
import fcntl
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import shlex
import stat
import uuid
from urllib.parse import unquote, urlsplit


MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
MAX_ATTACHMENTS = 6
MAX_METADATA_BYTES = 32 * 1024
MAX_STORE_BYTES = 512 * 1024 * 1024
MAX_STORED_ATTACHMENTS = 256
MAX_PATH_CHARS = 4096
ID = re.compile(r"[a-f0-9]{32}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
EXTENSION = re.compile(r"\.[a-z0-9]{1,12}\Z")


class AttachmentError(ValueError):
    """The selected attachment or retained snapshot is invalid."""


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _controls(value):
    return any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value)


def _name(value):
    if not isinstance(value, str) or not value or value in (".", ".."):
        raise AttachmentError("attachment filename is invalid")
    try:
        length = len(value.encode("utf-8"))
    except UnicodeError as error:
        raise AttachmentError("attachment filename is invalid") from error
    if length > 255 or _controls(value) or any(char in "/\\" for char in value):
        raise AttachmentError("attachment filename must be a single bounded filename")
    return value


def _extension(name):
    suffix = Path(name).suffix.lower()
    return suffix if EXTENSION.fullmatch(suffix) else ""


def _image(extension, raw):
    """A raster signature hint, not a full image decoder or safety verdict."""
    if extension == ".png":
        return raw.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in (".jpg", ".jpeg"):
        return raw.startswith(b"\xff\xd8\xff")
    if extension == ".gif":
        return raw.startswith((b"GIF87a", b"GIF89a"))
    if extension == ".webp":
        return raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
    if extension == ".bmp":
        return raw.startswith(b"BM")
    if extension in (".tif", ".tiff"):
        return raw.startswith((b"II*\x00", b"MM\x00*"))
    if extension in (".avif", ".heic", ".heif") and raw[4:8] == b"ftyp":
        brands = {raw[index:index + 4] for index in range(8, min(len(raw), 40), 4) if index != 12}
        return bool(brands & ({b"avif", b"avis"} if extension == ".avif" else {b"heic", b"heix", b"hevc", b"hevx", b"mif1"}))
    return False


@contextmanager
def _quota_lock(directory):
    fd = os.open(".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
            raise AttachmentError("attachment quota lock is invalid")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _directory(path, private=False):
    """Open a pinned directory through symlink-free components."""
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise AttachmentError("private attachment directory is invalid")
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or (private and stat.S_IMODE(info.st_mode) & 0o077):
            raise AttachmentError("attachment directory must be private and owned by the current user")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _stable(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read(fd, limit, retained=False):
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise AttachmentError("attachment must be a regular file within the byte limit")
    if retained and (before.st_uid != os.getuid() or before.st_nlink != 1 or stat.S_IMODE(before.st_mode) != 0o400):
        raise AttachmentError("retained attachment is not an immutable private file")
    with os.fdopen(fd, "rb", closefd=False) as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit or len(raw) != before.st_size or _stable(before) != _stable(os.fstat(fd)):
        raise AttachmentError("attachment changed while being read or exceeds the byte limit")
    return raw


def _read_at(directory, name, limit):
    # NONBLOCK lets fstat reject a replaced FIFO without waiting for a writer.
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        return _read(fd, limit, retained=True)
    finally:
        os.close(fd)


def _write_at(directory, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fchmod(fd, 0o400)
        os.fsync(fd)
    except BaseException:
        # O_EXCL succeeded, so this name belongs to this write attempt. Never
        # leave a partial actor copy that a later call could mistake for evidence.
        os.unlink(name, dir_fd=directory)
        raise
    finally:
        os.close(fd)


def _paths(value):
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_PATH_CHARS or _controls(value):
        raise AttachmentError("local attachment path is invalid")
    value = value.strip()
    if value.startswith("file:"):
        try:
            parsed = urlsplit(value)
            if parsed.scheme != "file" or parsed.netloc not in ("", "localhost") or parsed.query or parsed.fragment:
                raise AttachmentError("only local file URLs are supported")
            value = unquote(parsed.path, encoding="utf-8", errors="strict")
        except (ValueError, UnicodeError) as error:
            raise AttachmentError("local file URL is invalid") from error
        if _controls(value):
            raise AttachmentError("local attachment path is invalid")
        candidates = [value]
    else:
        # Try literal text first: shell-looking characters can be real filenames.
        candidates = [value]
        try:
            parts = shlex.split(value, posix=True)
        except ValueError:
            parts = []
        if len(parts) == 1 and parts[0] != value:
            candidates.append(parts[0])
    result = []
    for candidate in candidates:
        if candidate.startswith("~/"):
            candidate = str(Path.home()) + candidate[1:]
        if len(candidate) > MAX_PATH_CHARS or _controls(candidate):
            raise AttachmentError("local attachment path is invalid")
        path = Path(candidate)
        if path.is_absolute():
            result.append(path)
    if not result:
        raise AttachmentError("choose one absolute local path, ~/ path, or local file URL")
    return result


def _source(value, limit):
    paths = _paths(value)
    for index, path in enumerate(paths):
        try:
            # Explicit user-selected symlinks are allowed. The opened descriptor
            # is pinned and validated before any bytes are read; no directory is
            # traversed/enumerated for discovery and OS symlink limits still apply.
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except FileNotFoundError:
            if index + 1 < len(paths):
                continue
            raise
        try:
            return _name(path.name), _read(fd, limit), str(path)
        finally:
            os.close(fd)


def _parse(raw):
    def invalid_constant(_):
        raise AttachmentError("nonfinite attachment metadata value")
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise AttachmentError("duplicate attachment metadata field")
            value[key] = item
        return value
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise AttachmentError("attachment metadata is invalid") from error


class AttachmentStore:
    def __init__(self, root, max_bytes=MAX_ATTACHMENT_BYTES, max_store_bytes=MAX_STORE_BYTES, max_files=MAX_STORED_ATTACHMENTS):
        if type(max_bytes) is not int or not 0 < max_bytes <= MAX_ATTACHMENT_BYTES:
            raise AttachmentError("attachment byte limit is invalid")
        self.max_bytes = max_bytes
        if type(max_store_bytes) is not int or not 0 < max_store_bytes <= MAX_STORE_BYTES or type(max_files) is not int or not 0 < max_files <= MAX_STORED_ATTACHMENTS:
            raise AttachmentError("attachment storage quota is invalid")
        self.max_store_bytes, self.max_files = max_store_bytes, max_files
        try:
            root = Path(root)
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.root = root.resolve(strict=True)
            parent = _directory(self.root)
            try:
                try:
                    os.mkdir("attachments", 0o700, dir_fd=parent)
                except FileExistsError:
                    pass
            finally:
                os.close(parent)
            self.path = self.root / "attachments"
            os.close(_directory(self.path, private=True))
        except (OSError, RuntimeError) as error:
            raise AttachmentError("cannot open the private attachment store") from error

    def ingest(self, payload):
        """Snapshot exactly one upload/local file; return detached metadata."""
        if not isinstance(payload, dict):
            raise AttachmentError("attachment payload must be an object")
        try:
            if set(payload) == {"name", "content_base64"}:
                name = _name(payload["name"])
                encoded = payload["content_base64"]
                if not isinstance(encoded, str) or len(encoded) > 4 * ((self.max_bytes + 2) // 3):
                    raise AttachmentError("encoded attachment exceeds the byte limit or is invalid")
                try:
                    raw = base64.b64decode(encoded, validate=True)
                except (ValueError, binascii.Error) as error:
                    raise AttachmentError("attachment content must be valid base64") from error
                if len(raw) > self.max_bytes:
                    raise AttachmentError("attachment exceeds the byte limit")
                source_kind, original = "upload", None
            elif set(payload) == {"path"}:
                name, raw, original = _source(payload["path"], self.max_bytes)
                source_kind = "local_path"
            else:
                raise AttachmentError("supply either name/content_base64 or one local path")
            aid = uuid.uuid4().hex
            extension = _extension(name)
            metadata = {"schema_version": 1, "id": aid, "name": name, "bytes": len(raw), "sha256": _sha(raw),
                        "extension": extension, "mime_type": mimetypes.guess_type(name)[0] or "application/octet-stream",
                        "image": _image(extension, raw), "source_kind": source_kind, "original_path": original}
            envelope = {"value": metadata, "sha256": _sha(_canonical(metadata))}
            parent = _directory(self.path, private=True)
            directory = None
            created = False
            try:
                with _quota_lock(parent):
                    self._quota(parent, len(raw))
                    os.mkdir(aid, 0o700, dir_fd=parent)
                    created = True
                    directory = os.open(aid, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    _write_at(directory, "data" + extension, raw)
                    _write_at(directory, "metadata.json", _canonical(envelope))
            except BaseException:
                if directory is not None:
                    for filename in ("data" + extension, "metadata.json"):
                        try:
                            os.unlink(filename, dir_fd=directory)
                        except FileNotFoundError:
                            pass
                if created:
                    os.rmdir(aid, dir_fd=parent)
                raise
            finally:
                if directory is not None:
                    os.close(directory)
                os.close(parent)
            return self._public(metadata, envelope["sha256"])
        except (OSError, UnicodeError, RuntimeError) as error:
            raise AttachmentError("cannot snapshot the selected regular local file") from error

    def _public(self, metadata, metadata_hash):
        return dict(metadata, metadata_sha256=metadata_hash,
                    stored_path=str(self.path / metadata["id"] / ("data" + metadata["extension"])))

    def _quota(self, parent, incoming):
        # Only enumerate the store's own bounded directory, never a source path.
        ids = os.listdir(parent)
        if len(ids) > self.max_files + 1:
            raise AttachmentError("attachment store file quota is exceeded")
        total, count = 0, 0
        for aid in ids:
            if aid == ".lock":
                continue
            if not ID.fullmatch(aid):
                raise AttachmentError("attachment store contains an unexpected entry")
            directory = os.open(aid, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                names = os.listdir(directory)
                blobs = [name for name in names if name == "data" or (name.startswith("data") and EXTENSION.fullmatch(name[4:]))]
                if len(names) != 2 or "metadata.json" not in names or len(blobs) != 1:
                    raise AttachmentError("attachment store contains an incomplete snapshot")
                info = os.stat(blobs[0], dir_fd=directory, follow_symlinks=False)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o400 or info.st_size > self.max_bytes:
                    raise AttachmentError("attachment store contains an invalid snapshot")
                total += info.st_size
                count += 1
            finally:
                os.close(directory)
        if count >= self.max_files or total + incoming > self.max_store_bytes:
            raise AttachmentError("attachment store quota is full")

    def _ids(self, ids):
        if not isinstance(ids, list) or len(ids) > MAX_ATTACHMENTS:
            raise AttachmentError("at most six attachment IDs are allowed per message")
        if any(not isinstance(aid, str) or not ID.fullmatch(aid) for aid in ids) or len(set(ids)) != len(ids):
            raise AttachmentError("attachment IDs must be distinct opaque IDs")
        return ids

    def _load(self, aid):
        directory = _directory(self.path / aid, private=True)
        try:
            envelope = _parse(_read_at(directory, "metadata.json", MAX_METADATA_BYTES))
            if not isinstance(envelope, dict) or set(envelope) != {"value", "sha256"}:
                raise AttachmentError("attachment metadata envelope is invalid")
            meta = envelope["value"]
            fields = {"schema_version", "id", "name", "bytes", "sha256", "extension", "mime_type", "image", "source_kind", "original_path"}
            if not isinstance(meta, dict) or set(meta) != fields or envelope["sha256"] != _sha(_canonical(meta)):
                raise AttachmentError("attachment metadata integrity differs")
            if meta["schema_version"] != 1 or type(meta["schema_version"]) is not int or meta["id"] != aid:
                raise AttachmentError("attachment metadata identity differs")
            name = _name(meta["name"])
            extension = _extension(name)
            if meta["extension"] != extension or type(meta["bytes"]) is not int or not 0 <= meta["bytes"] <= self.max_bytes:
                raise AttachmentError("attachment metadata filename or byte limit is invalid")
            if not isinstance(meta["sha256"], str) or not HASH.fullmatch(meta["sha256"]):
                raise AttachmentError("attachment content digest is invalid")
            if meta["mime_type"] != (mimetypes.guess_type(name)[0] or "application/octet-stream") or type(meta["image"]) is not bool:
                raise AttachmentError("attachment media metadata is invalid")
            if meta["source_kind"] not in ("upload", "local_path"):
                raise AttachmentError("attachment source metadata is invalid")
            original = meta["original_path"]
            if ((meta["source_kind"] == "upload" and original is not None)
                    or (meta["source_kind"] == "local_path" and (not isinstance(original, str) or len(original) > MAX_PATH_CHARS or _controls(original) or not Path(original).is_absolute()))):
                raise AttachmentError("attachment original path is invalid")
            raw = _read_at(directory, "data" + extension, self.max_bytes)
            if len(raw) != meta["bytes"] or _sha(raw) != meta["sha256"] or meta["image"] != _image(extension, raw):
                raise AttachmentError("attachment content integrity differs")
            return self._public(meta, envelope["sha256"]), raw
        finally:
            os.close(directory)

    def resolve(self, ids):
        """Resolve only bounded opaque IDs, validating metadata and exact bytes."""
        ids = self._ids(ids)
        try:
            return [self._load(aid)[0] for aid in ids]
        except (OSError, UnicodeError, RuntimeError) as error:
            raise AttachmentError("cannot resolve a retained attachment") from error

    def materialize(self, ids, destination):
        """Copy verified bytes to a private per-call directory using ID names.

        Existing paths are never overwritten. Return metadata plus copy_path;
        failures remove only copies created by this invocation.
        """
        ids = self._ids(ids)
        written = []
        directory = None
        try:
            loaded = [self._load(aid) for aid in ids]
            destination = Path(destination).absolute()
            if ".." in destination.parts:
                raise AttachmentError("materialization destination is invalid")
            # The actor's per-call parent must already exist. Canonicalize OS
            # parent aliases once, then pin that parent and open/create the final
            # component without following a destination symlink, including races.
            destination = destination.parent.resolve(strict=True) / destination.name
            parent = _directory(destination.parent)
            try:
                try:
                    os.mkdir(destination.name, 0o700, dir_fd=parent)
                except FileExistsError:
                    pass
                directory = os.open(destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                info = os.fstat(directory)
                if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                    raise AttachmentError("materialization directory must be private and owned by the current user")
            finally:
                os.close(parent)
            result = []
            for metadata, raw in loaded:
                filename = metadata["id"] + metadata["extension"]
                try:
                    _write_at(directory, filename, raw)
                    written.append(filename)
                except FileExistsError:
                    pass
                copied = _read_at(directory, filename, self.max_bytes)
                if len(copied) != metadata["bytes"] or _sha(copied) != metadata["sha256"]:
                    raise AttachmentError("materialized attachment integrity differs")
                result.append(dict(metadata, copy_path=str(destination / filename)))
            return result
        except BaseException as error:
            if directory is not None:
                for filename in written:
                    os.unlink(filename, dir_fd=directory)
            if isinstance(error, (OSError, UnicodeError, RuntimeError)):
                raise AttachmentError("cannot materialize retained attachments") from error
            raise
        finally:
            if directory is not None:
                os.close(directory)
