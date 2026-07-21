#!/usr/bin/env python3
"""Mouse+keyboard oracle for eigen-sheet: drive REAL input, verify by pixels.

An interaction is not verified until real input moved real pixels (the #599
lesson). This launches the interactive app and drives xdotool through the two
primary flows, verifying each by decoding the rendered pixels:

  1. DRAG-select A1:A4 (real press -> stepped motion -> release) and read the
     status bar back: it must show "Sum:32" over "Count:4" (5+3+8+16).
  2. click A4, TYPE "=A1*A2", press Enter => A4 becomes 15 and B1 recomputes
     31 -> 29 (the typed edit propagates through the dependency graph).

The drag exercises real motion events with the button held (exactly the class
of bug #599 was); the type exercises the char mapping and recalc. The checker
is validated by asserting the post-edit grid differs from the baseline.

Assumes an X display (CI wraps this in xvfb-run). Needs the gfx build, xdotool,
xwd, PIL. Reuses the render oracle's bitmap-font decoder.
"""
import os, subprocess, sys, time, tempfile, shutil
import ui_oracle as u

EIGS, ENV, REPO = u.EIGS, u.ENV, u.REPO

# run()'s interactive geometry (window coords): formula bar (26) + col header
# (22) put the first data row at y=48; the status bar text sits at H-20=460.
GX, GY, CW, RH = 36, 48, 72, 22
STATUS_XY = (8, 460)


def cell_xy(col, row):
    return (GX + col * CW + CW // 2, GY + row * RH + RH // 2)


def launch():
    tmp = tempfile.mkdtemp()
    md = os.path.join(tmp, "eigs_modules", "sheet"); os.makedirs(md)
    shutil.copy(os.path.join(REPO, "sheet.eigs"), os.path.join(md, "sheet.eigs"))
    shutil.copy(os.path.join(REPO, "eigs.json"), os.path.join(md, "eigs.json"))
    shutil.copy(os.path.join(REPO, "main.eigs"), os.path.join(tmp, "main.eigs"))
    proc = subprocess.Popen([EIGS, "main.eigs"], cwd=tmp, env=ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    wid = origin = None
    for _ in range(150):
        time.sleep(0.2)
        r = subprocess.run(["xdotool", "search", "--name", "eigen-sheet"],
                           env=ENV, capture_output=True, text=True)
        if r.stdout.strip():
            wid = r.stdout.strip().split("\n")[0]; break
        if proc.poll() is not None:
            raise RuntimeError("app exited early: " + (proc.stdout.read() or ""))
    if not wid:
        raise RuntimeError("window never appeared")
    g = subprocess.run(["xdotool", "getwindowgeometry", wid], env=ENV,
                       capture_output=True, text=True).stdout
    for line in g.splitlines():
        if "Position:" in line:
            xy = line.split("Position:")[1].split("(")[0].strip()
            origin = tuple(int(v) for v in xy.split(","))
    return proc, wid, tmp, origin


def mv(origin, wx, wy):
    subprocess.run(["xdotool", "mousemove", str(origin[0] + wx), str(origin[1] + wy)], env=ENV)


def click(origin, wx, wy):
    mv(origin, wx, wy); subprocess.run(["xdotool", "click", "1"], env=ENV); time.sleep(0.2)


def drag(origin, path):
    mv(origin, *path[0]); subprocess.run(["xdotool", "mousedown", "1"], env=ENV); time.sleep(0.1)
    for wx, wy in path[1:]:
        mv(origin, wx, wy); time.sleep(0.1)
    subprocess.run(["xdotool", "mouseup", "1"], env=ENV); time.sleep(0.2)


def type_text(t):
    subprocess.run(["xdotool", "type", "--", t], env=ENV); time.sleep(0.2)


def press(k):
    subprocess.run(["xdotool", "key", k], env=ENV); time.sleep(0.2)


def grab_img(wid, tmp):
    xwd = os.path.join(tmp, "m.xwd")
    for _ in range(20):
        time.sleep(0.15)
        if subprocess.run(["xwd", "-id", wid, "-out", xwd], env=ENV, capture_output=True).returncode == 0:
            img = u._xwd_to_image(xwd)
            if u._has_content(img):
                return img
    raise RuntimeError("could not capture the window")


def decode_line(img, atlas, x, y, n=40):
    """Decode a horizontal run of glyph cells into a string (blanks dropped)."""
    px = img.load(); W, H = img.size
    s = ""
    for k in range(n):
        cx = x + k * u.CELL_W
        if cx + u.CELL_W > W or y + u.CELL_H > H:
            break
        s += atlas.get(u._cell_sig(px, cx, y), "")
    return s


def main():
    atlas = u.build_atlas(os.path.join(REPO, "sheet.eigs"))
    proc, wid, tmp, origin = launch()
    fails = 0
    try:
        if origin is None:
            raise RuntimeError("no window position")
        print("window origin (screen): %r" % (origin,))
        baseline = u.decode_grid(grab_img(wid, tmp), atlas, gy=GY)
        print("baseline A4=%r B1=%r" % (baseline[3][0], baseline[0][1]))

        # 1) drag-select A1:A4, read the live status bar
        drag(origin, [cell_xy(0, 0), cell_xy(0, 1), cell_xy(0, 2), cell_xy(0, 3)])
        status = decode_line(grab_img(wid, tmp), atlas, *STATUS_XY)
        print("status bar decoded: %r" % status)
        if "Sum:32" not in status:
            fails += 1; print("FAIL status Sum over A1:A4 should be 32: %r" % status)
        if "Count:4" not in status:
            fails += 1; print("FAIL status Count over A1:A4 should be 4: %r" % status)
        if "Sum:32" in status and "Count:4" in status:
            print("PASS drag A1:A4 -> status bar Sum:32 Count:4")

        # 2) click A4, type a formula, verify the edit + propagation
        click(origin, *cell_xy(0, 3))
        type_text("=A1*A2")
        press("Return")
        after = u.decode_grid(grab_img(wid, tmp), atlas, gy=GY)
        print("after edit A4=%r B1=%r" % (after[3][0], after[0][1]))
        if after[3][0] != "15":
            fails += 1; print("FAIL A4 did not become 15: %r" % after[3][0])
        if after[0][1] != "29":
            fails += 1; print("FAIL B1 did not recompute to 29: %r" % after[0][1])
        if after == baseline:
            fails += 1; print("FAIL grid unchanged — the drive was a no-op")
        if after[3][0] == "15" and after[0][1] == "29":
            print("PASS click A4 -> type '=A1*A2' -> Enter -> A4=15, B1 recalculated 31->29")

        if fails:
            sys.exit(1)
        print("\nmouse+keyboard oracle passed")
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
