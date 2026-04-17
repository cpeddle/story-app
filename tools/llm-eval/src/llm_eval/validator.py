from dataclasses import dataclass, field
import json
import re

import jsonschema


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    parsed: dict | None = None


class SchemaValidator:
    """Validates JSON strings against a JSON Schema. Reusable for any schema."""

    def __init__(self, schema_path: str):
        """Load a JSON Schema from file path."""
        with open(schema_path) as f:
            self._schema = json.load(f)
        jsonschema.Draft7Validator.check_schema(self._schema)
        self._validator = jsonschema.Draft7Validator(self._schema)

    def validate(self, json_str: str) -> ValidationResult:
        """Validate a JSON string against the loaded schema.

        Handles:
        - Markdown code-fence wrappers (```json ... ```) from LLM output
        - Malformed JSON (not valid JSON at all)
        - Valid JSON but fails schema validation
        - Valid JSON that passes schema validation
        """
        json_str = self._strip_code_fences(json_str)
        try:
            parsed = json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            return ValidationResult(valid=False, errors=[f"Invalid JSON: {e}"])

        errors = []
        for error in self._validator.iter_errors(parsed):
            path = (
                " -> ".join(str(p) for p in error.absolute_path)
                if error.absolute_path
                else "(root)"
            )
            errors.append(f"{path}: {error.message}")

        if errors:
            return ValidationResult(valid=False, errors=errors, parsed=parsed)
        return ValidationResult(valid=True, parsed=parsed)

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Strip markdown code fences (```json ... ```) that LLMs often wrap around JSON."""
        if not isinstance(text, str):
            return text
        stripped = text.strip()
        # Match ```json or ``` at start, ``` at end
        match = re.match(r"^```(?:json|JSON)?\s*\n(.*?)```\s*$", stripped, re.DOTALL)
        if match:
            return match.group(1).strip()
        return stripped
