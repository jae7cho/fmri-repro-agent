# The COBIDAS version criterion, and the retraction of "0/19 report a pipeline version"

**Scope.** This document records what COBIDAS requires of a reported software version, where
that requirement lives in the standard, what AESPA currently implements, and what may be said
about the corpus today. Deferral handling for the Software row is a separate question and is
not settled here.

## What the standard requires

OHBM COBIDAS Report v1.0 (2016-05-19), *Best Practices in Data Analysis and Sharing in
Neuroimaging using MRI*, Nichols TE, Das S, Eickhoff SB, Evans AC, Glatard T, Hanke M,
Kriegeskorte N, Milham MP, Poldrack RA, Poline J-B, Proal E, Thirion B, Van Essen DC, White T,
Yeo BTT. §4.3 "Software Issues", p. 10. This is the committee report, not Nichols et al. (2017)
in *Nature Neuroscience*, which shares a first author and is cited elsewhere in this repository.

The section heading sits on PDF page index 10 and that page's footer reads 10, so the two
paginations coincide and either citation resolves to the same page.

The requirement is that a report gives the exact version of every tool used, and §4.3 states
that a major version number alone does not satisfy it: reporting must give *"not just the major
version number"*. The section supplies four tokens, which are the operative audit criterion:

| Insufficient | Compliant |
|---|---|
| `SPM12` | `SPM12 revision 6225` |
| `FSL 5.0` | `FSL 5.0.8` |

What counts as exact therefore varies by tool. SPM requires a revision token because its major
version is fused into the tool name. FSL's three-component version suffices on its own. §4.3
gives examples rather than a general predicate, so any rule covering other tools is a
generalization built on those examples and should be recorded as one.

Table D.3's Software row carries the same bar in the mandatory-content column, transcribed at
`extractor_mvp/src/extractor_mvp/cobidas.py:13-14`. §4.3 is the body text that says what
"version" means there.

Notably, the one citation-like mechanism §4.3 raises under *Software versions* is the Research
Resource Identifier, and it is recommended in addition to reporting the version rather than in
place of it.

## What AESPA implements, and where the alignment actually lives

The extraction prompt excludes a version fused into a tool name, naming `SPM12`, `SPM8`, and
`SPM99` as names rather than separately stated versions (`extractor.py:132-140`). That rule is
aligned with §4.3.

The code carries no such rule. `_build_version_pf` (`extractor.py:640`) marks the field
`EXTRACTED` when the model returns a value with a verbatim quote, the quote resolves to a span,
and `quote_supports_value` accepts it (`extractor.py:654-663`). The fallback at
`extractor.py:677-681` returns `MissingFromPaper` with reason `version_deferred_to_kb` for
anything failing that gate, and makes no name-versus-version discrimination.
`quote_supports_value` (`span_resolver.py:400-427`) is whole-token containment with no
version-shape logic.

Consequently the §4.3 alignment is carried entirely by the prompt and is unenforced. A model
returning `SPM12` as `base_pipeline_version`, with a quote containing `SPM12`, would pass the
gate and be recorded as `EXTRACTED`.

The spelled-out form (`Statistical Parametric Mapping 12`, mueller_2021) fails the same §4.3
bar as the abbreviated one, so the count of fused cases does not depend on which surface form
a paper uses.

## The 0/19 claim is retracted

`docs/DESIGN_cobidas_coverage.md:28` states as a citable claim that 0 of 19 corpus papers
naming a base pipeline report its version. That claim is false and is retracted.
`docs/ground-truth-protocol.md:393-401` recorded the retraction and named three papers that
report explicit separate versions, read from the papers themselves: oconnor (`C-PAC version
0.4.0`), derosa (`FSL suite (version 5.0.10)`), and liu_2013 (`version 1.1-beta`).

The retraction stands. Its stated mechanism no longer describes the code. That paragraph
attributes the figure to `extractor.py` hardcoding `base_pipeline.version` to
`MissingFromPaper` with a prompt that never asks for a version, and neither is true at HEAD:

- `_build_version_pf` (`extractor.py:640`) is a real extraction path. Searching HEAD for the
  hardcode comment returns nothing.
- The prompt asks for the version (`extractor.py:132`), the field is declared at
  `extractor.py:101`, and it is wired into the call at `extractor.py:990`.
- `assess_coverage` keys the Software row off the extraction status of `base_pipeline.version`
  whenever a version row exists (`render.py:740-741`), which is whenever the outer arm resolves
  a `PipelineRef` (`render.py:265-271`). That status is no longer a constant.

Version extraction was built afterward (`DEVLOG.md:323`). Anyone reading
`ground-truth-protocol.md:393-401` for the mechanism will find a description of code that no
longer exists, inside a correction that is otherwise accurate.

## Extraction status is not compliance status

`base_pipeline.version` reaches `EXTRACTED` when the paper states a version string separately
from the tool name and the quote supports that value. No check applies §4.3's exact-version
bar. A paper writing `FSL (version 5.0)` as a separate string would therefore be recorded as
`EXTRACTED` while failing the criterion §4.3 names on its face.

The three papers above happen to clear the bar, since `5.0.10`, `0.4.0`, and `1.1-beta` are
exact in the sense the `FSL 5.0.8` example illustrates. That is a property of those three
papers and not a guarantee the extractor provides.

Consequently a count of `version.extraction.status == EXTRACTED` is a count of papers that
stated a separate version string, not a count of papers that comply with §4.3.

**Labelling decision recorded here.** Ground-truth labels for this field are to be assigned
against §4.3 read directly, never against extractor output or the prompt wording, because the
prompt encodes the criterion and any label derived from it measures the prompt. Labelling has
not started, and the per-tool exactness rule is to be fixed before it does.

## What is sayable about the corpus today

The corpus rate at which papers report a compliant pipeline version is unestablished. The 0/19
figure restated a hardcoded constant and is retracted. A scored count requires ground-truth
labels and a per-tool exactness rule fixed in advance.

The Software row is unconditionally mandatory because software use is universal, so the
compliance denominator is 19, every paper in the corpus. A descriptive sub-question, how many
of the papers that name a pipeline give an exact version, takes a different denominator.
Recording the two under separate names is a pre-registration item and is not yet written.

The three papers named at `ground-truth-protocol.md:397-398` establish that the 0/19 claim is
false. They do not establish what the true rate is.

Of note, the extractor's separateness predicate and the protocol's hand reading select the same
three papers. That convergence is not independent confirmation: both key on
`base_pipeline.version`, and the protocol passage predates the prompt that now encodes the
criterion.
