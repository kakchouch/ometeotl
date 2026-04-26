"""Tests for ometeotl_core.validation.epistemic."""

from ometeotl_core.validation.base import ValidationContext
from ometeotl_core.validation.epistemic import EpistemicValidator


def test_epistemic_validator_accepts_valid_statuses():
    """Known statuses should pass epistemic validation."""
    payload = {
        "perceived_spaces": [
            {"epistemic_status": "certain"},
            {"epistemic_status": "projected"},
        ]
    }

    result = EpistemicValidator().validate(
        payload, ValidationContext()
    )

    assert result.valid is True


def test_epistemic_validator_rejects_invalid_status():
    """Unknown epistemic statuses should produce errors."""
    payload = {"epistemic_status": "omniscient"}

    result = EpistemicValidator().validate(
        payload, ValidationContext()
    )

    assert result.valid is False
    assert result.errors[0].code == "EPI-INVALID-STATUS"
