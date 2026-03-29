from pydantic import BaseModel, Field, field_validator


class ConfiguracionResponse(BaseModel):
    DATABASE_CLOUD_USER: str
    DATABASE_CLOUD_HOST: str
    DATABASE_CLOUD_PORT: int
    DATABASE_CLOUD_NAME: str
    SYNC_AUTO_ENABLED: bool
    SYNC_INTERVAL_MINUTES: int
    MOBILE_PRINT: bool
    ENTRY_TICKET_CODE_TYPE: str
    PUBLIC_STATUS_BASE_URL: str


class ConfiguracionUpdate(BaseModel):
    DATABASE_CLOUD_USER: str = Field(min_length=1)
    DATABASE_CLOUD_PASSWORD: str = Field(min_length=1)
    DATABASE_CLOUD_HOST: str = Field(min_length=1)
    DATABASE_CLOUD_PORT: int = Field(ge=1, le=65535)
    DATABASE_CLOUD_NAME: str = Field(min_length=1)
    SYNC_AUTO_ENABLED: bool
    SYNC_INTERVAL_MINUTES: int = Field(ge=1)
    MOBILE_PRINT: bool
    ENTRY_TICKET_CODE_TYPE: str
    PUBLIC_STATUS_BASE_URL: str = Field(min_length=1)

    @field_validator(
        "DATABASE_CLOUD_USER",
        "DATABASE_CLOUD_PASSWORD",
        "DATABASE_CLOUD_HOST",
        "DATABASE_CLOUD_NAME",
        "PUBLIC_STATUS_BASE_URL",
    )
    @classmethod
    def validate_non_empty_text(cls, value):
        if not value or not value.strip():
            raise ValueError("Este campo no puede estar vacio")
        return value.strip()

    @field_validator("ENTRY_TICKET_CODE_TYPE")
    @classmethod
    def validate_entry_ticket_code_type(cls, value):
        mode = value.strip().upper()
        if mode not in {"BARCODE", "QR"}:
            raise ValueError("ENTRY_TICKET_CODE_TYPE debe ser BARCODE o QR")
        return mode
