#!/usr/bin/env python3
"""Check that every published eigen-sheet version reference agrees."""

import argparse
import json
import re
import tempfile
from pathlib import Path


def versions(root: Path) -> dict[str, str]:
    manifest = json.loads((root / "eigs.json").read_text())
    source = (root / "sheet.eigs").read_text()
    readme = (root / "README.md").read_text()
    source_match = re.search(r'^VERSION is "([^"]+)"$', source, re.MULTILINE)
    readme_match = re.search(
        r"--pkg add InauguralSystems/sheet \S+ v([^\s`]+)", readme
    )
    if source_match is None or readme_match is None:
        raise ValueError("missing VERSION or documented --pkg add tag")
    return {
        "eigs.json": manifest["version"],
        "sheet.eigs": source_match.group(1),
        "README.md": readme_match.group(1),
    }


def check(root: Path) -> None:
    found = versions(root)
    if len(set(found.values())) != 1:
        details = ", ".join(f"{name}={value}" for name, value in found.items())
        raise ValueError(f"release version mismatch: {details}")
    print(f"release versions agree: {next(iter(found.values()))}")


def self_test(root: Path) -> None:
    check(root)  # clean control
    with tempfile.TemporaryDirectory() as directory:
        fixture = Path(directory)
        for name in ("eigs.json", "sheet.eigs", "README.md"):
            (fixture / name).write_text((root / name).read_text())
        path = fixture / "eigs.json"
        path.write_text(path.read_text().replace('"version": "0.2.0"',
                                                  '"version": "9.9.9"'))
        try:
            check(fixture)
        except ValueError as error:
            if "release version mismatch" not in str(error):
                raise
            print(f"PASS: planted mismatch rejected: {error}")
        else:
            raise AssertionError("planted version mismatch was accepted")


parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument("--self-test", action="store_true")
args = parser.parse_args()
if args.self_test:
    self_test(args.root)
else:
    check(args.root)
