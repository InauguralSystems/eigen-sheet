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
d is {"pages": [{"width": 200, "height": 100, "items": [
 {"type":"text", "x":10, "y":70, "size":12, "text":"A (B) \\\\ snowman: ☃"},
 {"type":"line", "x1":10, "y1":50, "x2":190, "y2":50},
 {"type":"rect", "x":10, "y":10, "width":180, "height":30}]}]}
a is pdf.render of d
b is pdf.render of d
print of (json_encode of a)
print of (json_encode of b)
print of (str of (pdf.text_width of ["Hello", 10]))
'''
        app = os.path.join(tmp, "app.eigs")
        open(app, "w", encoding="utf-8").write(program)
        run = subprocess.run([EIGS, app], cwd=tmp, text=True, capture_output=True, timeout=30)
        if run.returncode:
            print("FAIL: freestanding load/run\n" + run.stdout + run.stderr); return 1
        lines = run.stdout.splitlines()
        if len(lines) != 3:
            print("FAIL: unexpected output " + repr(run.stdout)); return 1
        a, b = json.loads(lines[0]), json.loads(lines[1])
        if a != b or a.get("bytes") != b.get("bytes"):
            print("FAIL: two in-memory renders differ"); return 1
        if a.get("replaced") != 2:
            print("FAIL: unsupported character count is %r, expected 2 EigenScript character units" % a.get("replaced")); return 1
        blob = bytes(a["bytes"])
        if b"A \\(B\\) \\\\\\" not in blob:
            print("FAIL: PDF literal metacharacters were not escaped"); return 1
        if not blob.startswith(b"%PDF-1.4") or b"/CreationDate" in blob:
            print("FAIL: header or timestamp invariant"); return 1
        if lines[2] != "22.78":
            print("FAIL: Helvetica AFM width expected 22.78, got " + lines[2]); return 1
        print("PASS: freestanding in-memory render loads and returns identical bytes")
        print("PASS: backslash/parentheses escape; unsupported character becomes '?' and is counted")
        print("PASS: embedded Helvetica AFM metrics measure Hello at 22.78pt/10pt")
    return 0

if __name__ == "__main__":
    sys.exit(main())
