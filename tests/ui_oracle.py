#!/usr/bin/env python3
"""UI oracle for eigen-sheet: the rendered grid must decode back to the model.

eigen-sheet has a UI (the grid view), so a value diff is not enough — it never
looks at what a user sees. This renders through the real `draw_grid`, screen-
shots the window, and DECODES each cell's pixels back into text, asserting they
equal `display(sheet, addr)` computed headlessly. Catches rendering bugs: a
cell drawn in the wrong place, a dropped value, a wrong glyph.

Exact decode, not fuzzy OCR: the bitmap font (forced via a nonexistent
EIGS_GFX_FONT) is a fixed atlas, and draw_grid lays each cell's text on a 12x14
px glyph grid — cell (col c, row r, 0-based) has text origin (8 + c*84,
8 + r*16), 84 px = 7 glyph cells wide. The checker validates itself: a broken
draw_grid (blanks one cell) is run through the same pipeline and must be caught.

Assumes an X display (CI wraps this in `xvfb-run`). Needs the gfx build
(EIGENSCRIPT), xdotool, xwd, PIL.
"""
import os, subprocess, sys, tempfile, time, struct, shutil
from PIL import Image

EIGS = os.environ.get("EIGENSCRIPT", "eigenscript")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ, SDL_VIDEODRIVER="x11", EIGS_GFX_FONT="/nonexistent/force-bitmap.ttf")

CELL_W, CELL_H, ORIGIN_X, ORIGIN_Y = 12, 14, 8, 8   # scale-2 bitmap glyph grid
COL_W, ROW_H = 84, 20                                # draw_grid cell pitch
NCOLS, NROWS = 3, 4                                  # region the oracle checks
INK = lambda r, g, b: min(r, g, b) > 150
CHARSET = "".join(chr(c) for c in range(33, 127))

# The demo grid draw_grid/_demo builds (kept integer-valued for clean decode).
CELLS = {"A1": "5", "A2": "3", "A3": "=A1+A2", "A4": "=SUM(A1:A3)",
         "B1": "=A4*2-1", "B2": "=(A1+A2)/2"}


def eigs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def num_to_col(n):
    o = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        o = chr(65 + r) + o
    return o


def model_grid(edit_path):
    """display(sheet, addr) for every cell in the checked region: rows of strings."""
    setup = "\n".join('sheet.set_cell of [s, "%s", "%s"]' % (a, v) for a, v in CELLS.items())
    prints = []
    for r in range(1, NROWS + 1):
        for c in range(1, NCOLS + 1):
            addr = "%s%d" % (num_to_col(c), r)
            prints.append('print of (%s + "\\t" + (sheet.display of [s, "%s"]))'
                          % (eigs_str(addr), addr))
    prog = ("import sheet\ns is sheet.new_sheet of null\n%s\nsheet.recalc of s\n%s\n"
            % (setup, "\n".join(prints)))
    out = _run(edit_path, prog)
    disp = {}
    for line in out.splitlines():
        if "\t" in line:
            a, v = line.split("\t")
            disp[a] = v
        elif line:  # a cell whose display is empty prints "ADDR\t" -> split gives ["ADDR",""]
            disp[line] = ""
    grid = []
    for r in range(1, NROWS + 1):
        grid.append([disp.get("%s%d" % (num_to_col(c), r), "") for c in range(1, NCOLS + 1)])
    return grid


