#!/usr/bin/env python3
"""Regression checks for issue #72's documented standalone runtime."""

import os
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text()
WORKFLOW = (ROOT / ".github/workflows/test.yml").read_text()
EIGENSCRIPT = os.environ.get("EIGENSCRIPT")


def standalone_commands():
    match = re.search(r"## Run it standalone\s+```sh\n(.*?)\n```", README, re.S)
    assert match, "README has no shell fence under 'Run it standalone'"
    return match.group(1)


def test_readme_uses_the_ci_pin_and_zlib_build():
    commands = standalone_commands()
    pins = set(re.findall(r"git clone[^\n]*--branch ([^ ]+)[^\n]*EigenScript", WORKFLOW))
    assert len(pins) == 1, "CI EigenScript clone pins disagree: %r" % sorted(pins)
    pin = next(iter(pins))

    assert "git clone --depth 1 --branch %s " % pin in commands
    assert "make -C EigenScript zlib" in commands
    assert ".github/workflows/test.yml" in README[README.index("## Run it standalone"):]


def test_ci_binary_can_inflate_xlsx_payloads():
    assert EIGENSCRIPT, "EIGENSCRIPT must point to the README/CI zlib binary"
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "inflate.eigs"
        # A valid empty raw-DEFLATE stream; this is the same capability that
        # from_xlsx uses for compressed OOXML parts.
        probe.write_text("print of (str of (len of (inflate of [3,0])))\n")
        result = subprocess.run(
            [EIGENSCRIPT, str(probe)], capture_output=True, text=True, timeout=30
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "compiled without zlib support" not in result.stdout + result.stderr


if __name__ == "__main__":
    test_readme_uses_the_ci_pin_and_zlib_build()
    test_ci_binary_can_inflate_xlsx_payloads()
    print("PASS: README standalone commands use CI's pin and a zlib-capable runtime")
