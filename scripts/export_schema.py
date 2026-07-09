"""Export the current StudySpec JSON Schema to ``schema/``.

Imports the latest versioned root (``v0_3_0``) and derives the output filename
from the model's ``schema_version``, so a future minor bump needs only an import
change here — not a hardcoded-filename edit.
"""

from __future__ import annotations

import json
from pathlib import Path

from fmri_repro.spec.v0_3_0 import StudySpec


def main() -> Path:
    schema = StudySpec.model_json_schema()
    version = StudySpec.model_fields["schema_version"].default
    out_dir = Path("schema")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"study_spec-{version}.schema.json"
    out_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(out_path)
    return out_path


if __name__ == "__main__":
    main()
