"""MVP Methods Extractor.

The minimum end-to-end loop that grounds an extraction claim: parsed paper text
in -> single LLM call returning (value, verbatim_quote) per field -> Python-side
span resolution -> typed ``ProvenancedField`` values with character-offset spans.

Single-pipeline, single-pass. Deliberately NOT included (post-abstract Methods
Extractor thread): PDF parsing, multi-acquisition partitioning, DeferredToCitation
reasoning, self-critique iteration, cross-validation, confidence calibration.
"""

from __future__ import annotations

__version__ = "0.0.1"
