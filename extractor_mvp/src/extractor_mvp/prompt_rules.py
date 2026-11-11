"""Rules shared by the extraction prompts and mirrored in the checking pass (the author's item 3,
2026-11-09). One text, so the extraction and the check cannot drift apart."""

from __future__ import annotations

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
#: case papers of DESIGN_applies_to.md §3 are scored against this prompt in Stage 2.
VARIANT_RULES = """\
## Values that differ by what they apply to
When the text gives different values for a field for different parts of its data -- different
derived measures, analyses or parts of the paper, data types, scanners or sites, or named
preprocessing variants -- the field is "varied": return each value in variants, with applies_to = the paper's own words for the part it
applies to, verbatim_quote = the sentence that states the value, and applies_to_quote = the
sentence that ties the value to the part when that is not the value's own sentence.
- Never choose one value. Never write "all" for a value the text ties to a part of its data.
- A step stated as not performed for one part and performed for another is a varied
  `<step>_performed` ("no" for that part, "yes" for the other).
- Use the IDENTICAL phrase for the same part across fields: copy one applies_to once, then reuse it
  word for word in every field where that part has its own value.
- A value that holds for all of the data stays "extracted", as before.
- When the paper's object of study is a comparison of several preprocessing or denoising models
  applied to the same data, and a field differs across those models, return ONE variant with
  value null, applies_to "varied across compared models", and verbatim_quote = the sentence that
  states the comparison. Do not list the models.

"""
