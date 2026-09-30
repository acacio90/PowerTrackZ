"""Versao do PowerTrackZ lida do repositorio git montado no conteiner (sem depender do executavel git)."""
import os
import zlib
from pathlib import Path


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _packed_refs(git_dir):
    """Referencias compactadas: {ref: sha} e, para tags anotadas, {ref: sha do commit} pela linha '^'."""
    refs, peeled = {}, {}
    content = _read(git_dir / "packed-refs") or ""
    last_ref = None
    for line in content.splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("^"):
            if last_ref:
                peeled[last_ref] = line[1:].strip()
            continue
        sha, _, ref = line.partition(" ")
        refs[ref.strip()] = sha.strip()
        last_ref = ref.strip()
    return refs, peeled


def _resolve_ref(git_dir, ref, packed):
    return _read(git_dir / ref) or packed.get(ref)


def _tag_target(git_dir, sha):
    """Commit apontado por um objeto de tag anotada solto; devolve o proprio sha quando nao e uma tag."""
    try:
        raw = zlib.decompress((git_dir / "objects" / sha[:2] / sha[2:]).read_bytes())
    except (OSError, zlib.error):
        return sha
    header, _, body = raw.partition(b"\0")
    if not header.startswith(b"tag "):
        return sha
    first_line = body.split(b"\n", 1)[0].decode("utf-8", "replace")
    return first_line.split(" ", 1)[1].strip() if first_line.startswith("object ") else sha


def read_version(git_dir=None):
    """Devolve {"commit", "branch", "tag"} do HEAD; campos desconhecidos ficam nulos."""
    git_dir = Path(git_dir or os.environ.get("POWERTRACKZ_GIT_DIR", "/repo-git"))
    head = _read(git_dir / "HEAD")
    if not head:
        return {"commit": None, "branch": None, "tag": None}

    refs, peeled = _packed_refs(git_dir)
    branch = None
    commit = head
    if head.startswith("ref:"):
        ref = head[4:].strip()
        branch = ref.removeprefix("refs/heads/")
        commit = _resolve_ref(git_dir, ref, refs)

    tag = None
    if commit:
        tag_refs = {ref: sha for ref, sha in refs.items() if ref.startswith("refs/tags/")}
        tags_dir = git_dir / "refs" / "tags"
        if tags_dir.is_dir():
            for path in tags_dir.rglob("*"):
                if path.is_file():
                    tag_refs[path.relative_to(git_dir).as_posix()] = _read(path)
        for ref, sha in sorted(tag_refs.items()):
            target = (peeled.get(ref) or _tag_target(git_dir, sha)) if sha else None
            if target == commit:
                tag = ref.removeprefix("refs/tags/")
                break

    return {"commit": commit, "branch": branch, "tag": tag}
