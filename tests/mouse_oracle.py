#!/usr/bin/env python3
"""Mouse+keyboard oracle for eigen-sheet: drive REAL input, verify by pixels.

An interaction is not verified until real input moved real pixels (the #599
lesson). So this launches the interactive app and drives xdotool through the
primary editing flow — click cell A4 to select it, TYPE "=A1*A2", press Enter —
then decodes the grid to assert the edit landed and propagated:

    click A4 -> type "=A1*A2" -> Enter
      => A4 becomes 15 (=5*3), and B1 recomputes 31 -> 29 (=A4*2-1).

That exercises the whole chain a user relies on: the click reaches the real
event decode and selects the cell; the keystrokes reach the char mapping and
build the edit buffer; Enter commits and recalc propagates through the
dependency graph; and the render shows it. The checker is validated by
asserting the post-edit grid differs from the untouched baseline (so a no-op
drive can't pass).

Assumes an X display (CI wraps this in xvfb-run). Needs the gfx build, xdotool,
xwd, PIL. Reuses the render oracle's bitmap-font decoder.
"""
import os, subprocess, sys, time, tempfile, shutil
import ui_oracle as u   # atlas + grid decoder + capture helpers

EIGS, ENV, REPO = u.EIGS, u.ENV, u.REPO

# run()'s interactive grid geometry (window coords): formula bar (26) + column
# header (22) push the first data row to y=48.
GX, GY, CW, RH = 36, 48, 72, 22


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


def click(origin, wx, wy):
    subprocess.run(["xdotool", "mousemove", str(origin[0] + wx), str(origin[1] + wy)], env=ENV)
    subprocess.run(["xdotool", "click", "1"], env=ENV)
    time.sleep(0.2)


def type_text(t):
    subprocess.run(["xdotool", "type", "--", t], env=ENV); time.sleep(0.2)


def press(k):
    subprocess.run(["xdotool", "key", k], env=ENV); time.sleep(0.2)


def grab(wid, tmp, atlas):
    xwd = os.path.join(tmp, "m.xwd")
    for _ in range(20):
        time.sleep(0.15)
        if subprocess.run(["xwd", "-id", wid, "-out", xwd], env=ENV, capture_output=True).returncode == 0:
            img = u._xwd_to_image(xwd)
            if u._has_content(img):
                return u.decode_grid(img, atlas, gy=GY)
    raise RuntimeError("could not capture the window")


def main():
    atlas = u.build_atlas(os.path.join(REPO, "sheet.eigs"))
    proc, wid, tmp, origin = launch()
    try:
        if origin is None:
            raise RuntimeError("no window position")
        print("window origin (screen): %r" % (origin,))
        baseline = grab(wid, tmp, atlas)          # A4=16 (row3,col0), B1=31 (row0,col1)
        print("baseline A4=%r B1=%r" % (baseline[3][0], baseline[0][1]))

        click(origin, *cell_xy(0, 3))             # select A4 with the mouse
        type_text("=A1*A2")                       # type a formula
        press("Return")                           # commit
        after = grab(wid, tmp, atlas)
        print("after    A4=%r B1=%r" % (after[3][0], after[0][1]))

        fails = 0
        if after[3][0] != "15":
            fails += 1; print("FAIL A4 did not become 15 (typed edit didn't land): %r" % after[3][0])
        if after[0][1] != "29":
            fails += 1; print("FAIL B1 did not recompute to 29 (no dependency propagation): %r" % after[0][1])
        if after == baseline:
            fails += 1; print("FAIL grid unchanged — the drive was a no-op")
        if not fails:
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
