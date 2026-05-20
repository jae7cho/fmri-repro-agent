# fmri-repro-agent

An LLM-based agentic tool that ingests a published fMRI research paper (PDF) and emits a ready-to-run replication package.

> Developed on personal time and equipment. Not affiliated with any employer.

## Project overview

`fmri-repro-agent` reads a published fMRI methods section and produces a concrete, executable replication package: BIDS metadata, an `fMRIPrep` pipeline configuration, a BIDS Stats Models JSON, container specifications, Slurm submission scripts, and an explicit confidence/missingness report flagging which parameters were stated in the paper, which were inferred from defaults, and which remain unresolved. The intent is to compress the days-to-weeks of reverse-engineering that currently stands between a published study and an independent re-run.

The motivation is the well-documented reproducibility crisis in fMRI: methods sections routinely omit parameters required to re-run an analysis, default choices vary silently across software versions, and small pipeline differences can flip published conclusions. Rather than treat reproduction as artisanal work, this project treats it as a structured extraction-and-synthesis problem an agent can drive — with humans firmly in the loop on every confidence-flagged decision.

## Status

Pre-alpha. MVP in development. APIs, file layouts, and agent topology will change without notice.

## Scope

In scope: task-based fMRI, resting-state fMRI, naturalistic-stimulus fMRI at standard field strengths (1.5T / 3T) using BOLD contrast.

Out of scope: 7T laminar imaging, VASO and other non-BOLD contrasts, animal imaging, and any form of clinical decision support.

## Architecture

Multi-agent system with three-tier verification:

- **Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph) directed-graph control flow over typed agent nodes.
- **Structured outputs:** [Instructor](https://github.com/jxnl/instructor) + [Pydantic](https://docs.pydantic.dev/) for every cross-agent contract.
- **Model gateway:** [LiteLLM](https://github.com/BerriAI/litellm) so individual agents can be pinned to specific model families without code changes.
- **Verification, tier 1:** Deterministic validators (BIDS schema, JSON Schema, fMRIPrep CLI lint) on every structured output.
- **Verification, tier 2:** Inline self-critique on the highest-risk extraction and synthesis agents.
- **Verification, tier 3:** A global Critic agent run on a different model family from the producing agents, blocking emission when its disagreement exceeds threshold.

## Sibling repository

Curated defaults and prior-art knowledge base: [fmri-defaults-kb](https://github.com/jae7cho/fmri-defaults-kb).

## Citation

See [CITATION.cff](CITATION.cff).

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
