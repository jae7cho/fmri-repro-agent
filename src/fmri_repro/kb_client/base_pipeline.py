"""KB-driven inference for ``Preprocessing.base_pipeline.version`` + the seven
KB-backed parameter defaults.

Bridge module. Imports the standalone ``fmri_defaults_kb`` (the KB) and the
local ``fmri_repro.spec.*`` (the spec). The KB never imports anything from
``fmri_repro``; the contract surface is the basis-type literal set
(``KB_BASIS_LITERALS`` ⊆ ``BASIS_CEILINGS.keys()``).

Two entry points:

- :func:`infer_base_pipeline_version` resolves the version's inference arm
  via the KB.
- :func:`fill_dependent_defaults` fills the seven preprocessing-step defaults
  (target_space, resolution_mm, target_surface, surface_registration,
  effective_band_hz, intensity convention/value) IF the resolved version is
  *certain* (Extracted by the paper, or KB-inferred via ``version_default``).
  For ``date_inferred_version`` the seven fields are left untouched — we do
  not stack params on a merely inferred version.
"""

from __future__ import annotations

from datetime import date
from typing import Final, cast

from fmri_defaults_kb import (
    ConditionalParam,
    KbAmbiguousError,
    KbUnknownPipelineError,
    ParamResult,
    VersionCandidate,
    VersionResolution,
    get_param_defaults,
    recognize,
    resolve_version,
)
from fmri_defaults_kb import NotApplicable as KbNotApplicable

from fmri_repro.spec.preprocessing import (
    IntensityNormalization,
    PipelineRef,
    Preprocessing,
    SpatialNormalization,
    SurfaceProjection,
    TemporalFiltering,
)
from fmri_repro.spec.provenance import (
    BASIS_CEILINGS,
    AlternativeInference,
    DateInferredVersionBasis,
    DerivedBasis,
    InferredDefault,
    LeftMissing,
    NotApplicable,
    ProvenancedField,
    VersionDefaultBasis,
)

# The seven preprocessing-parameter fields that the KB can back. Paired
# (step_kind, attribute_name) so we can locate the right step in
# Preprocessing.steps and set the right attribute. Field IDs match attribute
# names per the agent's spec convention (_validate_step_invariants).
SEVEN_DEMOTED_FIELDS: Final[tuple[tuple[str, str], ...]] = (
    ("spatial_normalization", "target_space"),
    ("spatial_normalization", "resolution_mm"),
    ("surface_projection", "target_surface"),
    ("surface_projection", "surface_registration"),
    ("temporal_filtering", "effective_band_hz"),
    ("intensity_normalization", "convention"),
    ("intensity_normalization", "value"),
)

_KIND_TO_CLASS: Final[dict[str, type]] = {
    "spatial_normalization": SpatialNormalization,
    "surface_projection": SurfaceProjection,
    "temporal_filtering": TemporalFiltering,
    "intensity_normalization": IntensityNormalization,
}


# --- public API ------------------------------------------------------------


def infer_base_pipeline_version(
    preprocessing: Preprocessing, paper_date: date | None
) -> Preprocessing:
    """Fill the version-side inference arm of ``preprocessing.base_pipeline``.

    Cases handled (mutates and returns the passed-in ``preprocessing``):

    - ``base_pipeline`` is ``NotApplicable`` (Bassett-style): no-op.
    - Outer ProvenancedField has no extracted PipelineRef and no prior
      inferred default: no-op.
    - ``recognize(name) == None`` and the outer extraction arm is Missing or
      Deferred: demote ``base_pipeline`` to ``NotApplicable`` (the
      negative-control path). If outer extraction was ``Extracted`` (paper
      named something specific), leave the user's claim intact.
    - Version's extraction arm is ``Extracted`` (paper pinned the version):
      no-op (couple_stages forbids touching extracted values).
    - Else: call ``resolve_version`` and wrap into ``InferredDefault[str]``
      with a ``Basis`` subclass and ceiling-clamped confidence. Alternatives
      get the same wrapping for the ``date_inferred_version`` arm.
    """
    pipeline_ref = _get_pipeline_ref(preprocessing.base_pipeline)
    if pipeline_ref is None:
        return preprocessing

    pipeline_id = recognize(pipeline_ref.name)
    if pipeline_id is None:
        if _outer_extraction_uncertain(preprocessing.base_pipeline):
            preprocessing.base_pipeline = NotApplicable()
        return preprocessing

    version_pf = pipeline_ref.version
    if version_pf.extraction.status == "EXTRACTED":
        return preprocessing

    try:
        resolution = resolve_version(pipeline_id, paper_date)
    except KbAmbiguousError as exc:
        pipeline_ref.version = _rebuild_provenanced_field(
            version_pf, inference=LeftMissing(reason=str(exc))
        )
        return preprocessing

    basis = _build_basis(pipeline_id, resolution, paper_date)
    alternatives = [
        _build_alternative_inference(c, pipeline_id, paper_date)
        for c in resolution.alternative_candidates
    ]
    ceiling = BASIS_CEILINGS[resolution.basis_type]
    confidence = min(resolution.proposed_confidence, ceiling)

    inferred = InferredDefault[str](
        value=resolution.resolved_version,
        basis=basis,
        confidence=confidence,
        alternative_inferences=alternatives,
    )
    pipeline_ref.version = _rebuild_provenanced_field(version_pf, inference=inferred)
    return preprocessing


