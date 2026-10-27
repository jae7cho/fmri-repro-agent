"""``motion_correction.method`` as its own call (rulings A, B, C — 2026-10-19).

What these tests pin, and why each one exists:

* the motion call happens EXACTLY ONCE per paper on the single-acquisition path, and NOT AT ALL on
  the multi-acquisition path. Nothing in this suite counted ``create()`` calls before — every stub
  was ``lambda **_: payload``, which ignores ``response_model`` and so cannot tell one call from
  another. That was invisible while there was one call per paper.
* on the multi-acquisition path ``method`` carries ``not_targeted_by_mvp``, NEVER a source-absence
  reason. That path reuses the hash-pinned shared prompt, so it cannot carry this field; saying the
  paper did not report motion correction there would be a claim about the paper on the strength of a
  code path. Ruling A records the omission as a cost of the separate call.
* ``method`` only, per prereg ``:5`` and ruling B. The other nine MotionCorrection fields stay
  untargeted; bullets 2-7 arrive by amendment after the probe.
* the mapping check from the design doc's acceptance item 5.

FIXTURE NOTE, 2026-10-26: the motion payload's value used to be the resolver id ``spm_realign``.
Since the value-in-quote post-check (motion_guard.py, DELTA_value_in_quote_motion.md §4) a value
that is not in its own quote is demoted on the processed layer, and ``spm_realign`` is in no quote.
The fixtures now use the paper's own words, which the quote contains; nothing these tests pin
depends on the value's identity. The check itself is tested in test_motion_guard.py.
"""

from __future__ import annotations

from typing import Any

import pytest
from fmri_repro.spec.preprocessing import Preprocessing

from conftest import stub_client  # tests/ is on sys.path via pytest rootdir insertion
from extractor_mvp import render
from extractor_mvp.cobidas import COBIDAS_D3_ROWS, assess_coverage
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    MotionMethodExtraction,
    PreprocessingExtraction,
    extract_preprocessing,
    extract_preprocessing_for_acquisition,
)
from extractor_mvp.parsed_paper import ParsedPaper

TEXT = (
    "Methods\n"
    "Functional volumes were realigned to the mean image of each session using SPM12.\n"
    "Data were normalized to MNI152NLin6Asym at 2 mm.\n"
)


def _paper(text: str = TEXT) -> ParsedPaper:
    return ParsedPaper(text=text, source="test", parser="manual")


def _prep_payload() -> PreprocessingExtraction:
    none = FieldExtractionResult(status="missing")
    return PreprocessingExtraction(
        target_space=none,
        resolution_mm=none,
        surface_registration=none,
        target_surface=none,
        intensity_convention=none,
        intensity_value=none,
    )


def _motion(status: str, **kw: Any) -> MotionMethodExtraction:
    # version 3 (2026-10-26): an extracted payload must state its binding; these fixtures are the
    # paper's-own-words shape, so "described_only" unless a test says otherwise.
    binding = kw.pop("binding", "described_only" if status == "extracted" else None)
    return MotionMethodExtraction(
        motion_correction_method=FieldExtractionResult(status=status, **kw),
        motion_correction_binding=binding,
    )


def _method_field(prep: Preprocessing) -> Any:
    step = next(s for s in prep.steps if s.kind == "motion_correction")
    return step.method


# ---------------------------------------------------------------------------
# One call, and only on the single-acquisition path
# ---------------------------------------------------------------------------
def test_exactly_one_motion_call_per_paper_on_the_single_acquisition_path() -> None:
    counter: dict[str, int] = {}
    client = stub_client(
        _prep_payload(),
        motion=_motion(
            "extracted",
            value="realigned to the mean image of each session",
            verbatim_quote="realigned to the mean image of each session using SPM12",
        ),
        counter=counter,
    )
    extract_preprocessing(_paper(), "m", client=client)
    assert counter == {"PreprocessingExtraction": 1, "MotionMethodExtraction": 1}, counter


