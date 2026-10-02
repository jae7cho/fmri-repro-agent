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

All contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
