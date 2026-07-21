#!/usr/bin/env python3
"""Style render oracle: a styled cell renders its background AND stays readable.

Reuses the ui_oracle pixel machinery. Styles A1 of the demo grid with a
saturated background and a bright custom text color, renders through the real
draw_grid, then asserts two things from the screenshot:
  1. the cell's value still DECODES ("5") — a saturated bg (min channel < 150)
     doesn't trip the ink test, and a bright text color keeps the glyph shape,
     so the style doesn't corrupt the value;
  2. the background is actually painted — sampled pixels in the cell's left
     region (away from the right-aligned glyph) match the set bg color.

Needs the gfx build + xvfb + xdotool + PIL (same as ui_oracle).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_oracle as U

BG = [180, 40, 40]      # saturated red: min channel 40 < 150, so not "ink"
FG = [255, 255, 200]    # bright: min channel 200 > 150, so the glyph decodes


CBG = [40, 160, 40]     # conditional green: min channel 40 < 150, not "ink"


def render_styled(edit_path, atlas):
    setup = ("s is sheet.new_sheet of null\n"
             + "\n".join('sheet.set_cell of [s, "%s", "%s"]' % (a, v) for a, v in U.CELLS.items())
             + '\nsheet.set_style of [s, "A1", {"bg": [%d,%d,%d], "color": [%d,%d,%d], "align": "right"}]\n' % (BG[0], BG[1], BG[2], FG[0], FG[1], FG[2])
             # A2 (=3) gets a value-driven conditional: >0 -> green background
             + '\nsheet.set_conditional of [s, "A2", [{"op": ">", "value": 0, "style": {"bg": [%d,%d,%d]}}]]\n' % (CBG[0], CBG[1], CBG[2])
             + "sheet.recalc of s")
    body = {"setup": setup, "frame": "sheet.draw_grid of [s, %d, %d, 0]" % (U.NCOLS, U.NROWS)}
    img = U._capture(edit_path, body, "eigen-sheet v0.1.0")
    grid = U.decode_grid(img, atlas)
    px = img.load()
    # A1 static-style bg (left region; right-aligned glyph is far right)
    samples = [px[U.GX + 4, U.GY + 6], px[U.GX + 8, U.GY + 14], px[U.GX + 6, U.GY + 10]]
    # A2 conditional bg (one row down)
    cond = [px[U.GX + 4, U.GY + U.RH + 6], px[U.GX + 8, U.GY + U.RH + 14]]
    return grid, samples, cond


def close(a, b, tol=40):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def main():
    edit_path = os.path.join(U.REPO, "sheet.eigs")
    atlas = U.build_atlas(edit_path)
    grid, samples, cond = render_styled(edit_path, atlas)
    failures = 0

    if sum(1 for s in cond if close(s, CBG)) >= 1:
        print("PASS A2 conditional background painted %r (value-driven: 3 > 0)" % CBG)
    else:
        failures += 1
        print("FAIL A2 conditional bg not painted; samples=%r want~%r" % (cond, CBG))

    if grid[0][0] == "5":
        print("PASS styled A1 still decodes to '5' (bg + custom text color don't corrupt the value)")
    else:
        failures += 1
        print("FAIL styled A1 decoded to %r, not '5'" % grid[0][0])

    bg_ok = sum(1 for s in samples if close(s, BG))
    if bg_ok >= 2:
        print("PASS A1 background painted %r (%d/%d samples match)" % (BG, bg_ok, len(samples)))
    else:
        failures += 1
        print("FAIL A1 background not painted; samples=%r want~%r" % (samples, BG))

    # the rest of the (unstyled) grid must be unaffected
    rest = U.model_grid(edit_path)
    if grid[1] == rest[1] and grid[0][1:] == rest[0][1:]:
        print("PASS the unstyled cells around A1 are unchanged")
    else:
        failures += 1
        print("FAIL styling A1 disturbed other cells\n  got : %r\n  want: %r" % (grid, rest))

    if failures:
        print("\n%d style-render failure(s)" % failures); sys.exit(1)
    print("\nstyle rendering verified: background painted, value still readable")


if __name__ == "__main__":
    main()