def test_both_calls_are_made_with_the_same_sampling_settings() -> None:
    """A separate call is only comparable to the main one if it is made the SAME way.

    ``extractor.py:1199-1200`` (motion) and ``:1246-1247`` (main) both pass ``temperature=0.0`` and
    ``max_retries=2``. Nothing asserted it: the response model is checked by dispatch, but
    temperature is a keyword no test reads, so the motion call could have been given a different
    value -- or none, inheriting whatever the provider defaults to -- and every other test would
    still pass. The probe's whole premise is non-determinism AT TEMPERATURE 0 (``variance.md``), so
    a motion call sampling at a provider default would measure a different quantity than the one
    pre-registered, and the draws would look like instability.

    The absent case is distinguished from an explicit 0.0 by a sentinel, because ``kwargs.get(
    "temperature", 0.0)`` would make a removed argument pass.
    """
    calls: list[dict] = []
    extract_preprocessing(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            motion=_motion(
                "extracted",
                value="realigned to the mean image of each session",
                verbatim_quote="realigned to the mean image of each session using SPM12",
            ),
            calls=calls,
        ),
    )
    assert [c["response_model"] for c in calls] == [
        "MotionMethodExtraction",
        "PreprocessingExtraction",
    ], calls
    for c in calls:
        assert c["temperature"] == 0.0, f"{c['response_model']}: temperature={c['temperature']!r}"
        assert c["max_retries"] == 2, f"{c['response_model']}: max_retries={c['max_retries']!r}"
        assert c["model"] == "m", c
    # and both are floats, not ints: a 0 would also == 0.0 but is a different literal in the source
    assert all(isinstance(c["temperature"], float) for c in calls), calls


def test_the_multi_acquisition_path_makes_no_motion_call() -> None:
    """Ruling A's recorded cost, asserted rather than trusted.

    ``PER_ACQUISITION_EXTRACTION_PROMPT`` is ``prefix + EXTRACTION_PROMPT``, so the per-acquisition
    path reuses the pinned shared prompt and cannot carry a motion field. If a motion call were
    ever routed through that path it would also break the multi-acquisition stub, which pops one
    payload per acquisition.
    """
    counter: dict[str, int] = {}
    client = stub_client(_prep_payload(), counter=counter)
    extract_preprocessing_for_acquisition(_paper(), "hcp", "the HCP sample", "m", client=client)
    assert "MotionMethodExtraction" not in counter, counter
    assert counter == {"PreprocessingExtraction": 1}, counter


def test_on_the_multi_acquisition_path_method_is_untargeted_never_not_stated() -> None:
    prep, _, _ = extract_preprocessing_for_acquisition(
        _paper(), "hcp", "the HCP sample", "m", client=stub_client(_prep_payload())
    )
    field = _method_field(prep)
    assert field.extraction.status == "MISSING_FROM_PAPER"
    assert field.inference.reason == "not_targeted_by_mvp"
    # the distinction this test exists for: a source-absence reason would be a claim about the paper
    assert field.inference.reason != "not_stated_in_text"


# ---------------------------------------------------------------------------
# Ruling B — method only
# ---------------------------------------------------------------------------
def test_only_method_is_targeted_the_other_nine_fields_are_not() -> None:
    prep, _, _ = extract_preprocessing(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            motion=_motion(
                "extracted",
                value="realigned to the mean image of each session",
                verbatim_quote="realigned to the mean image of each session using SPM12",
            ),
        ),
    )
    step = next(s for s in prep.steps if s.kind == "motion_correction")
    targeted = [
        n
        for n in type(step).model_fields
        if n != "kind"
        and getattr(getattr(step, n).inference, "reason", None) != "not_targeted_by_mvp"
    ]
    assert targeted == ["method"], targeted


# ---------------------------------------------------------------------------
# The standard gap reasons, so the conditional-row rule handles them unchanged
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("payload", "expect_reason"),
    [
        (_motion("missing"), "not_stated_in_text"),
        (
            _motion(
                "extracted",
                value="realigned to the mean image of each session",
                verbatim_quote="nowhere in the text",
            ),
            "extraction_quote_unresolved:quote_not_found",
        ),
    ],
    ids=["absent", "dropped_quote"],
)
def test_motion_gap_reasons_are_the_standard_ones(payload: Any, expect_reason: str) -> None:
    """The motion call reuses ``_process_field``, so it cannot invent a private reason vocabulary
    that the conditional-row rule would not recognise."""
    prep, _, _ = extract_preprocessing(
        _paper(), "m", client=stub_client(_prep_payload(), motion=payload)
    )
    assert _method_field(prep).inference.reason == expect_reason


# ---------------------------------------------------------------------------
# The mapping check — design doc acceptance item 5
# ---------------------------------------------------------------------------
def test_motion_maps_to_exactly_one_cobidas_row() -> None:
    rows = [r for r in COBIDAS_D3_ROWS if "motion_correction" in r.spec_kinds]
    assert [r.row_id for r in rows] == ["motion_correction"]
    assert rows[0].spec_kinds == ("motion_correction",)
    # no other row shares the kind, and none mentions motion at all
    assert not [r for r in COBIDAS_D3_ROWS if "motion" in str(r.spec_kinds) and r is not rows[0]]