def fill_dependent_defaults(preprocessing: Preprocessing, paper_date: date | None) -> Preprocessing:
    """Fill the seven KB-backed param fields IF the resolved version is *certain*.

    "Certain" = extraction is ``Extracted`` (paper pinned it) OR inference is
    ``InferredDefault`` with ``basis.basis_type == "version_default"``.
    For ``date_inferred_version`` the seven fields are not touched — we don't
    stack params on a merely inferred version.

    For each KB-documented field:

    - concrete value → wrap as ``InferredDefault`` with
      ``VersionDefaultBasis`` and ``confidence ≤ 0.95``;
    - ``NotApplicable`` value (e.g. HCP minimal does not perform temporal
      filtering) → set inference to ``LeftMissing`` with informative reason
      (couple_stages forbids Missing/Deferred + NotApplicable);
    - field whose extraction arm is ``Extracted`` (paper pinned it) → no-op,
      preserving the user's claim.

    Mutates and returns ``preprocessing``.
    """
    pipeline_ref = _get_pipeline_ref(preprocessing.base_pipeline)
    if pipeline_ref is None:
        return preprocessing
    pipeline_id = recognize(pipeline_ref.name)
    if pipeline_id is None:
        return preprocessing

    version = certain_version(pipeline_ref.version)
    if version is None:
        return preprocessing

    field_paths = [f"{kind}.{name}" for kind, name in SEVEN_DEMOTED_FIELDS]
    try:
        results = get_param_defaults(pipeline_id, version, field_paths)
    except KbUnknownPipelineError:
        return preprocessing

    for kind, name in SEVEN_DEMOTED_FIELDS:
        result = results.get(f"{kind}.{name}")
        if result is None:
            continue
        _apply_param_result(preprocessing, kind, name, result, pipeline_id, version)

    return preprocessing


# --- helpers ---------------------------------------------------------------


def _get_pipeline_ref(
    base_pipeline: ProvenancedField[PipelineRef] | NotApplicable,
) -> PipelineRef | None:
    """Return the PipelineRef from base_pipeline if a name is known."""
    if isinstance(base_pipeline, NotApplicable):
        return None
    extraction = base_pipeline.extraction
    if extraction.status == "EXTRACTED":
        return cast(PipelineRef, extraction.value)
    inference = base_pipeline.inference
    if inference.status == "INFERRED_DEFAULT":
        return cast(PipelineRef, inference.value)
    return None


def _outer_extraction_uncertain(
    base_pipeline: ProvenancedField[PipelineRef] | NotApplicable,
) -> bool:
    """True if the outer extraction is Missing/Deferred (no extracted name)."""
    if isinstance(base_pipeline, NotApplicable):
        return False
    return base_pipeline.extraction.status in ("MISSING_FROM_PAPER", "DEFERRED_TO_CITATION")


def certain_version(version_pf: ProvenancedField[str]) -> str | None:
    """Return the version string if certain, else None."""
    if version_pf.extraction.status == "EXTRACTED":
        return cast(str, version_pf.extraction.value)
    inf = version_pf.inference
    if inf.status == "INFERRED_DEFAULT" and inf.basis.basis_type == "version_default":
        return cast(str, inf.value)
    return None


def _build_basis(pipeline_id: str, resolution: VersionResolution, paper_date: date | None):
    if resolution.basis_type == "version_default":
        return VersionDefaultBasis(tool=pipeline_id, version=resolution.resolved_version)
    if resolution.basis_type == "date_inferred_version":
        if paper_date is None:
            raise RuntimeError(
                "KB returned date_inferred_version but paper_date is None — KB contract violation"
            )
        return DateInferredVersionBasis(
            tool=pipeline_id,
            inferred_version=resolution.resolved_version,
            paper_date=paper_date,
        )
    raise ValueError(f"unexpected basis_type from KB: {resolution.basis_type!r}")


