# Backlog: per-tool exact-version rules, with sources (KB)

**Status: BACKLOG, recorded 2026-11-03 at the author's request; not built.**

The Software row is addressed only when every named in-scope software carries an exact version (the
author's ruling dated 2026-11-02). What counts as exact differs by tool, and today the code knows
one tool: `extractor_mvp/src/extractor_mvp/cobidas.py` `_EXACT_RELEASE_PARTS = {"freesurfer": 3}`,
from the author's statement that FreeSurfer releases are 5.3.0 and later. Every other tool's stated
version is taken as exact, and SPM's fused major version (`_FUSED_MAJOR`) is a second special case.

The item: a KB table of per-tool exact-version rules, each row with its source, read by the Software
row in place of both special cases.

| column | content |
|---|---|
| tool | canonical name, with the aliases the drafter returns (e.g. "FreeSurfer v5.1" carries its version in the name, weber_2024 in coverage_v4) |
| exact form | the release scheme (e.g. major.minor.patch; a release name; a revision number) |
| insufficient forms | what reads as partial (e.g. major.minor; a fused major version such as SPM12, COBIDAS §4.3's own example) |
| source | the tool's own release page or changelog, checked against the release itself, with the date checked |

Rules for building it:
- Each row is a curation decision checked against the tool's release history, never recalled. The
  same discipline as `citation-index-backlog.md`'s DOI note.
- A tool with no row keeps today's behaviour (a stated version is taken as exact), and the report
  says the rule is unknown for that tool, so a missing row is visible rather than silently lenient.
- FreeSurfer's row replaces `_EXACT_RELEASE_PARTS`, and SPM's replaces `_FUSED_MAJOR`, each in a
  commit that re-renders the stored vintages through the identity gate with the expected set
  derived first.