def test_a_method_only_run_credits_only_the_motion_row() -> None:
    prep, _, _ = extract_preprocessing(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            motion=_motion(
                "extracted",
                value="realigned to the mean image of each session",
                verbatim_quote="realigned to the mean image of each session using SPM12",
            ),
        ),
    )
    by_id = {rc.row.row_id: rc for rc in assess_coverage(render.flatten(prep), None)}
    assert by_id["motion_correction"].addressed is True
    # every OTHER row stays unaddressed: the motion call credits nothing else
    assert [r for r, rc in by_id.items() if rc.addressed and r != "motion_correction"] == []


def test_a_dropped_method_quote_renders_the_motion_row_unverifiable() -> None:
    """The reason ruling C ordered the conditional-row DELTA first. Without it this row would read
    as "the paper did not report motion correction" when only the quote failed to resolve."""
    prep, _, _ = extract_preprocessing(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            motion=_motion(
                "extracted",
                value="realigned to the mean image of each session",
                verbatim_quote="nowhere in the text",
            ),
        ),
    )
    rc = {c.row.row_id: c for c in assess_coverage(render.flatten(prep), None)}["motion_correction"]
    assert (rc.addressed, rc.covered_by_extractor, rc.unverifiable) == (False, False, True)
    out = render.to_cobidas_coverage(prep)
    assert "- Motion correction  (examined; the extractor could not verify what it found)" in out
    assert "- Motion correction  (no fields assessed by current extractor)" not in out


# ---------------------------------------------------------------------------
# The bare-id collision, in the direction that is easy to miss
# ---------------------------------------------------------------------------
def test_a_temporal_synonym_cannot_resolve_a_motion_value() -> None:
    """``method`` is the bare field_id of TWO fields now.

    The forward direction is obvious: adding "method" to a bare-id map for motion would also hit
    ``temporal_standardization.method``. The REVERSE is the one that is easy to miss -- a synonym
    written for temporal would silently resolve motion values, because both fields pass the same
    bare id into ``SYNONYMS_BY_FIELD.get(field_id)``. Nothing prevented that except "method" not
    being a key, which is a fact about the map's contents, not about the code.

    This drives the REAL path -- ``extract_preprocessing`` -> ``extract_motion_method`` -> its
    ``use_synonym_table=False`` -- because a first version of this test called ``_process_field``
    directly with the flag and so passed even with the production opt-out deleted. A guard that
    cannot fail is worthless; mutation-checked by removing that argument.
    """
    import extractor_mvp.synonym_resolver as synonym_resolver
    from extractor_mvp.extractor import _FIELD_SPECS, _MOTION_FIELD_SPEC

    _attr, m_field, _d, _l, _t = _MOTION_FIELD_SPEC
    temporal = next(s for s in _FIELD_SPECS if s[2] == "temporal_standardization.method")
    assert m_field == temporal[1] == "method", "the collision this test is about has gone away"
    assert synonym_resolver.SYNONYMS_BY_FIELD.get("method") is None, (
        "'method' now HAS a synonym entry. Decide which field it is for and key the map on "
        "(step kind, field); until then one entry would serve both fields."
    )

    text = "Methods\nFunctional volumes were zscored across time.\n"
    payload = _prep_payload()
    payload.temporal_standardization_method = FieldExtractionResult(
        status="extracted", value="zscored", verbatim_quote="zscored across time"
    )
    motion = _motion("extracted", value="zscored", verbatim_quote="zscored across time")

    synonym_resolver.SYNONYMS_BY_FIELD["method"] = (
        {"voxel_temporal_zscore": ["zscored"]},
        set(),
    )
    try:
        prep, _, _ = extract_preprocessing(
            _paper(text), "m", client=stub_client(payload, motion=motion)
        )
    finally:
        del synonym_resolver.SYNONYMS_BY_FIELD["method"]

    temporal_field = next(s for s in prep.steps if s.kind == "temporal_standardization").method
    motion_field = _method_field(prep)

    # positive control: the injection WAS live, and the temporal field resolved through it
    assert temporal_field.extraction.value.resolved == "voxel_temporal_zscore"
    # and the motion field, passing the same bare id, did not
    assert motion_field.extraction.value.resolved is None
    assert motion_field.extraction.value.resolution == "unrecognized"
    assert motion_field.extraction.value.verbatim == "zscored"


