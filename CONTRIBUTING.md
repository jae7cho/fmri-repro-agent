# Contributing

Thanks for your interest in `fmri-repro-agent`!

This project is in pre-alpha. Issue templates, PR templates, and more detailed contribution guidelines will land once the MVP stabilizes.

For now:

- **Small fixes** (typos, docs, obvious bugs): open a PR directly.
- **Anything larger** (new agents, schema changes, scope expansions, dependency additions): please open a GitHub Discussion or Issue first so we can align on direction before you invest the time.
- **Questions, ideas, or curious lurking**: Discussions are the right place.

## Development environment

The repository holds two Python packages with separate virtual environments, and only one of
them can run a batch.

| Interpreter | Package it installs | Reaches Bedrock |
|---|---|---|
| `extractor_mvp/.venv/bin/python` | `extractor_mvp` (the MVP extractor) | yes, `boto3` present |
| `.venv/bin/python` (repository root) | `fmri_repro` (the schema package) | no, `boto3` absent |

`import extractor_mvp` succeeds under both, which is the trap. Under the root environment it
resolves as a namespace package with `__file__` set to `None`, so nothing fails at import and a
batch run instead dies at the first model call.

### The shell's `grep` can hide `results/` from you

A second environment fact that silently changes a result, the same class as the interpreter trap
above: in some shells here `grep` is a **function** that filters git-ignored paths on a recursive
search from a directory. Measured:

```
grep -rl 'no_base_pipeline_named' .            ->   0 hits under results/
/usr/bin/grep -rl 'no_base_pipeline_named' .   -> 106 hits under results/
```

An **explicit** path (`grep -r pattern extractor_mvp/results/...`) is not filtered, which is why this
goes unnoticed: most probes work. It bites a *recursive* search used to establish an absence — the
result is a clean zero with no error, and `results/` holds the paid draws, the stored reports and every
diagnostic.

Use `/usr/bin/grep` when the question is "is this anywhere under `results/`", or `git grep` when the
question is about tracked files (it is tracked-only by design, which is correct for that question and
wrong for this one). And state a positive control beside any zero — that is what caught this.

Run a batch with the extractor's own interpreter:

```bash
cd extractor_mvp
./.venv/bin/python -m extractor_mvp.batch --config configs/<name>_config.yaml
```

Batch configs live in `extractor_mvp/configs/` and are tracked. Run output goes to
`extractor_mvp/results/`, which is ignored in full; see that directory's `.gitignore`.

## Run the tests the way CI runs them

```bash
cd extractor_mvp && uv run pytest -m "not live" --cov=extractor_mvp --cov-report=term-missing --cov-fail-under=70
```

That is the `extractor-mvp` job's own command, verbatim from `.github/workflows/ci.yml`. Use it. A
green result from any other invocation is not evidence that CI is green.

**The pass count is environment-dependent, so compare like with like.** All three of these are the
same 335 collected tests:

| where | result | why |
|---|---|---|
| CI, or any machine without the local corpus | `326 passed, 7 skipped, 2 deselected` | 5 corpus tests + 2 render tests skip |
| this laptop, same command | `331 passed, 2 skipped, 2 deselected` | corpus and `results/` are on disk |
| `python -m pytest tests` with no `-m` | `333 passed, 2 skipped` | the `live` pair skips by marker instead of being deselected |

Two guards make the difference, and both key on paths outside the checkout, so a git worktree or a
fresh clone on this machine does **not** reproduce CI:

- `tests/test_methods_finder.py:12` skips on `Path("/Users/cwook/.../tested_lit/sfn_batch")` — an
  absolute path, so it resolves the same from any checkout on this machine.
- `tests/test_render.py:1083`, `:1110` skip when gitignored batch output under `results/` is absent.

**`326 passed, 7 skipped, 2 deselected` is the number to check CI against.** The first version of this
table said 331 was the expectation, measured in a scratchpad worktree that was reaching the laptop's
corpus through that absolute path — stating a local count as CI's, in the section that exists to stop
exactly that.

**Why this is stated as a rule rather than a preference.** An earlier version of this section
prescribed `../.venv/bin/python -m pytest tests -q` and listed two "wrong" invocations whose failures
were `No module named 'pandas'` and `No module named 'tests'`. Those were not local quirks. They were,
verbatim, the two collection errors that had been failing the `extractor-mvp` job since 2026-09-12 —
documented here as environment trivia, with the one invocation that hides them written down as the
procedure. `python -m pytest` puts the cwd on `sys.path` and the root env happened to carry `pandas`,
so the masking was complete and the suite reported a clean count for three weeks.

The generalisation, which is the point: **verify against the checker that will actually run.** A
number produced by a harness nobody else uses certifies the harness, not the code.

## Before and after a push

`git ls-remote origin main` confirms what arrived; it does not confirm the arrival was good. The
remote runs the checks, so read the remote's verdict — both jobs, on the pushed head:

```bash
gh run list --workflow=ci.yml --branch=main --limit=1
gh run view <run-id>
```

Both `lint-and-test` and `extractor-mvp` must read `success`. A job that is merely *queued* is not a
pass, and the overall conclusion can be `failure` with one job green — which is exactly how a red job
stayed unnoticed across 6 pushes and 32 commits. CI runs per **push**, not per commit, so only the
pushed head is ever tested: in one case 21 commits went out together and 15 of them rode in on an
already-broken suite without being tested on their own. Small pushes, checked, or the bisect is yours
to do later.

All contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
