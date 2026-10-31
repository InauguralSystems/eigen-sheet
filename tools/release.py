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
try:
    datetime.date.fromisoformat(args.date)
except ValueError:
    parser.error("date must be an ISO date (YYYY-MM-DD)")

root = Path(__file__).resolve().parents[1]
manifest_path = root / "eigs.json"
manifest = json.loads(manifest_path.read_text())
current_version = manifest.get("version")
if not isinstance(current_version, str) or re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+", current_version) is None:
    raise SystemExit("eigs.json has no valid current version")
version_key = lambda value: tuple(int(part) for part in value.split("."))
if version_key(args.version) <= version_key(current_version):
    raise SystemExit(
        f"release version {args.version} must be newer than {current_version}")

source_path = root / "sheet.eigs"
source_input = source_path.read_text()
source_versions = re.findall(r'^VERSION is "([^"]+)"$', source_input,
                             flags=re.MULTILINE)
if len(source_versions) != 1:
    raise SystemExit("expected exactly one in-code VERSION")
source, count = re.subn(r'^VERSION is "[^"]+"$',
                        f'VERSION is "{args.version}"',
                        source_input, count=1, flags=re.MULTILINE)
if count != 1:
    raise SystemExit("expected exactly one in-code VERSION")

readme_path = root / "README.md"
readme_input = readme_path.read_text()
readme_versions = re.findall(
    r"--pkg add InauguralSystems/sheet \S+ v([^\s`]+)", readme_input)
if len(readme_versions) != 1:
    raise SystemExit("expected exactly one documented package tag")
readme, count = re.subn(
    r"(--pkg add InauguralSystems/sheet \S+ )v[^\s`]+",
    rf"\g<1>v{args.version}", readme_input, count=1)
if count != 1:
    raise SystemExit("expected exactly one documented package tag")
if source_versions[0] != current_version or readme_versions[0] != current_version:
    raise SystemExit(
        "release metadata is not clean and synchronized: "
        f"eigs.json={current_version}, sheet.eigs={source_versions[0]}, "
        f"README.md={readme_versions[0]}")

sections = []
fragment_files = []
archive = root / "changes" / "archive" / f"v{args.version}"
if archive.exists():
    raise SystemExit(f"release archive already exists: {archive.relative_to(root)}")
for category, heading in CATEGORIES:
    files = sorted((root / "changes" / category).glob("*.md"))
    if not files:
        continue
    entries = [path.read_text().strip() for path in files]
    if any(not entry for entry in entries):
        raise SystemExit(f"empty release fragment in changes/{category}")
    sections.append(f"### {heading}\n\n" + "\n".join(entries))
    fragment_files.extend((path, category) for path in files)

if not sections:
    raise SystemExit("no changes/<category> fragments to release")
changelog_path = root / "CHANGELOG.md"
old = changelog_path.read_text() if changelog_path.exists() else "# Changelog\n"
if re.search(rf"^## \[{re.escape(args.version)}\]", old, re.MULTILINE):
    raise SystemExit(f"CHANGELOG.md already contains v{args.version}")
entry = f"## [{args.version}] - {args.date}\n\n" + "\n\n".join(sections) + "\n"
first_release = re.search(r"^## \[", old, re.MULTILINE)
if first_release:
    changelog = old[:first_release.start()] + entry + "\n" + old[first_release.start():]
else:
    changelog = old.rstrip() + "\n\n" + entry

# All validation and input reads above must succeed before the first mutation.
manifest["version"] = args.version
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
source_path.write_text(source)
readme_path.write_text(readme)
changelog_path.write_text(changelog)
for path, category in fragment_files:
    destination = archive / category
    destination.mkdir(parents=True, exist_ok=True)
    shutil.move(path, destination / path.name)
print(f"prepared v{args.version}; archived {len(fragment_files)} fragments")