def test_no_bare_id_map_may_key_on_an_id_shared_by_two_targeted_fields() -> None:
    """Structural guard. Motion's opt-out fixes ONE caller; this covers every future one.

    Every step kind in the spec has a field called ``method``, so each new row built as its own
    call hits the same collision motion just hit: two targeted fields passing the same bare
    ``field_id`` into a map keyed on bare ids. Today ``method`` is shared by
    ``temporal_standardization.method`` and ``motion_correction.method`` and neither map holds it,
    so both lookups are inert — a fact about the maps' CONTENTS, which this test converts into a
    checked property.

    It fails the day someone adds ``"method"`` to a bare-id map while two targeted ``method``
    fields exist. The failure is the point: it forces the re-keying decision at the moment it
    becomes load-bearing, instead of after a temporal synonym has silently resolved a motion value.

    Scope: the two bare-id-keyed lookups in the extraction path. ``SYNONYMS_BY_FIELD`` is a real
    dict; the ``value_context`` guard is a literal ``field_id == "convention"`` comparison, so its
    key set is modelled as the one-element set it is.
    """
    from extractor_mvp.extractor import _FIELD_SPECS, _MOTION_FIELD_SPEC
    from extractor_mvp.synonym_resolver import SYNONYMS_BY_FIELD

    # every targeted field, by (dotted path, bare id) — the shared call's fields plus motion's
    targeted = [(spec[2], spec[1]) for spec in (*_FIELD_SPECS, _MOTION_FIELD_SPEC)]
    shared: dict[str, list[str]] = {}
    for dotted, bare in targeted:
        shared.setdefault(bare, []).append(dotted)
    ambiguous = {bare: paths for bare, paths in shared.items() if len(paths) > 1}

    # positive control: the collision this guard exists for is REAL and currently present
    assert "method" in ambiguous, (
        "no bare id is shared by two targeted fields any more, so this guard is vacuous — "
        f"re-derive it or delete it. shared ids: {sorted(shared)}"
    )
    assert sorted(ambiguous["method"]) == [
        "motion_correction.method",
        "temporal_standardization.method",
    ], ambiguous["method"]

    bare_id_keyed = {
        "SYNONYMS_BY_FIELD": set(SYNONYMS_BY_FIELD),
        # extractor.py's value_context guard: `intensity_value_ctx if field_id == "convention"`
        "value_context guard": {"convention"},
    }
    for map_name, keys in bare_id_keyed.items():
        collisions = sorted(keys & set(ambiguous))
        assert not collisions, (
            f"{map_name} keys on {collisions}, which {len(ambiguous[collisions[0]])} targeted "
            f"fields share: {sorted(ambiguous[collisions[0]])}. A bare-id map cannot distinguish "
            "them, so one entry serves both and the second field silently inherits the first's "
            "behaviour. Either re-key this map on (step kind, field), or have the affected "
            "caller opt out explicitly the way extract_motion_method does."
        )


# ---------------------------------------------------------------------------
# Option (c), 2026-10-26 — the model states the binding; the schema enforces when
# ---------------------------------------------------------------------------
def test_binding_is_required_when_extracted_and_forbidden_otherwise() -> None:
    """Amendment 7: ``motion_correction_binding`` is set ONLY on an extracted draw, and then always.
    A violation is a validation error -- under instructor, a reask the probe counts -- never a
    silent default that would make the heuristic's control vacuous."""
    import pytest

    # version 6 (protocol v1.8, 2026-10-26): named_tool carries its attribution level in the literal.
    for binding in ("named_tool_step", "named_tool_package", "described_only"):
        ok = MotionMethodExtraction(
            motion_correction_method=FieldExtractionResult(
                status="extracted", value="realigned", verbatim_quote="volumes were realigned"
            ),
            motion_correction_binding=binding,
        )
        assert ok.motion_correction_binding == binding
    with pytest.raises(ValueError, match="named_tool"):  # the pre-v6 literal is refused
        MotionMethodExtraction(
            motion_correction_method=FieldExtractionResult(
                status="extracted", value="realigned", verbatim_quote="volumes were realigned"
            ),
            motion_correction_binding="named_tool",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="requires motion_correction_binding"):
        MotionMethodExtraction(
            motion_correction_method=FieldExtractionResult(
                status="extracted", value="realigned", verbatim_quote="volumes were realigned"
            )
        )
    for status, kw in (
        ("missing", {}),
        ("deferred", {"deferral_sentence": "as described in ref", "ref_string": "ref"}),
    ):
        with pytest.raises(ValueError, match="set only when status='extracted'"):
            MotionMethodExtraction(
                motion_correction_method=FieldExtractionResult(status=status, **kw),
                motion_correction_binding="described_only",
            )
        # and the status path itself is untouched: no binding is fine
        MotionMethodExtraction(motion_correction_method=FieldExtractionResult(status=status, **kw))


def test_raw_out_carries_the_binding_beside_the_field_result() -> None:
    from extractor_mvp.extractor import extract_motion_method

    raw_out: list[MotionMethodExtraction] = []
    extract_motion_method(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            motion=_motion(
                "extracted",
                value="realigned to the mean image of each session",
                verbatim_quote="realigned to the mean image of each session using SPM12",
                binding="described_only",
            ),
        ),
        raw_out=raw_out,
    )
    assert raw_out[0].motion_correction_binding == "described_only"
    assert raw_out[0].motion_correction_method.status == "extracted"
