"""Execution boundary for the initial software/provenance review."""


def deferred(stage):
    raise SystemExit(
        f"BLOCKED: {stage} belongs to Gate 3 or later. This release implements Gates 0–2 only. "
        "Resolve data provenance and obtain scientific review before implementing/running experiments."
    )
