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
    "golden_trace": "golden_trace.schema.json",
    "instrument": "instrument.schema.json",
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


# --- CLI --------------------------------------------------------------------
#
# Added at M6 for one specific moment: an instrument file is hand-written during
# a session, and the cheapest time to learn it is malformed is before the
# participant stands up — not at the integrity check afterwards, and certainly
# not at analysis. The format is guessed from the filename prefix so the common
# case is `python -m trace_kit.validate <file>` with nothing to remember.

# Filename prefix -> format, for the files that are written by hand or by the
# runtime rather than being configs.
_PREFIX_FORMATS = (
    ("instrument_", "instrument"),
    ("manifest_", "session_manifest"),
    ("annotation_", "annotation"),
    ("reference_", "reference"),
    ("controller_config", "controller_config"),
)


def guess_format(path):
    """Format name from a filename prefix, or None if it is not recognisable."""
    name = Path(path).name
    for prefix, format_name in _PREFIX_FORMATS:
        if name.startswith(prefix):
            return format_name
    return None


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog="trace_kit.validate",
        description="Validate a JSON file against its TRACE schema. The format is "
                    "guessed from the filename (instrument_*, manifest_*, "
                    "annotation_*, reference_*, controller_config*) unless --format "
                    "is given.")
    parser.add_argument("files", nargs="+", help="file(s) to validate")
    parser.add_argument("--format", choices=sorted(FORMATS),
                        help="force a format instead of guessing from the filename")
    args = parser.parse_args(argv)

    failed = False
    for path in args.files:
        format_name = args.format or guess_format(path)
        if format_name is None:
            print("[SKIP] {}: cannot tell which format this is -- pass --format".format(path))
            failed = True
            continue
        errors = validate_file(path, format_name)
        print("[{}] {}  ({})".format("PASS" if not errors else "FAIL",
                                     Path(path).name, format_name))
        for error in errors:
            print("    - {}".format(error))
        if errors:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
