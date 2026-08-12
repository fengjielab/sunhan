from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


NominalSpec = Literal["available", "unavailable"]
LinkStatus = Literal["pass", "fail", "not_evaluable"]
ExposureStatus = Literal["full", "partial", "zero", "unavailable", "not_applicable"]
ProvenanceStatus = Literal["valid", "invalid"]
ExtractionMode = Literal["automatic", "structured_author_audit"]
MismatchDetail = Literal["guard", "clock", "parameter", "update", "other"]

FLOAT_TOL = 1e-12


@dataclass(frozen=True)
class EvidenceItem:
    """One auditable artifact-to-state observation.

    Outcome values, effect directions, p values, and significance fields are
    intentionally absent.  ``outcome_window`` is an alignment definition, not an
    observed human outcome.
    """

    state_field: Literal["nominal_spec", "n_to_c", "c_to_r", "exposure", "provenance"]
    artifact_path: str
    artifact_sha256: str
    collection_code_commit: str
    rule_id: str
    extraction_mode: ExtractionMode
    observed_value: str
    unit: str
    tolerance: str
    missing: bool
    rationale: str


@dataclass(frozen=True)
class ArtifactEvidence:
    """Normalized raw-artifact evidence for one intervention/window unit.

    Configuration-level specification/source audits can be joined to trial-level
    replay, exposure, and provenance observations before this object is created.
    The object records facts needed to derive an EvidenceState; it does not accept
    a pre-assigned state.
    """

    evidence_unit_id: str
    configuration: str
    trial_id: str
    outcome_window: str
    nominal_label_present: bool
    nominal_artifact_present: bool
    nominal_artifact_contemporaneous: bool
    nominal_elements_explicit: bool
    implementation_artifact_present: bool
    n_to_c_checks_complete: bool
    n_to_c_mismatch_details: tuple[MismatchDetail, ...] = ()
    replay_supported: bool = False
    replay_complete: bool = False
    replay_mismatch: bool = False
    exposure_applicable: bool = True
    exposure_trace_complete: bool = False
    exposure_fraction: float | None = None
    provenance_checks_complete: bool = False
    provenance_exact_match: bool = False
    items: tuple[EvidenceItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EvidenceState:
    nominal_spec: NominalSpec
    n_to_c: LinkStatus
    c_to_r: LinkStatus
    exposure: ExposureStatus
    provenance: ProvenanceStatus
    n_to_c_details: tuple[MismatchDetail, ...] = ()


@dataclass(frozen=True)
class Decision:
    diagnostic_codes: tuple[str, ...]
    nominal_identity_status: str
    comparison_level: str
    allowed_wording: str
    prohibited_wording: str
    causal_status: str = "outside_fidelity_framework"


def _ordered_unique(values: tuple[MismatchDetail, ...]) -> tuple[MismatchDetail, ...]:
    order = ("guard", "clock", "parameter", "update", "other")
    return tuple(item for item in order if item in values)


def derive_evidence_state(evidence: ArtifactEvidence) -> EvidenceState:
    """Stage A: deterministically map normalized artifacts to evidence state."""

    nominal_available = (
        evidence.nominal_artifact_present
        and evidence.nominal_artifact_contemporaneous
        and evidence.nominal_elements_explicit
    )
    nominal_spec: NominalSpec = "available" if nominal_available else "unavailable"

    details = _ordered_unique(evidence.n_to_c_mismatch_details)
    if not nominal_available:
        n_to_c: LinkStatus = "not_evaluable"
        details = ()
    elif details:
        n_to_c = "fail"
    elif evidence.implementation_artifact_present and evidence.n_to_c_checks_complete:
        n_to_c = "pass"
    else:
        n_to_c = "not_evaluable"

    if evidence.replay_mismatch:
        c_to_r: LinkStatus = "fail"
    elif evidence.replay_supported and evidence.replay_complete:
        c_to_r = "pass"
    else:
        c_to_r = "not_evaluable"

    if not evidence.exposure_applicable:
        exposure: ExposureStatus = "not_applicable"
    elif not evidence.exposure_trace_complete or evidence.exposure_fraction is None:
        exposure = "unavailable"
    else:
        phi = float(evidence.exposure_fraction)
        if phi < -FLOAT_TOL or phi > 1.0 + FLOAT_TOL:
            raise ValueError(f"exposure_fraction must lie in [0, 1], got {phi}")
        if phi <= FLOAT_TOL:
            exposure = "zero"
        elif phi >= 1.0 - FLOAT_TOL:
            exposure = "full"
        else:
            exposure = "partial"

    provenance: ProvenanceStatus = (
        "valid"
        if evidence.provenance_checks_complete and evidence.provenance_exact_match
        else "invalid"
    )
    return EvidenceState(
        nominal_spec=nominal_spec,
        n_to_c=n_to_c,
        c_to_r=c_to_r,
        exposure=exposure,
        provenance=provenance,
        n_to_c_details=details,
    )


def classify_evidence(state: EvidenceState) -> Decision:
    """Stage B: map evidence state to cumulative inference constraints."""

    diagnostics: list[str] = []
    if state.provenance == "invalid":
        diagnostics.append("PROVENANCE_INVALID")
    if state.nominal_spec == "unavailable":
        diagnostics.append("NOMINAL_SPEC_UNAVAILABLE")
    elif state.n_to_c == "fail":
        diagnostics.append("SPEC_IMPLEMENTATION_MISMATCH")
        detail_codes = {
            "guard": "GUARD_MISMATCH",
            "clock": "CLOCK_DOMAIN_MISMATCH",
            "parameter": "PARAMETER_MISMATCH",
            "update": "UPDATE_RULE_MISMATCH",
            "other": "OTHER_N_TO_C_MISMATCH",
        }
        diagnostics.extend(detail_codes[item] for item in state.n_to_c_details)
    elif state.n_to_c == "not_evaluable":
        diagnostics.append("N_TO_C_NOT_EVALUABLE")
    if state.c_to_r == "fail":
        diagnostics.append("IMPLEMENTATION_REALIZATION_MISMATCH")
    elif state.c_to_r == "not_evaluable":
        diagnostics.append("C_TO_R_NOT_EVALUABLE")
    if state.exposure == "partial":
        diagnostics.append("PARTIAL_WINDOW_EXPOSURE")
    elif state.exposure == "zero":
        diagnostics.append("ZERO_WINDOW_EXPOSURE")
    elif state.exposure == "unavailable":
        diagnostics.append("EXPOSURE_UNAVAILABLE")
    if not diagnostics:
        diagnostics.append("NO_DETECTED_FIDELITY_BREAK")

    exposure_known = state.exposure in {"full", "partial", "zero", "not_applicable"}
    if state.provenance == "invalid":
        identity = "not_evaluable"
        level = "none"
        allowed = "No intervention--outcome comparison from the unverified pair."
        prohibited = "Any effect or descriptive outcome claim linking the unverified intervention and outcome."
    elif state.c_to_r == "not_evaluable" and not exposure_known:
        identity = "not_evaluable"
        level = "implementation_only"
        allowed = "Implementation description only; realized delivery and exposure are unavailable."
        prohibited = "Nominal or realized intervention effect wording."
    elif state.c_to_r == "not_evaluable" and exposure_known:
        identity = "unsupported" if state.n_to_c == "fail" else "not_evaluable"
        level = "recorded_realized_configuration"
        allowed = "Description of the recorded trajectory and exposure, with C-to-R replay explicitly unevaluated."
        prohibited = "Claims that the executable logic was faithfully realized or that the nominal intervention was delivered."
    elif state.nominal_spec == "unavailable" or state.n_to_c == "not_evaluable":
        identity = "indeterminate"
        level = "realized_configuration"
        allowed = "Descriptive comparison of the recoverable realized configuration and exposure distribution."
        prohibited = "An effect attributed to an unrecovered nominal intervention."
    elif state.n_to_c == "fail":
        identity = "unsupported"
        level = "implemented_or_realized_configuration"
        allowed = "Descriptive comparison of the implemented/realized configuration with the mismatch disclosed."
        prohibited = "The nominal intervention effect or correctly implemented policy effect."
    elif state.c_to_r == "fail":
        identity = "unsupported"
        level = "realized_delivery"
        allowed = "Descriptive comparison of the recorded realized delivery state."
        prohibited = "The executable or nominal intervention effect."
    elif state.exposure == "zero":
        identity = "unsupported"
        level = "assignment_with_zero_window_exposure"
        allowed = "Assignment-level description stating that nominal window exposure was absent."
        prohibited = "An outcome-window effect of an intervention with zero recorded exposure."
    elif state.exposure == "partial":
        identity = "exposure_qualified"
        level = "assignment_with_exposure_distribution"
        allowed = "Assignment-level description qualified by the realized partial-exposure distribution."
        prohibited = "A uniform full-exposure intervention effect."
    else:
        identity = "retained"
        level = "nominal_identity_retained"
        allowed = "The nominal intervention identity may be retained, subject to separate design and measurement checks."
        prohibited = "A causal effect claim based on fidelity evidence alone."

    return Decision(
        diagnostic_codes=tuple(diagnostics),
        nominal_identity_status=identity,
        comparison_level=level,
        allowed_wording=allowed,
        prohibited_wording=prohibited,
    )
