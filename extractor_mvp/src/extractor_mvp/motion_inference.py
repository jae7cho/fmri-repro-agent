"""The inference arm of ``motion_correction.method`` -- the realignment tool from a documented
default (``docs/design/DESIGN_motion_inference_arm.md``; the author's rulings of 2026-10-28).

Fills the arm with the realignment PROGRAM when the extraction arm carries no tool:

* ``deferred`` with a pipeline target, or ``missing`` -> the inference arm proper (``InferredDefault``);
* ``extracted`` with the paper's own phrase (``described_only``) -> the SAME inference as a
  **diagnostic on the processed layer** (F1): the frozen provenance contract forbids an inferred
  default beside an EXTRACTED field, and the phrase is a valid extraction, so the inference travels
  in the result JSON with basis and source and renders with identical wording; the field is untouched;
* ``extracted`` with a tool-shaped value (``named_tool``) -> never.

Two bases. **P, a recognized base pipeline** (``kb/pipelines``): ``version_default`` at its ceiling
when the version is certain; ``date_inferred_version`` at 0.75 when the KB marks the program stable
across the inferred range (F3 -- the certain-version gate relaxed for this field only, on that
condition). **T, a package-attributed tool** (``kb/tools``, read from ``base_pipeline.name``):
``derived`` at 0.70 with ``source_field_ids = ["base_pipeline.name"]`` (F4). Precedence (F2): a
recognized pipeline with a certain version wins; otherwise the package basis is primary and the
pipeline default an alternative; the loser is always listed as an alternative. Never changes the
extraction arm. No model call.
"""

from __future__ import annotations

import dataclasses
from dataclasses import asdict, dataclass
from typing import Any, Literal, cast

from fmri_defaults_kb import (
    get_realignment_tool,
    realignment_program,
    realignment_tool_over,
    recognize,
    recognize_tool,
)
from fmri_defaults_kb.errors import KbError
from fmri_repro.spec.preprocessing import (
    MotionCorrection,
    MotionCorrectionMethod,
    PipelineRef,
    Preprocessing,
    SpecifiedTerm,
)
from fmri_repro.spec.provenance import (
    BASIS_CEILINGS,
    AlternativeInference,
    Basis,
    DateInferredVersionBasis,
    DerivedBasis,
    InferredDefault,
    NotApplicable,
    ProvenancedField,
    VersionDefaultBasis,
)

from extractor_mvp.motion_guard import is_tool_shaped_frozen

#: The program names the KB documents, mapped onto the spec's closed literal where a member exists.
PROGRAM_TO_MEMBER: dict[str, str] = {
    "MCFLIRT": "mcflirt",
    "Realign": "spm_realign",
    "3dvolreg": "afni_3dvolreg",
    "antsMotionCorr": "ants",
}

Path_ = Literal["arm", "diagnostic", "none", "never"]


@dataclass(frozen=True)
class MotionInferenceCandidate:
    basis_name: Literal["pipeline", "package"]
    program: str
    basis: Basis
    confidence: float
    source: str
    certain: bool  # a pipeline default at a certain version (F2's winner when present)


@dataclass(frozen=True)
class MotionInferenceRecord:
    """What the result JSON carries for both paths (F1), and what the report line reads."""

    field: str
    path: Path_
    reason: str
    program: str | None = None
    basis_name: str | None = None
    basis_type: str | None = None
    confidence: float | None = None
    source: str | None = None
    note: str | None = None
    alternatives: list[dict[str, Any]] = dataclasses.field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _base_pipeline_ref(preprocessing: Preprocessing) -> PipelineRef | None:
    bp = preprocessing.base_pipeline
    if isinstance(bp, NotApplicable):
        return None
    if bp.extraction.status == "EXTRACTED":
        return cast(PipelineRef, bp.extraction.value)
    if bp.inference.status == "INFERRED_DEFAULT":
        return cast(PipelineRef, bp.inference.value)
    return None


