"""Export JSON schemas from versioned Pydantic v2 contracts (API-001)."""

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel

from app.contracts import (
    ASRResult,
    AssessmentResult,
    ChildProgressDTO,
    DeviceCommand,
    DeviceEnvelope,
    DeviceEvent,
    ErrorResponse,
    LearningEvidence,
    ResponsePlan,
    TTSResult,
    VisionObservation,
)

EXPORTED_CONTRACTS: dict[str, type[BaseModel]] = {
    "device_envelope": DeviceEnvelope,
    "device_command": DeviceCommand,
    "device_event": DeviceEvent,
    "asr_result": ASRResult,
    "assessment_result": AssessmentResult,
    "response_plan": ResponsePlan,
    "tts_result": TTSResult,
    "vision_observation": VisionObservation,
    "learning_evidence": LearningEvidence,
    "child_progress_dto": ChildProgressDTO,
    "error_response": ErrorResponse,
}


def export_schemas(output_dir: Path | None = None) -> list[Path]:
    target_dir = output_dir or (Path(__file__).parent.parent / "schemas")
    target_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for name, model_cls in EXPORTED_CONTRACTS.items():
        schema_path = target_dir / f"{name}.json"
        schema_data = model_cls.model_json_schema()
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        written.append(schema_path)
        print(f"Exported schema: {schema_path.name}")

    return written


def check_schemas(target_dir: Path | None = None) -> bool:
    """Verify that on-disk JSON schemas match current Pydantic models (drift check)."""
    schema_dir = target_dir or (Path(__file__).parent.parent / "schemas")
    all_match = True

    for name, model_cls in EXPORTED_CONTRACTS.items():
        schema_path = schema_dir / f"{name}.json"
        if not schema_path.exists():
            print(f"MISSING schema file: {schema_path.name}")
            all_match = False
            continue

        with open(schema_path, encoding="utf-8") as f:
            existing_data = json.load(f)

        current_data = model_cls.model_json_schema()
        if existing_data != current_data:
            print(f"DRIFT detected in schema: {schema_path.name}")
            all_match = False

    return all_match


if __name__ == "__main__":
    if "--check" in sys.argv:
        if not check_schemas():
            print("ERROR: Schemas have drifted. Run 'python scripts/export_schemas.py' to update.")
            sys.exit(1)
        print("ALL SCHEMAS UP TO DATE!")
        sys.exit(0)
    else:
        export_schemas()
