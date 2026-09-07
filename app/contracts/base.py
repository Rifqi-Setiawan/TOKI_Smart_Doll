"""Base contracts and core primitives for TOKI (API-001, API-006)."""

from pydantic import BaseModel, ConfigDict, Field

CURRENT_SCHEMA_VERSION = "1.0"


class ContractModel(BaseModel):
    """Base model for all versioned TOKI domain and API contracts."""

    model_config = ConfigDict(
        extra="forbid",
        validate_default=True,
        populate_by_name=True,
        use_enum_values=False,
        protected_namespaces=(),
    )

    schema_version: str = Field(
        default=CURRENT_SCHEMA_VERSION,
        description="Semantic contract schema version (API-001)",
    )


class CallbackCorrelation(ContractModel):
    """Mandatory correlation metadata for asynchronous or provider callbacks (API-006, ADR-003)."""

    session_id: str = Field(description="Authoritative session identifier")
    turn_id: str = Field(description="Turn correlation identifier")
    state_version: int = Field(
        ge=1,
        description="Monotonic state version for optimistic concurrency guard (API-006)",
    )
