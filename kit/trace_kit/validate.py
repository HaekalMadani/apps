"""Python-side validation of TRACE data files against schemas/*.schema.json.

This is the Python half of the validation-parity pair (the Lua half is
lua/trace_rt/lib/validate.lua). The shared fixture corpus in configs/ keeps the
two in agreement; see kit/tests/test_m0_roundtrip.py.
"""

import json
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schemas"

# format name -> schema file. The first three are the runtime inputs and are
# also validated in Lua; the rest are output formats (validated offline only).
FORMATS = {
    "controller_config": "controller_config.schema.json",
    "annotation": "annotation.schema.json",
    "reference": "reference.schema.json",
    "session_manifest": "session_manifest.schema.json",
    "ticks_columns": "ticks_columns.schema.json",
    "passes": "passes.schema.json",
    "fades": "fades.schema.json",
}

# Formats whose validator also exists in lua/trace_rt/lib/validate.lua.
RUNTIME_INPUT_FORMATS = ("controller_config", "annotation", "reference")


def load_schema(format_name):
    """Load and return the JSON Schema for a named format."""
    path = SCHEMA_DIR / FORMATS[format_name]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_data(format_name, data):
    """Validate a decoded document. Returns a list of error strings (empty = valid)."""
    validator = jsonschema.Draft7Validator(load_schema(format_name))
    return [
        "{}: {}".format("/".join(str(p) for p in e.absolute_path) or "<root>", e.message)
        for e in validator.iter_errors(data)
    ]


def validate_file(path, format_name):
    """Validate a JSON file. Returns a list of error strings (empty = valid)."""
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            return ["JSON parse error: {}".format(e)]
    return validate_data(format_name, data)
