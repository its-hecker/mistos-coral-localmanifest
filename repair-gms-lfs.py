#!/usr/bin/env python3
"""Materialize incomplete Git LFS payloads in MistOS vendor/gms.

Some APKs were committed as LFS pointers without corresponding .gitattributes
rules, so repo sync leaves text pointers where Android expects APK files.
This tool never fabricates or replaces an APK with an unverified download.
"""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

REPO = Path("vendor/gms").resolve()
POINTER = re.compile(
    rb"\Aversion https://git-lfs.github.com/spec/v1\r?\n"
    rb"oid sha256:([0-9a-f]{64})\r?\n"
    rb"size ([0-9]+)\r?\n?\Z"
)
ZIP_EXTENSIONS = {".apk", ".apex", ".jar", ".zip"}


def find_pointers():
    for path in REPO.rglob("*"):
        if not path.is_file() or path.is_symlink() or ".git" in path.relative_to(REPO).parts:
            continue
        with path.open("rb") as source:
            beginning = source.read(160)
            if not beginning.startswith(b"version https://git-lfs.github.com/spec/v1"):
                continue
            extra = source.read(1)
        if extra:
            raise RuntimeError(f"Unexpected oversized LFS pointer: {path}")
        match = POINTER.fullmatch(beginning)
        if not match:
            raise RuntimeError(f"Malformed LFS pointer: {path}")
        yield path, match.group(1).decode(), int(match.group(2))


def materialize(path, expected_sha, expected_size):
    relative = path.relative_to(REPO)
    fd, destination = tempfile.mkstemp(prefix=".mist-lfs-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as target, path.open("rb") as pointer:
            env = dict(os.environ)
            env.pop("GIT_LFS_SKIP_SMUDGE", None)
            subprocess.run(
                ["git", "-C", str(REPO), "lfs", "smudge", str(relative)],
                stdin=pointer,
                stdout=target,
                check=True,
                env=env,
            )

        hasher = hashlib.sha256()
        actual_size = 0
        with open(destination, "rb") as payload:
            for block in iter(lambda: payload.read(1024 * 1024), b""):
                hasher.update(block)
                actual_size += len(block)
        if actual_size != expected_size or hasher.hexdigest() != expected_sha:
            raise RuntimeError(
                f"Git LFS returned incorrect bytes for {relative}: "
                f"size={actual_size}, sha256={hasher.hexdigest()}"
            )
        if path.suffix.lower() in ZIP_EXTENSIONS:
            with zipfile.ZipFile(destination) as archive:
                if archive.testzip() is not None:
                    raise RuntimeError(f"Invalid archive after LFS download: {relative}")

        os.chmod(destination, path.stat().st_mode & 0o777)
        os.replace(destination, path)
        print(f"RESTORED {relative} ({actual_size} bytes)")
    finally:
        if os.path.exists(destination):
            os.unlink(destination)


def add_local_lfs_attributes(pointer_files):
    """Make materialized but untracked LFS files appear clean to repo sync."""
    result = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--git-path", "info/attributes"],
        check=True,
        text=True,
        capture_output=True,
    )
    info_path = Path(result.stdout.strip())
    if not info_path.is_absolute():
        info_path = (REPO / info_path).resolve()
    info_path.parent.mkdir(parents=True, exist_ok=True)
    existing = info_path.read_text() if info_path.exists() else ""
    additions = []
    for path, _, _ in pointer_files:
        relative = path.relative_to(REPO).as_posix()
        attr = subprocess.run(
            ["git", "-C", str(REPO), "check-attr", "filter", "--", relative],
            check=True, capture_output=True, text=True
        ).stdout.strip()
        if not attr.endswith(": lfs"):
            if " " in relative or "\t" in relative:
                raise RuntimeError(f"Unexpected whitespace in GMS LFS path: {relative}")
            additions.append(f"/{relative} filter=lfs diff=lfs merge=lfs -text")
    if additions:
        with info_path.open("a") as stream:
            if existing and not existing.endswith("\n"):
                stream.write("\n")
            stream.write("\n".join(additions) + "\n")
        print(f"Registered {len(additions)} missing local Git LFS attributes")


def main():
    if not REPO.is_dir():
        raise RuntimeError("vendor/gms not found. Sync MistOS first.")
    pointer_files = list(find_pointers())
    add_local_lfs_attributes(pointer_files)
    if not pointer_files:
        print("MistOS vendor/gms: no unresolved LFS pointers found.")
        return
    print(f"MistOS vendor/gms: restoring {len(pointer_files)} LFS payload(s).", flush=True)
    for path, sha, size in pointer_files:
        materialize(path, sha, size)
    print("All found vendor/gms LFS pointer payloads verified.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"ERROR: vendor/gms Git LFS repair failed: {exc}", file=sys.stderr)
        sys.exit(1)
