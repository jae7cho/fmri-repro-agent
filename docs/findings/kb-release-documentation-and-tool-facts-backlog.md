# Backlog: dataset release to processing documentation, and tool facts, with sources (KB)

**Status: BACKLOG, recorded 2026-11-03 at the author's request; not built.** Read by the
released-derivatives state (`docs/design/DESIGN_citation_hop.md`, design only).

## 1. Dataset release to processing documentation

One row per release, never per dataset: a release's pipeline can differ from the one a methods paper
describes (gracia-tabuenca_2024 uses ABCD 3.0 and the ABCD-BIDS Community Collection 3165; Hagler et
al. (2019) describes Releases 2.0 and 2.0.1).

| column | content |
|---|---|
| dataset, release | as the release names itself (e.g. ABCD 3.0; ABCD-BIDS Community Collection 3165; HCP 1200 Subjects) |
| release date | from the release's own notes |
| derivatives | what the release distributes, by name (e.g. FC matrices, minimally preprocessed BOLD) |
| documented pipeline | the steps the documentation lists, each mapped to a D.3 row, with tool and version when stated |
| document, section | the release notes or pipeline paper that documents it (e.g. the ABCD release notes for that release; Glasser et al. (2013) for the HCP minimal preprocessing pipelines) |
| source, checked | URL or DOI, and the date the row was checked against it |

## 2. Tool facts

| column | content |
|---|---|
| tool | canonical name and the aliases the drafter returns |
| fact | one step the tool performs, mapped to a D.3 row (e.g. FreeSurfer recon-all includes skull stripping) |
| applies to | the data it covers (recon-all: the T1w image, not the BOLD series) |
| source, checked | the tool's documentation, with version range and date checked |

## Rules for building both

- Each row is a curation decision checked against its source, never recalled; the same discipline as
  `kb-exact-version-rules-backlog.md`.
- A release or tool with no row produces no inference, and the report says it is not in the KB.
- Every value from either table sits on the inference arm with its basis, and never changes a
  COBIDAS row's state.
