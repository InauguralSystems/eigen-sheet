#!/usr/bin/env python3
"""Issue #100: freestanding, deterministic PDF core oracle."""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")


def main():
    source = open(os.path.join(ROOT, "pdf.eigs"), encoding="utf-8").read()
    forbidden = ("read_text of", "read_bytes of", "write_text of", "write_bytes of",
                 "gfx_", "random_", "now of", "shell")
    bad = [word for word in forbidden if word in source]
    if bad:
        print("FAIL: PDF core contains host/I/O calls: " + ", ".join(bad)); return 1
    print("PASS: pure core contains no filesystem, gfx, random, clock, or shell calls")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(os.path.join(ROOT, "pdf.eigs"), tmp)
        program = r'''import pdf
d is {"pages": [{"width": 123456789, "height": (0 - 0), "items": [
 {"type":"text", "x":10, "y":70, "size":12, "text":"café A (B) \\\\ snowman: ☃"},
 {"type":"line", "x1":-0.5, "y1":-1.25, "x2":-0.001, "y2":0},
 {"type":"rect", "x":10, "y":10, "width":180, "height":30}]}]}
a is pdf.render of d
b is pdf.render of d
print of (json_encode of a)
print of (json_encode of b)
print of (str of (pdf.text_width of ["Hello", 10]))
c is pdf.encode_text of "a\tb\nc"
print of (json_encode of [c.replaced, c.text])
print of (json_encode of [pdf.text_width of ["—", 10], pdf.text_width of ["…", 10], pdf.text_width of ["“", 10]])
big is pdf.render of {"pages": [{"width": 200, "height": 200, "items": [{"type":"text", "x":10, "y":100, "size":40, "text":"gyp", "max_width":180}]}]}
print of (json_encode of big)
'''
        app = os.path.join(tmp, "app.eigs")
        open(app, "w", encoding="utf-8").write(program)
        run = subprocess.run([EIGS, app], cwd=tmp, text=True, capture_output=True, timeout=30)
        if run.returncode:
            print("FAIL: freestanding load/run\n" + run.stdout + run.stderr); return 1
        lines = run.stdout.splitlines()
        if len(lines) != 6:
            print("FAIL: unexpected output " + repr(run.stdout)); return 1
        a, b = json.loads(lines[0]), json.loads(lines[1])
        if a != b or a.get("bytes") != b.get("bytes"):
            print("FAIL: two in-memory renders differ"); return 1
        if a.get("replaced") != 1:
            print("FAIL: unsupported character count is %r, expected one Unicode character" % a.get("replaced")); return 1
        blob = bytes(a["bytes"])
        if b"caf\xe9" not in blob or b"caf??" in blob:
            print("FAIL: UTF-8 text was not mapped to WinAnsi"); return 1
        if b"A \\(B\\) \\\\\\" not in blob:
            print("FAIL: PDF literal metacharacters were not escaped"); return 1
        if not blob.startswith(b"%PDF-1.4") or b"/CreationDate" in blob:
            print("FAIL: header or timestamp invariant"); return 1
        if lines[2] != "22.78":
            print("FAIL: Helvetica AFM width expected 22.78, got " + lines[2]); return 1
        if b"-0.500 -1.250 m -0.001 0 l S" not in blob or b"/MediaBox [0 0 123456789 0]" not in blob:
            print("FAIL: negative fractional, negative-zero, or large coordinate formatting"); return 1
        ctl = json.loads(lines[3])
        if ctl != [2, "a?b?c"]:
            print("FAIL: control characters must be one '?' and one count each, got %r" % (ctl,)); return 1
        widths = json.loads(lines[4])
        if widths != [10, 10, 3.33]:
            print("FAIL: cp1252 0x80-0x9f glyph widths (em dash, ellipsis, left quote) expected [10, 10, 3.33], got %r" % (widths,)); return 1
        clip = bytes(json.loads(lines[5])["bytes"])
        if b"10 91.720 180 " not in clip:
            print("FAIL: 40pt text clip must start 0.207 em (8.28pt) below the baseline"); return 1
        print("PASS: control characters counted once; cp1252 extension widths; clip descent scales with size")
        print("PASS: freestanding in-memory render loads and returns identical bytes")
        print("PASS: backslash/parentheses escape; unsupported character becomes '?' and is counted")
        print("PASS: embedded Helvetica AFM metrics measure Hello at 22.78pt/10pt")
        print("PASS: negative fractions, negative zero, and large coordinates serialize exactly")
    return 0

if __name__ == "__main__":
    sys.exit(main())
