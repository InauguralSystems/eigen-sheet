#!/usr/bin/env python3
"""Issue #100 end-to-end PDF validity, pagination, text, render, reproducibility."""
import hashlib, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
GOLDEN = os.path.join(ROOT, "tests", "golden_issue_100_page1.pgm")


# Decoded-pixel tolerance: antialiasing differs across poppler versions by
# small per-pixel amounts. 0.05% of pixels (242 at 612x792) catches one lost
# row of text (~430 px); lost text inside a cell is the pdftotext oracle's job.
PIXEL_DELTA = 64
PIXEL_FRACTION = 0.0005

def read_pgm(path):
    """Return (width, height), max value, and decoded P5 pixel bytes."""
    data = open(path, "rb").read()
    offset = 0

    def token():
        nonlocal offset
        while True:
            while offset < len(data) and data[offset] in b" \t\r\n":
                offset += 1
            if offset < len(data) and data[offset] == ord("#"):
                offset = data.find(b"\n", offset)
                if offset < 0:
                    raise ValueError("unterminated PGM comment")
                continue
            break
        end = offset
        while end < len(data) and data[end] not in b" \t\r\n":
            end += 1
        value = data[offset:end]
        offset = end
        return value

    if token() != b"P5":
        raise ValueError("golden/render is not a raw P5 PGM")
    width, height, maximum = int(token()), int(token()), int(token())
    if maximum != 255 or offset >= len(data) or data[offset] not in b" \t\r\n":
        raise ValueError("unsupported PGM header")
    offset += 1
    pixels = data[offset:]
    if len(pixels) != width * height:
        raise ValueError("PGM pixel payload has the wrong length")
    return (width, height), maximum, pixels


def pixel_digest(image):
    dimensions, maximum, pixels = image
    return "%dx%d/%d:%s" % (dimensions[0], dimensions[1], maximum, hashlib.sha256(pixels).hexdigest())


def main():
    for tool in ("qpdf", "pdftotext", "docker"):
        if not shutil.which(tool):
            print("FAIL: required oracle tool missing: " + tool); return 1
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("sheet.eigs", "pdf.eigs", "eigs.json"):
            shutil.copy(os.path.join(ROOT, name), tmp)
        cells = []
        for c in range(8):
            col = chr(65 + c)
            cells.append('sheet.set_cell of [s, "%s1", "H%d"]' % (col, c))
            for r in range(1, 80):
                cells.append('sheet.set_cell of [s, "%s%d", "R%02dC%d"]' % (col, r + 1, r, c))
        app = os.path.join(tmp, "app.eigs")
        open(app, "w").write("import sheet\ns is sheet.new_sheet of null\n" + "\n".join(cells) +
            '\nsheet.recalc of s\na is sheet.save_as of [s, "a.pdf", "pdf", "Letter"]\n'
            'b is sheet.save_as of [s, "b.pdf", "PDF", "Letter"]\n'
            'print of (json_encode of {"pages":a.page_count,"breaks":a.breaks,"replaced":a.replaced})\n')
        run = subprocess.run([EIGS, app], cwd=tmp, text=True, capture_output=True, timeout=60)
        if run.returncode:
            print("FAIL: export errored\n" + run.stdout + run.stderr); return 1
        meta = json.loads(run.stdout.strip())
        expected_breaks = [
            {"c0":0,"c1":6,"r0":1,"r1":38}, {"c0":0,"c1":6,"r0":38,"r1":75},
            {"c0":0,"c1":6,"r0":75,"r1":80}, {"c0":6,"c1":8,"r0":1,"r1":38},
            {"c0":6,"c1":8,"r0":38,"r1":75}, {"c0":6,"c1":8,"r0":75,"r1":80}]
        if meta != {"pages":6,"breaks":expected_breaks,"replaced":0}:
            print("FAIL: page count/breaks " + repr(meta)); return 1
        print("PASS: 6 pages with expected down-then-across break positions")
        a, b = os.path.join(tmp, "a.pdf"), os.path.join(tmp, "b.pdf")
        if open(a,"rb").read() != open(b,"rb").read():
            print("FAIL: repeat exports differ"); return 1
        print("PASS: repeat export is byte-identical sha256=" + hashlib.sha256(open(a,"rb").read()).hexdigest())
        check = subprocess.run(["qpdf", "--check", a], text=True, capture_output=True)
        if check.returncode:
            print("FAIL: qpdf --check\n" + check.stdout + check.stderr); return 1
        print("PASS: qpdf --check accepts xref, trailer, and all six pages")
        for page, br in enumerate(expected_breaks, 1):
            txt = os.path.join(tmp, "p%d.txt" % page)
            subprocess.run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), a, txt], check=True)
            words = open(txt).read().split()
            expected = ["H%d" % c for c in range(br["c0"], br["c1"])]
            expected += ["R%02dC%d" % (r,c) for r in range(br["r0"],br["r1"]) for c in range(br["c0"],br["c1"])]
            expected += ["Page", str(page), "of", "6"]
            if sorted(words) != sorted(expected) or len(words) != len(expected):
                print("FAIL: page %d text differs; got=%r expected=%r" % (page, words, expected)); return 1
        print("PASS: pdftotext -layout has exactly each page's cells, repeated header, and footer")
        rendered = os.path.join(tmp, "page1.pgm")
        subprocess.run([os.path.join(ROOT, "tools", "render_golden.sh"), "--render", a, rendered], check=True)
        if os.environ.get("ISSUE100_UPDATE_GOLDEN"):
            shutil.copy(rendered, GOLDEN)
            print("PASS: regenerated reviewed golden with pinned Poppler/font container")
        got = read_pgm(os.path.join(tmp, "page1.pgm"))
        if not os.path.exists(GOLDEN):
            print("FAIL: reviewed golden missing"); return 1
        want = read_pgm(GOLDEN)
        got = read_pgm(os.path.join(tmp, "page1.pgm"))
        keep = os.environ.get("ISSUE100_KEEP_RENDER")
        if keep:
            shutil.copy(os.path.join(tmp, "page1.pgm"), keep)
        # Decoded-pixel comparison with a stated tolerance: poppler versions
        # antialias glyph edges differently, so exact bytes would tie the gate
        # to one poppler build. A real layout fault (a lost or moved row or
        # column) changes thousands of pixels by far more than the threshold.
        if got[0] != want[0] or got[1] != want[1]:
            print("FAIL: page 1 differs from golden (dimensions %s != %s)" % (got[0], want[0])); return 1
        big = sum(1 for a, b in zip(got[2], want[2]) if abs(a - b) > PIXEL_DELTA)
        limit = int(len(want[2]) * PIXEL_FRACTION)
        if big > limit:
            print("FAIL: page 1 differs from golden (%d pixels differ by more than %d; limit %d)" % (big, PIXEL_DELTA, limit)); return 1
        print("PASS: pdftoppm page 1 matches the reviewed golden (%d pixels beyond +/-%d; limit %d)" % (big, PIXEL_DELTA, limit))
    return 0

if __name__ == "__main__":
    sys.exit(main())
