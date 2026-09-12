#!/usr/bin/env python3
"""Re-render identity gate: which papers' reports does a code change alter?

Renders every paper in a batch results directory twice — once through the library code
at ``--against`` (a git worktree, loaded via ``PYTHONPATH``), once through the working
tree — and diffs the two. The input is held fixed and only the library varies, so a
difference is attributable to the code change by construction. That is why this exists
rather than a stored-baseline comparison: a baseline answers "does today match some past
day", which conflates a render change with an input change.

THE DRIVER IS ALWAYS THE WORKING-TREE COPY OF THIS FILE. ``--emit-to`` re-invokes this
same path as a subprocess with a different ``PYTHONPATH``; only the library moves. A
worktree-resident driver would fail immediately, since this script does not exist at
older refs.

Two library packages are editable installs resolving to the working tree
(``_editable_impl_extractor_mvp.pth``, ``_editable_impl_fmri_repro_agent.pth``).
``PYTHONPATH`` overrides them, and BOTH must be overridden or old ``render.py`` imports
new ``fmri_repro``.

NEVER writes into ``<results-dir>/papers``. That directory holds the only copy of the
rendered reports, it is gitignored (``git ls-files`` returns 0 for it), so an in-place
overwrite is unrecoverable and leaves no diff to notice.

Byte-identity here is pinned to an interpreter and a pydantic version: report row order
comes from ``for name in cls.model_fields`` (render.py:277), i.e. pydantic
field-definition order. A pydantic upgrade or a field reorder in
``src/fmri_repro/spec/preprocessing.py`` changes bytes with no set or hash involved, so
both versions are recorded next to every result.

RUN THE NEGATIVE CONTROL, NOT JUST THE SELF-TEST. ``--against HEAD`` returns 19 identical,
but so does a silently failed ``PYTHONPATH`` override, because both subprocesses then run
working-tree code. The self-test's pass condition is satisfied by the failure it should
catch, so it proves nothing on its own. The control is the only check that distinguishes a
working override from a broken one, and any future ref needs its own expected set derived
BEFORE running it.

    --against d31e8b7   ->   7 changed, 12 identical

d31e8b7 is ``c9c2951^``. The 7 are exactly the papers with no ``base_pipeline.version``
row, the set that reaches cobidas.py:181 — binder_1999, braun_2015, cole_2013, liu_2005,
poldrack_2015, power_2014, viduarre_2017. Note that 7 is right and 2 is wrong: c9c2951's
*violation section* moved for the two deferrals only (braun 1->0, binder 1->1), but it
changed ``covered`` as well as ``addressed``, so the Software row moved from "Not assessed
by AESPA" into "Assessed by AESPA" in the header of all seven. A section-level prediction
against a file-level instrument under-counts.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_MANIFEST_HEADER = (
    "# Re-render identity manifest.\n"
    "# Columns: paper_id  sha256(input .json)  sha256(output .md)\n"
    "#\n"
    "# THESE HASHES NAME FILES THIS REPOSITORY DOES NOT CONTAIN. Both the .json inputs\n"
    "# and the .md outputs live under extractor_mvp/results/, which is ignored in full.\n"
    "# A matching manifest proves the reports are UNCHANGED. It never proves they are\n"
    "# correct, and it cannot be checked on a clone that lacks the run.\n"
    "#\n"
    "# Inputs are hashed as well as outputs so a mismatch is diagnosable: inputs equal\n"
    "# and outputs differing means the render changed, which is the signal. Inputs\n"
    "# differing means the baseline is stale and the check is void, not failing.\n"
)


def _require_dir(path: Path, what: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"{what} not found: {resolved}")
    return resolved


def _require_file(path: Path, what: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{what} not found: {resolved}")
    return resolved


def _papers_dir(results_dir: Path) -> Path:
    return _require_dir(results_dir / "papers", "papers/ under --results-dir")


def _versions() -> dict[str, str]:
    import pydantic

    return {"python": sys.version.split()[0], "pydantic": pydantic.__version__}


# --------------------------------------------------------------------------- emit mode


def _render_one(json_path: Path) -> str:
    """Render one stored paper JSON back into its report.

    Imports are function-local so the module can be driven without the library present,
    and so the subprocess picks up whichever copy ``PYTHONPATH`` selects.
    """
    from fmri_repro.spec.migrations import parse_any_version

    from extractor_mvp.methods_finder import MethodsSlice
    from extractor_mvp.render import to_report

    data = json.loads(json_path.read_text(encoding="utf-8"))
    # The real MethodsSlice, not a shim: to_protocol reads four of its eight fields
    # (suspicious, found_via, slice_ratio, ended_at, at render.py:632-642) and `text` is
    # not among them, but constructing the real class means a schema change surfaces
    # loudly here instead of diverging silently.
    methods = MethodsSlice(text="", **data["methods"])
    preprocessing = parse_any_version(data["preprocessing"])
    # source= binds to the JSON's paper_id, not the filename stem: the two agree today
    # and diverge only under corruption, which is the case worth catching.
    # Bound to a local first: the pre-commit mypy hook runs with additional_dependencies: []
    # and so sees to_report as untyped, making a bare return a no-any-return error.
    report: str = to_report(preprocessing, source=data["paper_id"], methods_slice=methods)
    return report


def _emit(results_dir: Path, out_dir: Path) -> int:
    papers = _papers_dir(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for json_path in sorted(papers.glob("*.json")):
        (out_dir / f"{json_path.stem}.md").write_text(_render_one(json_path), encoding="utf-8")
        n += 1
    (out_dir / "_versions.json").write_text(json.dumps(_versions()), encoding="utf-8")
    print(f"emitted {n} report(s) to {out_dir}")
    return 0


# ------------------------------------------------------------------------- differ mode


def _run_emit(script: Path, results_dir: Path, out_dir: Path, src_roots: list[Path]) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(str(p) for p in src_roots)
    proc = subprocess.run(
        [sys.executable, str(script), "--results-dir", str(results_dir), "--emit-to", str(out_dir)],
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"render subprocess failed (PYTHONPATH={env['PYTHONPATH']})\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )


def _repo_root(start: Path) -> Path:
    out = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(out.stdout.strip())


def _differ(results_dir: Path, ref: str) -> int:
    script = Path(__file__).resolve()  # ALWAYS the working-tree copy
    repo = _repo_root(script.parent)
    papers = _papers_dir(results_dir)

    tmp = Path(tempfile.mkdtemp(prefix="rerender-gate-"))
    worktree = tmp / "worktree"
    try:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), ref],
            capture_output=True,
            text=True,
            check=True,
        )

        old_out, new_out = tmp / "old", tmp / "new"
        _run_emit(
            script,
            results_dir,
            old_out,
            [worktree / "extractor_mvp" / "src", worktree / "src"],
        )
        _run_emit(
            script,
            results_dir,
            new_out,
            [repo / "extractor_mvp" / "src", repo / "src"],
        )

        old_v = json.loads((old_out / "_versions.json").read_text())
        new_v = json.loads((new_out / "_versions.json").read_text())

        ids = sorted(p.stem for p in papers.glob("*.json"))
        changed: list[str] = []
        print(f"\n{'paper_id':<18}{'result'}")
        print("-" * 44)
        for pid in ids:
            a = (old_out / f"{pid}.md").read_text(encoding="utf-8")
            b = (new_out / f"{pid}.md").read_text(encoding="utf-8")
            if a == b:
                print(f"{pid:<18}identical")
            else:
                changed.append(pid)
                print(f"{pid:<18}CHANGED")
        print("-" * 44)
        print(
            f"{len(ids) - len(changed)} identical, {len(changed)} changed   (working tree vs {ref})"
        )
        print(f"python {new_v['python']} / pydantic {new_v['pydantic']}", end="")
        if old_v != new_v:
            print(f"   [!] {ref} ran under python {old_v['python']} / pydantic {old_v['pydantic']}")
        else:
            print()

        for pid in changed:
            old_lines = (old_out / f"{pid}.md").read_text(encoding="utf-8").splitlines()
            new_lines = (new_out / f"{pid}.md").read_text(encoding="utf-8").splitlines()
            print(f"\n=== {pid} ===")
            for line in difflib.unified_diff(
                old_lines, new_lines, ref, "working-tree", lineterm="", n=1
            ):
                print(line)
        return 0
    finally:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
            capture_output=True,
            text=True,
        )
        shutil.rmtree(tmp, ignore_errors=True)


# ----------------------------------------------------------------------- manifest mode


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_rows(results_dir: Path) -> list[tuple[str, str, str]]:
    papers = _papers_dir(results_dir)
    rows = []
    for json_path in sorted(papers.glob("*.json")):
        md = papers / f"{json_path.stem}.md"
        if not md.is_file():
            raise FileNotFoundError(f"report missing for {json_path.stem}: {md}")
        rows.append((json_path.stem, _sha(json_path), _sha(md)))
    return rows


def _manifest_write(results_dir: Path, dest: Path) -> int:
    rows = _manifest_rows(results_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{pid}  {js}  {ms}\n" for pid, js, ms in rows)
    dest.write_text(_MANIFEST_HEADER + body, encoding="utf-8")
    print(f"wrote {len(rows)} row(s) to {dest}")
    return 0


def _manifest_verify(results_dir: Path, src: Path) -> int:
    src = _require_file(src, "--manifest")
    want = {}
    for line in src.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        pid, js, ms = line.split()
        want[pid] = (js, ms)
    have = {pid: (js, ms) for pid, js, ms in _manifest_rows(results_dir)}

    stale, regressed, ok = [], [], 0
    for pid in sorted(set(want) | set(have)):
        w, h = want.get(pid), have.get(pid)
        if w is None or h is None:
            stale.append(f"{pid}: present in {'manifest' if h is None else 'results'} only")
        elif w[0] != h[0]:
            stale.append(f"{pid}: INPUT hash differs — baseline stale, check void")
        elif w[1] != h[1]:
            regressed.append(f"{pid}: input equal, OUTPUT differs — the render changed")
        else:
            ok += 1
    for line in stale + regressed:
        print("  " + line)
    print(f"{ok} matching, {len(regressed)} render-changed, {len(stale)} void/stale")
    return 1 if (stale or regressed) else 0


# ------------------------------------------------------------------------------- entry


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--results-dir",
        required=True,
        type=Path,
        help="batch results directory holding papers/<id>.json (absolute or relative to CWD)",
    )
    ap.add_argument("--against", default="HEAD", help="git ref to compare the working tree against")
    ap.add_argument("--emit-to", type=Path, help=argparse.SUPPRESS)
    ap.add_argument("--write-manifest", type=Path, help="write paper_id/json-sha/md-sha to PATH")
    ap.add_argument("--manifest", type=Path, help="verify against an existing manifest at PATH")
    args = ap.parse_args(argv)

    results_dir = _require_dir(args.results_dir, "--results-dir")
    papers = _papers_dir(results_dir)

    if args.emit_to is not None:
        out = args.emit_to.expanduser().resolve()
        if out == papers or papers in out.parents:
            raise SystemExit(f"refusing to write inside the baseline directory: {out}")
        return _emit(results_dir, out)
    if args.write_manifest is not None:
        return _manifest_write(results_dir, args.write_manifest.expanduser().resolve())
    if args.manifest is not None:
        return _manifest_verify(results_dir, args.manifest)
    return _differ(results_dir, args.against)


if __name__ == "__main__":
    sys.exit(main())
