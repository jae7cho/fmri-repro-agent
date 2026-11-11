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

from collections.abc import Callable
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
from pydantic import BaseModel

from fmri_repro.spec.preprocessing import (
    IntensityNormalization,
    PipelineRef,
    Preprocessing,
    SpatialNormalization,
    SpecifiedTerm,
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

# 0.5.0: the retyped literal_type fields carry a SpecifiedTerm{verbatim, resolved, resolution}.
# A KB-inferred value for one of these is a SpecifiedTerm with verbatim=None (nothing was stated in
# the paper) and resolved=<member>; reading a sibling's value unwraps .resolved for rule matching.
_SPECIFIED_TERM_FIELDS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("spatial_normalization", "target_space"),
        ("surface_projection", "target_surface"),
        ("surface_projection", "surface_registration"),
        ("intensity_normalization", "convention"),
        ("temporal_standardization", "method"),
    }
)


def _member_of(value: object) -> object:
    """The resolved member behind a field value: unwrap a SpecifiedTerm, else the value itself."""
    return value.resolved if isinstance(value, SpecifiedTerm) else value


def _inferred_value(step_kind: str, field_name: str, member: object) -> object:
    """Wrap an inferred bare member into a SpecifiedTerm for a retyped field (verbatim=None — the
    value came from inference, nothing was stated in the paper); a non-retyped field keeps the
    bare member."""
    if (step_kind, field_name) in _SPECIFIED_TERM_FIELDS:
        return SpecifiedTerm(verbatim=None, resolved=member, resolution="resolved")
    return member


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
        # STABLE PREFIX, ruled 2026-10-19 (docs/design/DELTA_conditional_row_unverifiable.md
        # ruling 6). A bare str(exc) is free text: cobidas._gap_base splits on the first ":" and
        # so cannot extract a base, the classification in _UNVERIFIABLE_GAP_BASES cannot match it,
        # and the AST reason scan cannot enumerate it. The prefix makes all three work.
        pipeline_ref.version = _rebuild_provenanced_field(
            version_pf, inference=LeftMissing(reason=f"kb_ambiguous:{exc}")
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


def fill_dependent_defaults(
    preprocessing: Preprocessing,
    paper_date: date | None,
    skip: frozenset[tuple[str, str]] = frozenset(),
) -> Preprocessing:
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
    # 2026-11-05 (found by the third-round re-run): a version the paper states as the KB does not
    # spell it ("v1.5.3" for fMRIPrep's "1.5.3") raised KbUnknownVersionError here and failed the
    # whole paper. The version is matched as fill_deferred_defaults matches it; a version the KB
    # does not list fills nothing.
    try:
        found = _kb_versions(pipeline_id, version, field_paths)
    except KbUnknownPipelineError:
        return preprocessing
    if found is None:
        return preprocessing
    version, results = found

    for kind, name in SEVEN_DEMOTED_FIELDS:
        # ``skip`` (2026-10-29, DESIGN_report_v2.md F1a): fields a caller holds back from KB
        # defaults -- the extractor holds temporal_filtering.effective_band_hz until the KB build.
        if (kind, name) in skip:
            continue
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
    if current_pf.extraction.status in ("EXTRACTED", "VARIED"):
        return  # 0.7.0: values the paper states for parts of its data are stated too

    if isinstance(result.value, ConditionalParam):
        _apply_conditional(preprocessing, step, field_name, result.value, current_pf)
        return

    new_inference: LeftMissing | InferredDefault
    if result.value is KbNotApplicable:
        # STABLE PREFIX, ruled 2026-10-19 (ruling 6). The old reason was free text AND leaked
        # implementation prose into author-facing output: unprefixed, it matched neither render
        # table, fell through to "unspecified (reason: ...)", and printed "couple_stages forbids"
        # to the reader. The suffix keeps the pipeline and version for diagnostics; the rendered
        # sentence now comes from render._REASON_LINE["kb_not_applicable"].
        #
        # Why this travels in the gap arm at all: couple_stages permits no Missing/Deferred +
        # NotApplicable pair, so a not-applicable verdict has no slot of its own. See
        # TRACK_A_SCOPE.md A7a — a missing slot in the spec, not a defect of this function.
        new_inference = LeftMissing(reason=f"kb_not_applicable:{pipeline_id} {version}")
    else:
        basis = VersionDefaultBasis(tool=pipeline_id, version=version)
        confidence = min(result.proposed_confidence, BASIS_CEILINGS["version_default"])
        new_inference = InferredDefault(
            value=_inferred_value(step_kind, field_name, result.value),
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
    sib_value = _member_of(sib_pf.extraction.value)  # 0.5.0: unwrap SpecifiedTerm.resolved
    matched = next((r for r in cond.rules if sib_value in r.when), None)
    if matched is None:
        return  # extracted sibling value matches no rule (incl. resolved=None) -> fail closed
    basis = DerivedBasis(source_field_ids=[cond.conditional_on], note=matched.source)
    confidence = min(matched.proposed_confidence, BASIS_CEILINGS["derived"])
    inferred: InferredDefault = InferredDefault(
        value=_inferred_value(getattr(step, "kind", ""), field_name, matched.value),
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


# --- fix 3 (2026-11-05): KB defaults for fields a paper defers to its pipeline ----------------


def _step_of_kind(preprocessing: Preprocessing, kind: str) -> BaseModel | None:
    step: BaseModel | None = next(
        (s for s in preprocessing.steps if getattr(s, "kind", None) == kind), None
    )
    return step


def _typed_value(current_pf: ProvenancedField, member: object) -> object:
    """The KB member in the field's own type: a ``SpecifiedTerm`` (verbatim None -- nothing was
    stated in the paper), a list of them, or the bare value."""
    import typing

    (inner,) = type(current_pf).__pydantic_generic_metadata__["args"]
    if isinstance(inner, type) and issubclass(inner, SpecifiedTerm):
        return inner(verbatim=None, resolved=member, resolution="resolved")
    if typing.get_origin(inner) is list:
        (item,) = typing.get_args(inner)
        if isinstance(item, type) and issubclass(item, SpecifiedTerm) and isinstance(member, list):
            return [item(verbatim=None, resolved=m, resolution="resolved") for m in member]
    return member


def _kb_versions(pipeline_id: str, version: str, paths: list[str]) -> tuple[str, dict] | None:
    """The KB's param defaults at ``version``, matched exactly, then with a leading "v" removed or
    added ("v1.5.3" is fMRIPrep's 1.5.3). None when the KB lists no such version."""
    from fmri_defaults_kb.errors import KbUnknownVersionError

    tries = [version, version[1:] if version[:1] in ("v", "V") else "v" + version]
    for v in tries:
        try:
            return v, get_param_defaults(pipeline_id, v, paths)
        except KbUnknownVersionError:
            continue
    return None


def fill_deferred_defaults(
    preprocessing: Preprocessing, deferred: list[tuple[str, str]]
) -> tuple[Preprocessing, list[dict[str, object]]]:
    """Fill the INFERENCE arm of each field the paper defers to its base pipeline, from the KB's
    defaults for that pipeline at that version (DESIGN_kb_deferred_defaults.md, fix 3).

    ``deferred``: (field path, the deferral's reference string) for each field whose deferral
    target kind is ``pipeline``. A field is filled only when its extraction arm is
    ``DEFERRED_TO_CITATION``, its inference arm is ``LEFT_MISSING``, its reference names the same
    pipeline as the base pipeline, the KB documents the field at the version, and the value
    validates as the field's type. The extraction arm is never touched.

    Basis: a certain version (stated, or KB ``version_default``) gives ``VersionDefaultBasis`` (at
    most 0.95); a date-inferred version gives ``DateInferredVersionBasis`` (at most 0.75), and only
    for a value identical at the inferred version and every alternative (the motion arm's stability
    rule). The KB source is the basis note. Returns the record and one entry per field considered.
    """
    from pydantic import ValidationError

    out: list[dict[str, object]] = []
    pipeline_ref = _get_pipeline_ref(preprocessing.base_pipeline)
    pipeline_id = recognize(pipeline_ref.name) if pipeline_ref is not None else None
    if pipeline_ref is None or pipeline_id is None or not deferred:
        return preprocessing, out
    paths = [p for p, _ in deferred]
    certain = certain_version(pipeline_ref.version)
    inf = pipeline_ref.version.inference
    basis_for: Callable[[str], VersionDefaultBasis | DateInferredVersionBasis]
    if certain is not None:
        found = _kb_versions(pipeline_id, certain, paths)
        if found is None:
            return preprocessing, out
        kb_version, results = found

        def basis_for(note: str) -> VersionDefaultBasis | DateInferredVersionBasis:
            return VersionDefaultBasis(tool=pipeline_id, version=kb_version, note=note)

        ceiling = BASIS_CEILINGS["version_default"]
    elif inf.status == "INFERRED_DEFAULT" and inf.basis.basis_type == "date_inferred_version":
        versions = [str(inf.value)] + [str(a.value) for a in inf.alternative_inferences]
        per_version = [_kb_versions(pipeline_id, v, paths) for v in versions]
        if any(f is None for f in per_version):
            return preprocessing, out
        results = {}
        first = per_version[0][1]  # type: ignore[index]
        for path, r in first.items():
            if all(
                path in f[1] and f[1][path].value == r.value  # type: ignore[index]
                for f in per_version
            ):
                results[path] = r
        paper_date = inf.basis.paper_date
        inferred_version = str(inf.value)

        def basis_for(note: str) -> VersionDefaultBasis | DateInferredVersionBasis:
            return DateInferredVersionBasis(
                tool=pipeline_id,
                inferred_version=inferred_version,
                paper_date=paper_date,
                note=note,
            )

        ceiling = BASIS_CEILINGS["date_inferred_version"]
    else:
        return preprocessing, out

    for path, ref in deferred:
        kind, _, name = path.partition(".")
        entry: dict[str, object] = {"field": path, "filled": False}
        out.append(entry)
        if recognize(ref) != pipeline_id:
            entry["reason"] = "reference_names_another_pipeline"
            continue
        step = _step_of_kind(preprocessing, kind)
        current_pf = getattr(step, name, None) if step is not None else None
        if (
            step is None
            or current_pf is None
            or current_pf.extraction.status != "DEFERRED_TO_CITATION"
        ):
            entry["reason"] = "not_deferred"
            continue
        if current_pf.inference.status != "LEFT_MISSING":
            entry["reason"] = "inference_already_set"
            continue
        # fix 3 follow-up (2026-11-05): the step's FieldMeta says whether an inferred default is
        # allowed at all; setattr does not run the step's validator, so it is checked here
        meta = getattr(type(step), "ARM_REGISTRY", {}).get(name)
        if meta is None or not meta.inference_applicable:
            entry["reason"] = "inference_not_applicable"
            continue
        result = results.get(path)
        if result is None or isinstance(result.value, ConditionalParam):
            entry["reason"] = "not_in_kb"
            continue
        if result.value is KbNotApplicable:
            entry["reason"] = "kb_not_applicable"
            continue
        if not (result.source or "").strip():  # ruling 1 (2026-11-05): a sourced entry or nothing
            entry["reason"] = "kb_entry_unsourced"
            continue
        try:
            inferred = InferredDefault(
                value=_typed_value(current_pf, result.value),
                basis=basis_for(result.source),
                confidence=min(result.proposed_confidence, ceiling),
                alternative_inferences=[],
            )
            rebuilt = _rebuild_provenanced_field(current_pf, inference=inferred)
        except ValidationError:
            entry["reason"] = "value_does_not_validate"
            continue
        setattr(step, name, rebuilt)
        try:  # the whole step re-validates with the new arm, or the fill is undone
            type(step).model_validate(step.model_dump())
        except ValidationError:
            setattr(step, name, current_pf)
            entry["reason"] = "step_rejects_inference"
            continue
        entry.update(filled=True, basis_type=inferred.basis.basis_type)
    return preprocessing, out