def _pipeline_candidate(
    pipeline_id: str, ref: PipelineRef | None
) -> MotionInferenceCandidate | None:
    """Basis P for a recognized pipeline, from its version field when there is one."""
    version_pf = ref.version if ref is not None else None
    certain_version: str | None = None
    inferred_versions: list[str] = []
    inferred_basis: DateInferredVersionBasis | None = None
    if version_pf is not None:
        if version_pf.extraction.status == "EXTRACTED":
            certain_version = str(version_pf.extraction.value)
        else:
            inf = version_pf.inference
            if inf.status == "INFERRED_DEFAULT":
                if inf.basis.basis_type == "version_default":
                    certain_version = str(inf.value)
                elif inf.basis.basis_type == "date_inferred_version":
                    inferred_basis = cast(DateInferredVersionBasis, inf.basis)
                    inferred_versions = [str(inf.value)] + [
                        str(a.value) for a in inf.alternative_inferences
                    ]
    try:
        if certain_version is not None:
            rt = get_realignment_tool(pipeline_id, certain_version)
            if rt is None:
                return None
            # the basis note carries the SOURCE verbatim: the report line reads it when no
            # record travels with the stored result, so the wording is identical either way
            basis: Basis = VersionDefaultBasis(
                tool=pipeline_id, version=certain_version, note=rt.source
            )
            return MotionInferenceCandidate(
                "pipeline", rt.program, basis, BASIS_CEILINGS["version_default"], rt.source, True
            )
        if inferred_versions and inferred_basis is not None:
            rt = realignment_tool_over(pipeline_id, inferred_versions)
            if rt is None:
                return None  # F3: not marked stable across the inferred range -> no fill
            basis = DateInferredVersionBasis(
                tool=pipeline_id,
                inferred_version=inferred_basis.inferred_version,
                paper_date=inferred_basis.paper_date,
                note=rt.source,
            )
            return MotionInferenceCandidate(
                "pipeline",
                rt.program,
                basis,
                BASIS_CEILINGS["date_inferred_version"],
                rt.source,
                False,
            )
    except KbError:
        return None  # an unlisted version, or a document without the block: no pipeline basis
    return None


def _package_candidate(name: str | None) -> MotionInferenceCandidate | None:
    """Basis T: the package the paper names for its preprocessing as a whole, from
    ``base_pipeline.name`` (the main call already extracts it), through ``kb/tools``."""
    if not name:
        return None
    tool_id = recognize_tool(name)
    if tool_id is None:
        return None
    rp = realignment_program(tool_id)
    basis = DerivedBasis(source_field_ids=["base_pipeline.name"], note=rp.source)
    return MotionInferenceCandidate(
        "package", rp.program, basis, BASIS_CEILINGS["derived"], rp.source, False
    )


def _term(program: str) -> SpecifiedTerm[MotionCorrectionMethod]:
    member = PROGRAM_TO_MEMBER.get(program)
    return SpecifiedTerm[MotionCorrectionMethod](
        verbatim=program,
        resolved=cast(Any, member),
        resolution="resolved" if member else "unrecognized",
    )


def _choose(
    pipeline: MotionInferenceCandidate | None, package: MotionInferenceCandidate | None
) -> tuple[MotionInferenceCandidate | None, list[MotionInferenceCandidate]]:
    """F2: a recognized pipeline with a certain version wins; otherwise the package basis is
    primary and the pipeline default an alternative; the loser is always listed."""
    if pipeline is not None and pipeline.certain:
        return pipeline, [c for c in (package,) if c is not None]
    if package is not None:
        return package, [c for c in (pipeline,) if c is not None]
    return pipeline, []


