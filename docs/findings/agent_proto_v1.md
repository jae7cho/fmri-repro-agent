# Agent prototype v1: the 19 labelled papers, scored against corpus_full_v2

2026-11-10. An experiment outside the pipeline: no repo code changed. Code, per-run outputs and
score files are in `docs/findings/agent_proto/`. Counts only; no rates. liu_2005, tang_2025 and
wheaton_2004 show states and agree/disagree only.

## Setup

- **Agent.** `agent_proto_v2.py` with `aespa_cli.py`. The pipeline's methods text is in the first
  message. Tools:
  - outline, search and read on any open doc;
  - references and open_reference on the paper or an opened reference (up to 2 citations deep;
    local PDF, else Europe PMC by the entry's DOI or CrossRef's);
  - kb_lookup on the defaults KB.
- **Submission.** One submit carries every field. A submit missing scored fields is answered once.
- **Provenances (six).** EXTRACTED, CITED, DEFERRED_UNREAD, KB_DEFAULT, MODEL, NOT_REPORTED.
- **Checks (code).**
  - The quote resolves in its document (`span_resolver.resolve_quote`).
  - A number in the value is in the quote.
  - A KB_DEFAULT value is named by a kb_lookup result in the run.
- **Model.** `claude-sonnet-4-5-20250929`, the pipeline's model.
- **Runner.** Headless Claude Code (`claude -p`) on the author's plan (`run_local.py`), 2 at a time:
  - one empty working folder per paper;
  - the only command is the paper's wrapper; the only writable file is its `submit.json`;
  - every other file and web tool is denied; no MCP servers; no settings sources.
- **Code.** Repo code at `3fa32b6` (a worktree); KB at `8ea0350`.
- **Scripts are archived verbatim** as `docs/findings/agent_proto/*.py.txt`, so the repo's ruff
  hooks leave them byte-identical to what ran.
- **Script hashes (sha256, first 12), of those files.**
  - `aespa_cli.py` 12bff9c7a203
  - `run_local.py` cb5467698892
  - `agent_proto_v2.py` 9bcacf2b0b4c
  - `score_agent.py` 1bc3c2ce9109
- **Scoring.** `score_agent.py` maps each run to what the three scorers read, then runs
  score_motion, score_motion_resolved and score_smoothing_filtering unchanged.
  - The pipeline side is `results/corpus_full_v2_labelled19`.
  - It reproduces the recorded v2 counts: motion 8 / 11; smoothing 13 / 3 / 6; filtering 11 / 5 / 6.

## The three scorers, 19 papers

