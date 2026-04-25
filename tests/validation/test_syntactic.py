"""Tests for masm.validation.syntactic."""

from masm.validation.base import ValidationContext
from masm.validation.syntactic import SyntacticValidator


def test_syntactic_validator_accepts_valid_json_payload():
    """Valid JSON should parse cleanly."""
    validator = SyntacticValidator()

    result = validator.validate(
        '{"id":"obj-1","object_type":"generic"}',
        ValidationContext(),
    )

    assert result.valid is True
    assert result.metadata["parsed_format"] == "json"


def test_syntactic_validator_accepts_valid_yaml_payload():
    """Valid YAML should parse cleanly when requested."""
    validator = SyntacticValidator()
    context = ValidationContext(metadata={"format": "yaml"})

    result = validator.validate(
        "id: obj-1\nobject_type: generic\n", context
    )

    assert result.valid is True
    assert result.metadata["parsed_format"] == "yaml"


def test_syntactic_validator_rejects_invalid_json_payload():
    """Invalid JSON must produce a syntactic error."""
    validator = SyntacticValidator()
    context = ValidationContext(metadata={"format": "json"})

    result = validator.validate('{"id": "obj-1",}', context)

    assert result.valid is False
    assert result.summary["error"] == 1
    assert result.errors[0].code == "SYN-PARSE-FAILED"


def test_syntactic_validator_rejects_unsupported_input_type():
    """Unsupported input types should return structured syntactic issues."""
    validator = SyntacticValidator()

    result = validator.validate(42, ValidationContext())

    assert result.valid is False
    assert result.errors[0].code == "SYN-UNSUPPORTED-INPUT"
