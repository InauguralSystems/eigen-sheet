#!/usr/bin/env python3
"""Regression tests for release metadata checks and preflight validation."""

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path, ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if (result.returncode == 0) != ok:
        raise AssertionError(
            f"unexpected exit {result.returncode}: {' '.join(args)}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}")
    return result


def synchronize_version(fixture: Path, version: str) -> None:
    manifest_path = fixture / "eigs.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["version"] = version
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    for name in ("sheet.eigs", "README.md"):
        path = fixture / name
        path.write_text(path.read_text().replace("0.2.0", version))


def test_self_test_at_current_and_bumped_versions(tmp: Path) -> None:
    for version in ("0.2.0", "0.2.1"):
        fixture = tmp / version
        fixture.mkdir()
        for name in ("eigs.json", "sheet.eigs", "README.md"):
            shutil.copy2(ROOT / name, fixture / name)
        synchronize_version(fixture, version)
        result = run("python3", str(ROOT / "tools/check_release_versions.py"),
                     "--root", str(fixture), "--self-test", cwd=ROOT)
        assert "PASS: planted mismatch rejected" in result.stdout


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*") if path.is_file() and ".git" not in path.parts
    }


def test_no_fragments_is_byte_identical(tmp: Path) -> None:
    fixture = tmp / "release"
    shutil.copytree(ROOT, fixture, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    changes = fixture / "changes"
    for category in ("breaking", "added", "changed", "fixed", "internal"):
        shutil.rmtree(changes / category, ignore_errors=True)
        (changes / category).mkdir(parents=True)
    run("git", "init", "-q", cwd=fixture)
    run("git", "add", ".", cwd=fixture)
    run("git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-qm", "fixture", cwd=fixture)
    before = tree_hashes(fixture)
    result = run("python3", "tools/release.py", "0.2.1", "--date", "2026-10-31",
                 cwd=fixture, ok=False)
    assert "no changes/<category> fragments" in result.stderr
    assert tree_hashes(fixture) == before
    assert run("git", "status", "--porcelain", cwd=fixture).stdout == ""


with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    test_self_test_at_current_and_bumped_versions(temp)
    test_no_fragments_is_byte_identical(temp)
print("PASS: release tools preflight without mutations")
