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
