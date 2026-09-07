"""Contract compatibility and schema snapshot tests (API-001, API-004)."""

import json
from pathlib import Path

from scripts.export_schemas import EXPORTED_CONTRACTS

SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas"


def test_exported_schemas_exist_and_match():
    """Verify that all exported JSON schemas exist on disk and match model schemas (API-001)."""
    assert SCHEMAS_DIR.exists(), "schemas directory must exist"

    for name, model_cls in EXPORTED_CONTRACTS.items():
        schema_file = SCHEMAS_DIR / f"{name}.json"
        assert schema_file.exists(), f"Missing exported schema file: {schema_file.name}"

        with open(schema_file, encoding="utf-8") as f:
            disk_schema = json.load(f)

        live_schema = model_cls.model_json_schema()
        assert disk_schema == live_schema, f"Schema mismatch for {name}"
        assert "properties" in disk_schema
        assert "schema_version" in disk_schema["properties"]


def test_additive_change_backward_compatibility():
    """API-004: Additive fields with default values maintain backward compatibility."""
    from app.contracts.device import CommandType, DeviceCommand

    # Payload created without optional 'parameters' or new optional fields
    legacy_payload = {
        "schema_version": "1.0",
        "command_type": "START_SESSION",
    }

    command = DeviceCommand.model_validate(legacy_payload)
    assert command.command_type == CommandType.START_SESSION
    assert command.parameters == {}
    assert command.audio_asset_id is None
