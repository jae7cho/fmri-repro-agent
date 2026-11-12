"""Rules shared by the extraction prompts and mirrored in the checking pass (the author's item 3,
2026-11-09). One text, so the extraction and the check cannot drift apart."""

from __future__ import annotations

#: 2026-11-11 (Stage 2b, the author's item 2): the two part rules (a measure, data type or dataset's
#: preprocessing is preprocessing for that part; "not applied to one part" is a value), in the
#: author's words, which name ALFF, fALFF, ReHo and functional connectivity. Shared with the checking
#: pass through CHECKING_RULES.
PREPROCESSING_RULES = """\
Rules for every field:
- Volumes "co-registered" or "registered" to correct for head motion (to a volume of the same run)
  is motion correction, not coregistration. Coregistration aligns the functional data to an
  anatomical image.
- Preprocessing that a data provider applied to a released dataset (e.g. "minimally preprocessed
  data from the <release>") is reported as applied: give the step and its values with the sentence
  that names the release as the quote.
- Smoothing of statistical, contrast or parameter maps is not preprocessing of the BOLD data: it is
  not spatial smoothing.
- A confound that is computed or made available (framewise displacement, DVARS, motion parameters,
  CompCor components) is not applied unless the paper says it was regressed out, censored or
  otherwise removed.
- Preprocessing applied before a derived measure is computed (e.g. ALFF, fALFF, ReHo, functional
  connectivity), or applied to one data type (e.g. task or rest data) or to one dataset, is
  preprocessing for that part of the data, not analysis: give it with applies_to = the measure, data
  type or dataset in the paper's words.
- A statement that a step was not applied to one part of the data is a value for that part: the
  step's performed is "no" for that part.

"""

#: The same rules, as the checking pass applies them to the draft.
CHECKING_RULES = (
    "Judge every line by these rules, which the draft was extracted under:\n"
    + PREPROCESSING_RULES.split("\n", 1)[1]
)


#: DESIGN_applies_to.md §2 (Stage 1, 2026-11-11): the first hop's own wording of the citation hop's
#: variant rule, with the author's same-phrase instruction (fork B1). One text for the extraction,
#: temporal/volume and spatial prompts. Not part of the checking rules: the checking pass gets its
#: own wording of what a ``[<part>]`` line means. No example is taken from a corpus paper: the five
#: case papers of DESIGN_applies_to.md §3 are scored against this prompt in Stage 2. 2026-11-11
#: (Stage 2b, the author's item 1): compared models, one variant each when each is described; the
#: null "varied across compared models" entry only when the variation is stated without description.
#: 2026-11-11 (pre-rerun item 3): what a part is, and that a value is never one (ciric_2017's Stage 2b
#: record gave temporal_filtering.applied_to's value "all regressors" as a part).
VARIANT_RULES = """\
## Values that differ by what they apply to
When the text gives different values for a field for different parts of its data -- different
derived measures, analyses or parts of the paper, data types, scanners or sites, or named
preprocessing variants -- the field is "varied": return each value in variants, with applies_to = the paper's own words for the part it
applies to, verbatim_quote = the sentence that states the value, and applies_to_quote = the
sentence that ties the value to the part when that is not the value's own sentence.
- A part names a subset of the paper's data or analyses (a measure, a data type, a dataset, a named
  variant). A value is never a part: "all regressors", "6 mm" or "band-pass" is a value, not
  something a value applies to.
- Never choose one value. Never write "all" for a value the text ties to a part of its data.
- A step stated as not performed for one part and performed for another is a varied
  `<step>_performed` ("no" for that part, "yes" for the other).
- Use the IDENTICAL phrase for the same part across fields: copy one applies_to once, then reuse it
  word for word in every field where that part has its own value.
- A value that holds for all of the data stays "extracted", as before.
- When the paper compares several preprocessing or denoising models applied to the same data and
  describes each one, return one variant per model, applies_to = the model's name in the paper.
  Only when the text states that a field varies across the compared models WITHOUT describing them,
  return ONE variant with value null, applies_to "varied across compared models", and
  verbatim_quote = the sentence that states the variation.

"""


#: 2026-11-11 (pre-rerun item 1): a value's evidence as 1-3 verbatim spans, never one quote stitched
#: from several places. For the extraction, temporal/volume and spatial prompts (the step fields).
QUOTE_RULES = """\
## Quotes
verbatim_quote is one passage copied exactly from the text. When the evidence for a value is in two
or three places (for example, the value in one sentence and the step or part it belongs to in
another), give each place as its own quote: the first in verbatim_quote, the others in
additional_quotes (at most two), each copied exactly. Never stitch: never join words from different
sentences into one quote, and never leave words out of the middle of a quote. A variant's quotes
follow the same rule.

"""