def infer_motion_method(
    preprocessing: Preprocessing,
) -> tuple[Preprocessing, MotionInferenceRecord]:
    """Fill the motion method's inference arm (or produce the diagnostic) and return both the
    (mutated) preprocessing and the record the result JSON and the report carry."""
    field_id = "motion_correction.method"
    step = next(
        (s for s in preprocessing.steps if getattr(s, "kind", None) == "motion_correction"), None
    )
    if step is None:
        return preprocessing, MotionInferenceRecord(field_id, "none", "no motion_correction step")
    step = cast(MotionCorrection, step)
    pf = step.method
    ext = pf.extraction
    deferral_pipeline_ref: str | None = None
    if ext.status == "EXTRACTED":
        verbatim = getattr(ext.value, "verbatim", None) or str(ext.value)
        if is_tool_shaped_frozen(verbatim):
            return preprocessing, MotionInferenceRecord(
                field_id, "never", "named_tool: the paper names the tool"
            )
        path: Path_ = "diagnostic"
    elif ext.status == "MISSING_FROM_PAPER" and str(
        getattr(pf.inference, "reason", "") or ""
    ).startswith("not_targeted_by_mvp"):
        # the per-acquisition path never made the motion call: nothing was looked for, so
        # nothing is inferred (ruling A's recorded cost stays visible as not_targeted)
        return preprocessing, MotionInferenceRecord(
            field_id, "none", "not targeted by the motion call"
        )
    elif ext.status == "DEFERRED_TO_CITATION":
        pipelines = [d for d in ext.deferrals if d.target_kind == "pipeline"]
        if not pipelines:
            return preprocessing, MotionInferenceRecord(
                field_id, "none", "deferred to a paper, not a pipeline"
            )
        deferral_pipeline_ref = pipelines[0].ref
        path = "arm"
    else:
        path = "arm"

    ref = _base_pipeline_ref(preprocessing)
    name = ref.name if ref is not None else None
    pipeline_id = recognize(name) if name else None
    if pipeline_id is None and deferral_pipeline_ref:
        pipeline_id = recognize(deferral_pipeline_ref)
        ref_for_version = ref if (ref is not None and recognize(ref.name) == pipeline_id) else None
    else:
        ref_for_version = ref
    pipeline = _pipeline_candidate(pipeline_id, ref_for_version) if pipeline_id else None
    package = _package_candidate(name)
    primary, losers = _choose(pipeline, package)
    if primary is None:
        why = "no recognized pipeline with a usable version and no listed package on base_pipeline.name"
        return preprocessing, MotionInferenceRecord(field_id, "none", why)

    alternatives = [
        {
            "program": c.program,
            "basis_name": c.basis_name,
            "basis_type": c.basis.basis_type,
            "confidence": c.confidence,
            "source": c.source,
        }
        for c in losers
    ]
    record = MotionInferenceRecord(
        field_id,
        path,
        {
            "arm": "the inference arm proper",
            "diagnostic": "described_only: a diagnostic on the processed layer (F1)",
        }[path],
        program=primary.program,
        basis_name=primary.basis_name,
        basis_type=primary.basis.basis_type,
        confidence=primary.confidence,
        source=primary.source,
        note=(
            f"{primary.basis_name} basis: "
            + (f"{pipeline_id}" if primary.basis_name == "pipeline" else f"package {name!r}")
            + f" supplies {primary.program} for realignment"
        ),
        alternatives=alternatives,
    )
    if path == "arm":
        inferred = InferredDefault[SpecifiedTerm[MotionCorrectionMethod]](
            value=_term(primary.program),
            basis=primary.basis,
            confidence=primary.confidence,
            alternative_inferences=[
                AlternativeInference[SpecifiedTerm[MotionCorrectionMethod]](
                    value=_term(c.program), basis=c.basis, confidence=c.confidence
                )
                for c in losers
            ],
        )
        step.method = ProvenancedField[SpecifiedTerm[MotionCorrectionMethod]](
            field_id=pf.field_id, extraction=pf.extraction, inference=inferred
        )
    return preprocessing, record
