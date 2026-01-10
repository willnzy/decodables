"""
Core Schemas - JSON Schema definitions for data validation.

@module core.schemas
@version 1.0.0
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

try:
    import jsonschema
    from jsonschema import Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


# Schema directory
SCHEMA_DIR = Path(__file__).parent


@lru_cache(maxsize=10)
def load_schema(schema_name: str) -> Dict[str, Any]:
    """
    Load JSON Schema from file.

    Args:
        schema_name: Schema file name (without extension)

    Returns:
        Dict containing JSON Schema

    Raises:
        FileNotFoundError: If schema file not found
        json.JSONDecodeError: If schema file is invalid JSON
    """
    schema_path = SCHEMA_DIR / f"{schema_name}.json"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_with_schema(
    data: Any,
    schema_name: str,
    raise_on_error: bool = False
) -> tuple[bool, Optional[str]]:
    """
    Validate data against JSON Schema.

    Args:
        data: Data to validate
        schema_name: Schema file name (without .json extension)
        raise_on_error: If True, raise ValidationError on failure

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> is_valid, error = validate_with_schema(canvas_data, "canvas_data_schema")
        >>> if not is_valid:
        ...     print(f"Validation failed: {error}")
    """
    if not JSONSCHEMA_AVAILABLE:
        # Graceful degradation: if jsonschema not installed, skip validation
        return True, None

    try:
        schema = load_schema(schema_name)
    except FileNotFoundError as e:
        return False, f"Schema not found: {e}"
    except json.JSONDecodeError as e:
        return False, f"Invalid schema file: {e}"

    try:
        # Create validator
        validator = Draft7Validator(schema)

        # Validate
        errors = list(validator.iter_errors(data))

        if errors:
            # Format first error for readability
            error = errors[0]
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            message = f"Validation error at {path}: {error.message}"

            if raise_on_error:
                raise jsonschema.ValidationError(message)

            return False, message

        return True, None

    except jsonschema.ValidationError as e:
        if raise_on_error:
            raise
        return False, str(e)
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def validate_canvas_data_schema(
    canvas_data: Optional[Dict[str, Any]],
    raise_on_error: bool = False
) -> tuple[bool, Optional[str]]:
    """
    Validate canvas_data against Canvas Data JSON Schema.

    This is a convenience wrapper around validate_with_schema for canvas_data.

    Args:
        canvas_data: Canvas data dict to validate
        raise_on_error: If True, raise ValidationError on failure

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> canvas = {"version": "5.3.0", "objects": []}
        >>> is_valid, error = validate_canvas_data_schema(canvas)
        >>> if not is_valid:
        ...     raise HTTPException(400, f"Invalid canvas data: {error}")
    """
    if canvas_data is None:
        return True, None

    if not isinstance(canvas_data, dict):
        return False, "canvas_data must be a dictionary"

    return validate_with_schema(canvas_data, "canvas_data_schema", raise_on_error)


__all__ = [
    "load_schema",
    "validate_with_schema",
    "validate_canvas_data_schema",
    "JSONSCHEMA_AVAILABLE",
]
