#!/usr/bin/env python3
"""Mouse oracle for eigen-sheet: drive REAL pointer input, verify by pixels.

A dropdown/menu is not verified until a real click moved real pixels (the #599
lesson). So this launches the interactive app, drives xdotool through the whole
mouse flow — click a cell to select it, click the "Insert" button to open the
dropdown, click a menu item — and then DECODES the grid to assert the mutation
landed and propagated:

    select A4 -> open dropdown -> click "=A1*A2"
      => A4 becomes 15 (=5*3), and B1 recomputes 31 -> 29 (=A4*2-1).

The dependency propagation through a mouse-driven edit is the payoff: the click
has to reach the real event decode, mutate the model, and trigger recalc. The
checker is validated by asserting the post-click grid actually differs from the
untouched baseline (so a no-op drive can't pass), and by driving the popup
click-trap: the menu item must win the click over the grid cell beneath it.

Assumes an X display (CI wraps this in xvfb-run). Needs the gfx build, xdotool,
xwd, PIL. Reuses the render oracle's bitmap-font decoder.
"""
import os, subprocess, sys, time, tempfile, shutil
import ui_oracle as u   # same dir: atlas + grid decoder + capture helpers

EIGS = u.EIGS
ENV = u.ENV
REPO = u.REPO

# Interactive-run grid geometry (window coords), from sheet.eigs run().
GX, GY, CW, RH = 36, 22, 72, 22
BTN = (83, 448 + 12)                   # Insert button center
ITEM1 = (83, 448 - (3 - 1) * 22 + 10)  # menu item k=1 ("=A1*A2") center


def cell_xy(col, row):   # 0-based -> window-pixel center of the cell
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
            wid = r.stdout.strip().split("\n")[0]
            break
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


def click(origin, wx, wy):
    subprocess.run(["xdotool", "mousemove", str(origin[0] + wx), str(origin[1] + wy)], env=ENV)
    subprocess.run(["xdotool", "click", "1"], env=ENV)
    time.sleep(0.25)


def grab(wid, tmp, atlas):
    xwd = os.path.join(tmp, "m.xwd")
    for _ in range(20):
        time.sleep(0.15)
        if subprocess.run(["xwd", "-id", wid, "-out", xwd], env=ENV, capture_output=True).returncode == 0:
            img = u._xwd_to_image(xwd)
            if u._has_content(img):
                return u.decode_grid(img, atlas)
    raise RuntimeError("could not capture the window")


def main():
    atlas = u.build_atlas(os.path.join(REPO, "sheet.eigs"))
    proc, wid, tmp, origin = launch()
    try:
        if origin is None:
            raise RuntimeError("no window position")
        print("window origin (screen): %r" % (origin,))
        baseline = grab(wid, tmp, atlas)   # A4=16 (row3,col0), B1=31 (row0,col1)
        print("baseline A4=%r B1=%r" % (baseline[3][0], baseline[0][1]))

        click(origin, *cell_xy(0, 3))      # select A4
        click(origin, *BTN)                # open the Insert dropdown
        click(origin, *ITEM1)              # click "=A1*A2"
        after = grab(wid, tmp, atlas)
        print("after    A4=%r B1=%r" % (after[3][0], after[0][1]))

        fails = 0
        if after[3][0] != "15":
            fails += 1; print("FAIL A4 did not become 15 (mouse edit didn't land): %r" % after[3][0])
        if after[0][1] != "29":
            fails += 1; print("FAIL B1 did not recompute to 29 (no dependency propagation): %r" % after[0][1])
        if after == baseline:
            fails += 1; print("FAIL grid unchanged — the drive was a no-op")
        if not fails:
            print("PASS mouse flow: select A4 -> dropdown -> '=A1*A2' -> A4=15, B1 recalculated 31->29")
        if fails:
            sys.exit(1)
        print("\nmouse oracle passed")
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
