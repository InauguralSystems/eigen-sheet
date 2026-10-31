#!/usr/bin/env python3
"""Synchronize release metadata and consume changelog fragments."""

import argparse
import datetime
import json
import re
import shutil
from pathlib import Path

CATEGORIES = (
    ("breaking", "Breaking changes"),
    ("added", "Added"),
    ("changed", "Changed"),
    ("fixed", "Fixed"),
    ("internal", "Internal"),
)

parser = argparse.ArgumentParser()
parser.add_argument("version", help="bare semantic version, for example 0.2.0")
parser.add_argument("--date", default=datetime.date.today().isoformat())
args = parser.parse_args()
if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version) is None:
    parser.error("version must be a bare major.minor.patch version")

root = Path(__file__).resolve().parents[1]
manifest_path = root / "eigs.json"
manifest = json.loads(manifest_path.read_text())
manifest["version"] = args.version
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

source_path = root / "sheet.eigs"
source, count = re.subn(r'^VERSION is "[^"]+"$',
                        f'VERSION is "{args.version}"',
                        source_path.read_text(), count=1, flags=re.MULTILINE)
if count != 1:
    raise SystemExit("expected exactly one in-code VERSION")
source_path.write_text(source)

readme_path = root / "README.md"
readme, count = re.subn(
    r"(--pkg add InauguralSystems/sheet \S+ )v[^\s`]+",
    rf"\g<1>v{args.version}", readme_path.read_text(), count=1)
if count != 1:
    raise SystemExit("expected exactly one documented package tag")
readme_path.write_text(readme)

sections = []
archive = root / "changes" / "archive" / f"v{args.version}"
for category, heading in CATEGORIES:
    files = sorted((root / "changes" / category).glob("*.md"))
    if not files:
        continue
    entries = [path.read_text().strip() for path in files]
    sections.append(f"### {heading}\n\n" + "\n".join(entries))
    (archive / category).mkdir(parents=True, exist_ok=True)
    for path in files:
        shutil.move(path, archive / category / path.name)

if not sections:
    raise SystemExit("no changes/<category> fragments to release")
changelog_path = root / "CHANGELOG.md"
old = changelog_path.read_text() if changelog_path.exists() else "# Changelog\n"
entry = f"## [{args.version}] - {args.date}\n\n" + "\n\n".join(sections) + "\n"
changelog_path.write_text(old.rstrip() + "\n\n" + entry)
print(f"prepared v{args.version}; archived {sum(s.count(chr(10) + '-') for s in sections)} fragments")