| scorer | agent | pipeline |
|---|---|---|
| motion, bullet 1: agree / disagree | 6 / 13 | 8 / 11 |
| resolved tool, KB-confirmed: agree / disagree / label blank | 8 / 0 / 3 | 8 / 1 / 5 |
| resolved tool, model-only: agree / disagree / label blank | 0 / 1 / 7 | 0 / 0 / 5 |
| smoothing: agree / disagree / not separable | 12 / 4 / 6 | 13 / 3 / 6 |
| filtering: agree / disagree / not separable | 11 / 5 / 6 | 11 / 5 / 6 |
| model calls (agent: Claude Code turns) | 453 | 208 |
| cost, USD (agent: Claude Code's API-equivalent figure) | 12.82 | 11.33 (metered) |

### Rows where the agent and the pipeline differ

| scorer | agent agrees, pipeline does not | pipeline agrees, agent does not |
|---|---|---|
| motion, bullet 1 | binder_1999 | gordon_2014, weber_2024, wheaton_2004 |
| resolved tool | — | — |
| smoothing | braun_2015, viduarre_2017 | liu_2005, oconnor_2017, poldrack_2015 |
| filtering | braun_2015 | oconnor_2017 |

The resolved tool for derosa_2025 disagrees on both sides: model-only for the agent, KB-confirmed
for the pipeline. The pipeline's v2 disagreement is the one `7d96e0b` changed.

## Per paper

| paper | label | method: agent | method: pipeline | tool: agent | tool: pipeline | smoothing: agent | smoothing: pipeline | filtering: agent | filtering: pipeline | turns | equiv. $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| agtzidis_2020 | named_tool | described_only ✗ | described_only ✗ | agree (KB-confirmed) | agree (KB-confirmed) | reported ✓ | reported ✓ | not_reported ✓ | not_reported ✓ | 12 | 0.6615 |
| binder_1999 | described_only | described_only ✓ | undecided ✗ | label blank (KB-confirmed) | label blank (model-only) | reported ✗ | reported ✗ | not_reported ✓ | not_reported ✓ | 23 | 0.5715 |
| braun_2015 | deferred | deferred ✓ | deferred ✓ | label blank (model-only) | label blank (model-only) | deferred ✓ | not_reported ✗ | deferred ✓ | not_reported ✗ | 29 | 0.7609 |
| chen_2015 | deferred | described_only ✗ | described_only ✗ | label blank (model-only) | label blank (KB-confirmed) | not separable; not separable | not separable; not separable | not separable; not separable | not separable; not separable | 22 | 0.6137 |
| ciric_2017 | named_tool | named_tool ✓ | named_tool ✓ | agree (KB-confirmed) | agree (KB-confirmed) | not separable; not separable | not separable; not separable | reported ✗ | reported ✗ | 13 | 0.6027 |
| cole_2013 | named_tool | described_only ✗ | described_only ✗ | agree (KB-confirmed) | agree (KB-confirmed) | reported ✓ | reported ✓ | reported ✗ | stated_not_performed ✗ | 10 | 0.4131 |
| derosa_2025 | named_tool | named_tool ✓ | named_tool ✓ | disagree (model-only) | disagree (KB-confirmed) | reported ✓ | reported ✓ | reported ✓ | reported ✓ | 37 | 0.9885 |
| gordon_2014 | named_tool | described_only ✗ | named_tool ✓ | agree (KB-confirmed) | agree (KB-confirmed) | reported ✓ | reported ✓ | reported ✓ | reported ✓ | 12 | 0.3068 |
| liu_2005 | named_tool | unverifiable ✗ | unverifiable ✗ | agree (KB-confirmed) | agree (KB-confirmed) | reported ✗ | stated_not_performed ✓ | unverifiable ✗ | unverifiable ✗ | 30 | 0.748 |
| liu_2013 | deferred | described_only ✗ | described_only ✗ | label blank (model-only) | label blank (KB-confirmed) | reported ✓ | reported ✓ | reported ✓ | reported ✓ | 20 | 0.5823 |
| mueller_2021 | named_tool | described_only ✗ | described_only ✗ | agree (KB-confirmed) | agree (KB-confirmed) | reported ✓ | reported ✓ | reported ✓ | reported ✓ | 20 | 0.6904 |
| oconnor_2017 | deferred | described_only ✗ | described_only ✗ | label blank (KB-confirmed) | label blank (KB-confirmed) | stated_not_performed ✗ | not_reported ✓ | stated_not_performed ✗ | not_reported ✓ | 29 | 0.8209 |
| poldrack_2015 | deferred | described_only ✗ | described_only ✗ | label blank (model-only) | label blank (model-only) | unverifiable ✗ | reported ✓ | reported ✓ | reported ✓ | 48 | 1.0163 |
| power_2014 | described_only | described_only ✓ | described_only ✓ | label blank (model-only) | label blank (model-only) | reported ✓ | reported ✓ | not separable; not separable | not separable; not separable | 17 | 0.4445 |
| tang_2025 | named_tool | described_only ✗ | described_only ✗ | agree (KB-confirmed) | agree (KB-confirmed) | not separable; not separable | not separable; not separable | not separable; not separable | not separable; not separable | 18 | 0.6856 |
| vanderwal_2016 | deferred | described_only ✗ | described_only ✗ | label blank (model-only) | label blank (KB-confirmed) | stated_not_performed ✓ | stated_not_performed ✓ | reported ✓ | reported ✓ | 28 | 0.7587 |
| viduarre_2017 | deferred | deferred ✓ | deferred ✓ | label blank (KB-confirmed) | label blank (KB-confirmed) | deferred ✓ | not_reported ✗ | not_reported ✗ | not_reported ✗ | 47 | 1.1419 |
| weber_2024 | deferred | described_only ✗ | deferred ✓ | label blank (model-only) | label blank (model-only) | reported ✓ | reported ✓ | reported ✓ | reported ✓ | 23 | 0.69 |
| wheaton_2004 | named_tool | described_only ✗ | named_tool ✓ | agree (KB-confirmed) | agree (KB-confirmed) | reported ✓ | reported ✓ | reported ✓ | reported ✓ | 15 | 0.3267 |

## Runs

- **All 23 runs submitted.** No run hit a cap.
  - Turns per run: 9 to 48.
  - Claude Code's API-equivalent cost: USD 15.58 in all.
- **Permission refusals:** 11, all Bash `cat` or `ls`, in 8 runs. Every run still submitted
  through its wrapper.

## Variance: three papers run twice

19 scored fields per paper.

| paper | same tool | same tool provenance | same method state | same smoothing state | same filtering state | provenance differs | value differs |
|---|---|---|---|---|---|---|---|
| achuthan_2023 | yes | yes | yes | yes | yes | 4 | 4 |
| viduarre_2017 | yes | yes | yes | yes | yes | 1 | 1 |
| gordon_2014 | yes | yes | yes | yes | yes | 0 | 4 |

## What came before this run

Bedrock (`bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`), metered by LiteLLM:

| batch | runs | USD |
|---|---|---|
| two-paper test (prototype v0, two tries) | 4 | 4.48 |
| v1, 23 at once: every run throttled and crashed | 23 | 1.52 |
| v1, 2 at a time: braun_2015 out of retries; stopped | 2 | 1.55 |
| v1, 1 at a time: 58 throttles in 25 turns; stopped | 1 | 0.75 |
| v1, stopped for v2 (agtzidis 42 calls; braun partial) | 2 | 1.40 |
| v2, stopped for the reference-list fix | 2 | 1.19 |
| v2, stopped for DEFERRED_UNREAD and the KB pipeline nudge (11 complete) | 12 | 11.55 |
| v2, network outage (DNS): 1 complete, 1 partial, 21 failed on their first call | 23 | 1.84 |
| total | | 24.28 |

- **Bedrock throttling.** From 21:15 on 2026-11-09, after the 23-run burst, calls were throttled
  at about 1 per minute.
  - On 2026-11-10 a call was refused with "Too many tokens per day".
  - The account's listed Sonnet 4.5 quotas are 50 requests and 5,000,000 tokens per minute
    (cross-region). The only listed daily token quota for Sonnet 4.5 is the 1M-context
    variant's: 27,000,000.
  - Which quota throttled the calls is not determined from here.

### Changes between versions, each before its batch

- **v1 → v2:**
  - the methods text up front;
  - one submit for every field;
  - a missing-fields reply.
- **v2 fixes:**
  - each opened paper's own reference list, and CrossRef DOIs;
  - DEFERRED_UNREAD, and the KB pipeline nudge;
  - multi-word reference search;
  - a connection-error retry (Bedrock only).
- **Claude Code runner:** the submission is written to a file (a heredoc and a JSON argument
  were refused by the permission check).
- **Earlier runs:** the 11 v2 Bedrock runs before DEFERRED_UNREAD are not scored here.
