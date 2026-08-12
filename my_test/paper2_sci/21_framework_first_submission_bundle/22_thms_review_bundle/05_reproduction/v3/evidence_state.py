from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


NominalSpec = Literal["available", "unavailable"]
LinkStatus = Literal["pass", "fail", "not_evaluable"]
ExposureStatus = Literal["full", "partial", "zero", "unavailable", "not_applicable"]
ProvenanceStatus = Literal["valid", "invalid"]
MismatchDetail = Literal["none", "guard", "clock", "other"]


@dataclass(frozen=True)
class EvidenceState:
    """Machine-readable evidence state for one intervention--outcome comparison.

    The state deliberately contains no outcome value, effect direction, p value, or
    causal-identification flag. Fidelity can constrain the identity and wording of
    a comparison; it cannot by itself authorize a causal claim.
    """

    nominal_spec: NominalSpec
    n_to_c: LinkStatus
    c_to_r: LinkStatus
    exposure: ExposureStatus
    provenance: ProvenanceStatus
    n_to_c_detail: MismatchDetail = "none"


@dataclass(frozen=True)
class Decision:
    diagnostic_codes: tuple[str, ...]
    nominal_identity_status: str
    comparison_level: str
    allowed_wording: str
    prohibited_wording: str
    causal_status: str = "outside_fidelity_framework"


_VALID_VALUES = {
    "nominal_spec": {"available", "unavailable"},
    "n_to_c": {"pass", "fail", "not_evaluable"},
    "c_to_r": {"pass", "fail", "not_evaluable"},
    "exposure": {"full", "partial", "zero", "unavailable", "not_applicable"},
    "provenance": {"valid", "invalid"},
    "n_to_c_detail": {"none", "guard", "clock", "other"},
}


def _validate(state: EvidenceState) -> None:
    for field, allowed in _VALID_VALUES.items():
        value = getattr(state, field)
        if value not in allowed:
            raise ValueError(f"Invalid {field}={value!r}; expected one of {sorted(allowed)}")
    if state.nominal_spec == "unavailable" and state.n_to_c != "not_evaluable":
        raise ValueError("n_to_c must be not_evaluable when nominal_spec is unavailable")
    if state.n_to_c != "fail" and state.n_to_c_detail != "none":
        raise ValueError("n_to_c_detail is only applicable when n_to_c=fail")
    if state.c_to_r == "not_evaluable" and state.exposure not in {"unavailable", "not_applicable"}:
        raise ValueError("exposure must be unavailable/not_applicable when c_to_r is not evaluable")


def classify_evidence(state: EvidenceState) -> Decision:
    """Map evidence to diagnostic and wording boundaries without using outcomes."""

    _validate(state)
    diagnostics: list[str] = []

    if state.provenance == "invalid":
        diagnostics.append("PROVENANCE_INVALID")

    if state.nominal_spec == "unavailable":
        diagnostics.append("NOMINAL_SPEC_UNAVAILABLE")
    elif state.n_to_c == "fail":
        diagnostics.append("SPEC_IMPLEMENTATION_MISMATCH")
        if state.n_to_c_detail == "guard":
            diagnostics.append("GUARD_MISMATCH")
        elif state.n_to_c_detail == "clock":
            diagnostics.append("CLOCK_DOMAIN_MISMATCH")
    elif state.n_to_c == "not_evaluable":
        diagnostics.append("N_TO_C_NOT_EVALUABLE")

    if state.c_to_r == "fail":
        diagnostics.append("IMPLEMENTATION_REALIZATION_MISMATCH")
    elif state.c_to_r == "not_evaluable":
        diagnostics.append("REALIZATION_EVIDENCE_UNAVAILABLE")

    if state.exposure == "partial":
        diagnostics.append("PARTIAL_WINDOW_EXPOSURE")
    elif state.exposure == "zero":
        diagnostics.append("ZERO_WINDOW_EXPOSURE")
    elif state.exposure == "unavailable":
        diagnostics.append("EXPOSURE_UNAVAILABLE")

    if not diagnostics:
        diagnostics.append("NO_DETECTED_FIDELITY_BREAK")

    # Provenance is an orthogonal prerequisite and therefore has first priority
    # when deciding whether an intervention--outcome pair is evaluable.
    if state.provenance == "invalid":
        identity = "not_evaluable"
        level = "none"
        allowed = "No intervention--outcome comparison from the unverified pair."
        prohibited = "Any effect or descriptive outcome claim linking the unverified intervention and outcome."
    elif state.c_to_r == "not_evaluable" or state.exposure == "unavailable":
        identity = "not_evaluable"
        level = "implementation_only"
        allowed = "Implementation description only; realized delivery and outcome-window exposure are not evaluable."
        prohibited = "Nominal or realized intervention effect wording."
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

