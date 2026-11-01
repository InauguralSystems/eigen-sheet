#!/usr/bin/env python3
"""Every test entry point must run in CI, or be named in a reviewed allowlist.

The workflow is a hand-written list of steps, so a test file added without a
step is green forever without ever running (tests/issue_74_aggregate_args.py
sat unwired from #80 on). This check enumerates tests/*.py and tests/*.sh and
requires each one to be invoked by a workflow under .github/workflows/
(comments do not count), or to be listed in tests/NOT_IN_CI.txt with a reason.

Allowlist format, one entry per line:  tests/<file>  # <reason>
An entry with no reason, for a file that does not exist, or for a file that is
already wired is itself a failure, so the list cannot rot.

  python3 tools/check_ci_wiring.py              # check this repository
  python3 tools/check_ci_wiring.py --self-test  # prove each failure mode fires
"""
import glob
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWLIST = os.path.join("tests", "NOT_IN_CI.txt")


def strip_yaml_comments(text):
    """Drop what cannot run a test: YAML comments (whole-line and ` #`
    trailing) and step `name:` labels. A '#' with no preceding whitespace (a
    shell $#, a URL fragment) is kept as content."""
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        if re.match(r"^\s*(-\s+)?name:", line):
            continue
        out.append(re.sub(r"\s#.*$", "", line))
    return "\n".join(out)


def test_files(root):
    found = []
    for pattern in ("*.py", "*.sh"):
        found += glob.glob(os.path.join(root, "tests", pattern))
    return sorted(os.path.relpath(p, root).replace(os.sep, "/") for p in found)


def workflow_text(root):
    parts = []
    for path in sorted(glob.glob(os.path.join(root, ".github", "workflows", "*.y*ml"))):
        with open(path, encoding="utf-8") as f:
            parts.append(strip_yaml_comments(f.read()))
    return "\n".join(parts)


def is_wired(rel, text):
    return re.search(r"(?<![\w./-])" + re.escape(rel) + r"(?![\w.-])", text) is not None


def read_allowlist(root):
    """{path: reason}, plus a list of malformed-line errors."""
    entries, errors = {}, []
    path = os.path.join(root, ALLOWLIST)
    if not os.path.exists(path):
        return entries, errors
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            body = line.strip()
            if not body or body.startswith("#"):
                continue
            name, _, reason = body.partition("#")
            name, reason = name.strip(), reason.strip()
            if not reason:
                errors.append("%s:%d: %s has no reason" % (ALLOWLIST, n, name))
            entries[name] = reason
    return entries, errors


def check(root):
    """Returns a list of failure messages (empty = pass) and the counts."""
    failures = []
    files = test_files(root)
    text = workflow_text(root)
    allow, errors = read_allowlist(root)
    failures += errors
    wired = 0
    for rel in files:
        if is_wired(rel, text):
            wired += 1
            if rel in allow:
                failures.append("%s is wired into CI but still allowlisted in %s"
                                % (rel, ALLOWLIST))
        elif rel not in allow:
            failures.append("%s is not run by any workflow step and is not in %s"
                            % (rel, ALLOWLIST))
    for rel in allow:
        if rel not in files:
            failures.append("%s lists %s, which is not a tests/*.py|*.sh file"
                            % (ALLOWLIST, rel))
    return failures, len(files), wired


def report(root):
    failures, total, wired = check(root)
    for msg in failures:
        print("FAIL: " + msg)
    if failures:
        print("FAIL: %d CI wiring problem(s)" % len(failures))
        return 1
    print("PASS: %d/%d test entry points run in CI; %d allowlisted"
          % (wired, total, total - wired))
    return 0


def self_test():
    """Each planted fault must be reported; the clean tree must pass."""
    wf_clean = ("jobs:\n  t:\n    steps:\n"
                "      - run: python3 tests/a.py\n"
                "      - run: bash tests/b.sh\n")
    cases = [
        ("clean tree", wf_clean, {"a.py": "", "b.sh": ""}, None, False),
        ("unwired test file", wf_clean,
         {"a.py": "", "b.sh": "", "issue_999_x.py": ""}, None, True),
        ("named only in a comment",
         wf_clean + "      # python3 tests/c.py\n",
         {"a.py": "", "b.sh": "", "c.py": ""}, None, True),
        ("named only in a trailing comment",
         wf_clean + "      - run: true  # tests/c.py\n",
         {"a.py": "", "b.sh": "", "c.py": ""}, None, True),
        ("named only in a step label",
         wf_clean + "      - name: Run tests/c.py\n        run: true\n",
         {"a.py": "", "b.sh": "", "c.py": ""}, None, True),
        ("a longer name does not wire a prefix",
         wf_clean.replace("tests/a.py", "tests/a.py_old"),
         {"a.py": "", "b.sh": ""}, None, True),
        ("allowlisted with a reason", wf_clean,
         {"a.py": "", "b.sh": "", "helper.py": ""},
         "tests/helper.py  # imported by a.py, not an entry point\n", False),
        ("allowlisted without a reason", wf_clean,
         {"a.py": "", "b.sh": "", "helper.py": ""}, "tests/helper.py\n", True),
        ("stale allowlist entry", wf_clean, {"a.py": "", "b.sh": ""},
         "tests/gone.py  # removed\n", True),
        ("wired and still allowlisted", wf_clean, {"a.py": "", "b.sh": ""},
         "tests/a.py  # was manual\n", True),
    ]
    bad = 0
    for label, wf, tests, allow, expect_fail in cases:
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".github", "workflows"))
            os.makedirs(os.path.join(tmp, "tests"))
            with open(os.path.join(tmp, ".github", "workflows", "ci.yml"), "w") as f:
                f.write(wf)
            for name, body in tests.items():
                with open(os.path.join(tmp, "tests", name), "w") as f:
                    f.write(body)
            if allow is not None:
                with open(os.path.join(tmp, ALLOWLIST), "w") as f:
                    f.write(allow)
            failures, _, _ = check(tmp)
            if bool(failures) == expect_fail:
                print("PASS self-test: %s -> %s" % (label, "red" if failures else "green"))
            else:
                bad += 1
                print("FAIL self-test: %s -> %s (expected %s)"
                      % (label, "red" if failures else "green",
                         "red" if expect_fail else "green"))
    return bad


def main(argv):
    if "--self-test" in argv:
        bad = self_test()
        if bad:
            print("FAIL: %d self-test case(s) wrong" % bad)
            return 1
    return report(ROOT)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
