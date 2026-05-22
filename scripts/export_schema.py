"""Export the v0.1.0 StudySpec JSON Schema to ``schema/``."""

from __future__ import annotations

import json
from pathlib import Path

from fmri_repro.spec.v0_1_0 import StudySpec


def main() -> Path:
    schema = StudySpec.model_json_schema()
    out_dir = Path("schema")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "study_spec-0.1.0.schema.json"
    out_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(out_path)
    return out_path


if __name__ == "__main__":
    main()