def _build_alternative_inference(
    candidate: VersionCandidate, pipeline_id: str, paper_date: date | None
) -> AlternativeInference[str]:
    basis = DateInferredVersionBasis(
        tool=pipeline_id,
        inferred_version=candidate.version,
        paper_date=paper_date or candidate.release_date,
    )
    ceiling = BASIS_CEILINGS["date_inferred_version"]
    return AlternativeInference[str](
        value=candidate.version,
        basis=basis,
        confidence=min(candidate.proposed_confidence, ceiling),
    )


def _apply_param_result(
    preprocessing: Preprocessing,
    step_kind: str,
    field_name: str,
    result: ParamResult,
    pipeline_id: str,
    version: str,
) -> None:
    step = _find_step(preprocessing, step_kind)
    if step is None:
        return
    current_pf: ProvenancedField | None = getattr(step, field_name, None)
    if current_pf is None:
        return
    if current_pf.extraction.status == "EXTRACTED":
        return

    if isinstance(result.value, ConditionalParam):
        _apply_conditional(preprocessing, step, field_name, result.value, current_pf)
        return

    new_inference: LeftMissing | InferredDefault
    if result.value is KbNotApplicable:
        new_inference = LeftMissing(
            reason=(
                f"{pipeline_id} {version} does not apply this step "
                "(KB-marked not_applicable; couple_stages forbids "
                "Missing/Deferred + NotApplicable so encoded as LeftMissing)"
            )
        )
    else:
        basis = VersionDefaultBasis(tool=pipeline_id, version=version)
        confidence = min(result.proposed_confidence, BASIS_CEILINGS["version_default"])
        new_inference = InferredDefault(
            value=result.value,
            basis=basis,
            confidence=confidence,
            alternative_inferences=[],
        )

    setattr(
        step,
        field_name,
        _rebuild_provenanced_field(current_pf, inference=new_inference),
    )


def _apply_conditional(
    preprocessing: Preprocessing,
    step: object,
    field_name: str,
    cond: ConditionalParam,
    current_pf: ProvenancedField,
) -> None:
    """Resolve a default DERIVED from a sibling extracted field (B1).

    Reads the extracted value of ``cond.conditional_on`` (a dotted spec-field path),
    selects the matching rule, and writes an ``InferredDefault`` with ``DerivedBasis``
    capped at ``BASIS_CEILINGS["derived"]`` (0.70). The B0 code-verified-vs-lineage
    asymmetry rides on the rule's ``proposed_confidence`` + ``source`` (no source_type
    enum). Fails closed — no inference — when the sibling field is absent / not
    EXTRACTED, or its value matches no rule (the caller already guards the target field
    being EXTRACTED).
    """
    sib_step_kind, _, sib_attr = cond.conditional_on.rpartition(".")
    sib_step = _find_step(preprocessing, sib_step_kind)
    if sib_step is None:
        return
    sib_pf: ProvenancedField | None = getattr(sib_step, sib_attr, None)
    if sib_pf is None or sib_pf.extraction.status != "EXTRACTED":
        return  # sibling not extracted -> no signal -> fail closed
    sib_value = sib_pf.extraction.value
    matched = next((r for r in cond.rules if sib_value in r.when), None)
    if matched is None:
        return  # extracted sibling value matches no rule -> fail closed
    basis = DerivedBasis(source_field_ids=[cond.conditional_on], note=matched.source)
    confidence = min(matched.proposed_confidence, BASIS_CEILINGS["derived"])
    inferred: InferredDefault = InferredDefault(
        value=matched.value,
        basis=basis,
        confidence=confidence,
        alternative_inferences=[],
    )
    setattr(step, field_name, _rebuild_provenanced_field(current_pf, inference=inferred))


def _find_step(preprocessing: Preprocessing, kind: str):
    cls = _KIND_TO_CLASS.get(kind)
    if cls is None:
        return None
    for step in preprocessing.steps:
        if isinstance(step, cls):
            return step
    return None


def _rebuild_provenanced_field(current: ProvenancedField, *, inference) -> ProvenancedField:
    """Re-construct a ProvenancedField preserving its field_id + extraction
    arm and substituting a new inference arm.

    Round-trips through ``model_validate`` on the same concrete class so
    ``couple_stages`` re-runs.
    """
    payload = current.model_dump()
    payload["inference"] = inference.model_dump()
    # type(current) is type[ProvenancedField[Any]]; model_validate widens to Any.
    return cast(ProvenancedField, type(current).model_validate(payload))