def _run(edit_path, prog):
    tmp = tempfile.mkdtemp()
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        shutil.copy(edit_path, os.path.join(md, "sheet.eigs"))
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
        app = os.path.join(tmp, "app.eigs"); open(app, "w").write(prog)
        r = subprocess.run([EIGS, app], cwd=tmp, env=ENV, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(r.stdout + r.stderr)
        return r.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _capture(edit_path, render_body, title, w=720, h=480):
    tmp = tempfile.mkdtemp()
    try:
        md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
        shutil.copy(edit_path, os.path.join(md, "sheet.eigs"))
        shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
        app = os.path.join(tmp, "r.eigs")
        prog = ('import sheet\n%s\n'
                'ok is gfx_open of [%d, %d, %s]\n'
                'n is 0\n'
                'loop while n < 600:\n'
                '    %s\n'
                '    gfx_present of null\n'
                '    gfx_delay of 16\n'
                '    n is n + 1\n'
                'gfx_close of null\n'
                % (render_body["setup"], w, h, eigs_str(title), render_body["frame"]))
        open(app, "w").write(prog)
        proc = subprocess.Popen([EIGS, app], cwd=tmp, env=ENV,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            wid = None
            for _ in range(50):
                time.sleep(0.1)
                r = subprocess.run(["xdotool", "search", "--name", title],
                                   env=ENV, capture_output=True, text=True)
                if r.stdout.strip():
                    wid = r.stdout.strip().split("\n")[0]; break
            if not wid:
                raise RuntimeError("window never appeared: " + (proc.stdout.read() or ""))
            time.sleep(0.3)
            xwd = os.path.join(tmp, "s.xwd")
            subprocess.run(["xwd", "-id", wid, "-out", xwd], env=ENV, check=True, capture_output=True)
            return _xwd_to_image(xwd)
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except Exception: proc.kill()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _xwd_to_image(path):
    d = open(path, "rb").read()
    f = struct.unpack(">25I", d[:100])
    hs, pw, ph, bpl, ncolors = f[0], f[4], f[5], f[12], f[19]
    off = hs + ncolors * 12
    img = Image.new("RGB", (pw, ph)); px = img.load()
    for y in range(ph):
        row = off + y * bpl
        for x in range(pw):
            p = struct.unpack_from("<I", d, row + x * 4)[0]
            px[x, y] = ((p >> 16) & 255, (p >> 8) & 255, p & 255)
    return img


def _cell_sig(px, cx, cy):
    return frozenset((dx, dy) for dy in range(CELL_H) for dx in range(CELL_W)
                     if INK(*px[cx + dx, cy + dy]))


def build_atlas(edit_path):
    body = {"setup": "", "frame": "gfx_clear of [16,18,28]\n    gfx_text of [8, 8, %s, 220,222,235, 2]"
            % eigs_str(CHARSET)}
    img = _capture(edit_path, body, "eigen-sheet-atlas", w=CELL_W * len(CHARSET) + 40, h=40)
    px = img.load()
    atlas = {}
    for k, ch in enumerate(CHARSET):
        atlas[_cell_sig(px, ORIGIN_X + k * CELL_W, ORIGIN_Y)] = ch
    atlas[frozenset()] = ""   # blank glyph cell
    return atlas


def decode_grid(img, atlas):
    """Decode the rendered grid into rows of cell strings."""
    px = img.load(); W, H = img.size
    grid = []
    for r in range(NROWS):
        row = []
        for c in range(NCOLS):
            ox = ORIGIN_X + c * COL_W
            oy = ORIGIN_Y + r * ROW_H
            s = ""
            for k in range(COL_W // CELL_W):     # up to 7 glyph cells per grid cell
                cx = ox + k * CELL_W
                if cx + CELL_W > W or oy + CELL_H > H:
                    break
                ch = atlas.get(_cell_sig(px, cx, oy), "�")
                if ch == "":
                    break
                s += ch
            row.append(s)
        grid.append(row)
    return grid


def render_grid(edit_path, atlas):
    body = {"setup": ("s is sheet.new_sheet of null\n"
                      + "\n".join('sheet.set_cell of [s, "%s", "%s"]' % (a, v) for a, v in CELLS.items())
                      + "\nsheet.recalc of s"),
            "frame": "sheet.draw_grid of [s, %d, %d]" % (NCOLS, NROWS)}
    return decode_grid(_capture(edit_path, body, "eigen-sheet v0.1.0"), atlas)


def main():
    edit_path = os.path.join(REPO, "sheet.eigs")
    atlas = build_atlas(edit_path)
    print("atlas: %d glyphs" % len(atlas))
    model = model_grid(edit_path)
    shown = render_grid(edit_path, atlas)
    failures = 0
    if shown == model:
        print("PASS grid render decodes to model:")
        for row in model:
            print("     " + " | ".join("%-6s" % c for c in row))
    else:
        failures += 1
        print("FAIL grid render != model\n   model : %r\n   screen: %r" % (model, shown))

    # validate the checker: a broken draw_grid (blanks B1) must be caught.
    broken = os.path.join(tempfile.mkdtemp(), "sheet.eigs")
    src = open(edit_path).read().replace(
        "            local txt is display of [sheet, addr]",
        '            local txt is display of [sheet, addr]\n            if addr == "B1":\n                txt is ""')
    assert src != open(edit_path).read(), "planted-fault substitution did not apply"
    open(broken, "w").write(src)
    bmodel = model_grid(edit_path)
    bshown = render_grid(broken, atlas)
    if bshown != bmodel:
        print("PASS checker  broken draw_grid (blanks B1) was caught")
    else:
        failures += 1
        print("FAIL checker  planted render bug slipped through")

    if failures:
        print("\n%d UI-oracle failure(s)" % failures); sys.exit(1)
    print("\nall UI-oracle checks passed")


if __name__ == "__main__":
    main()
