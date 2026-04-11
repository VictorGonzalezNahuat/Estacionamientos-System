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
    AVISO_ENTRADA: str
    AVISO_SALIDA: str


class DatabaseConfigUpdate(BaseModel):
    """Schema para actualizar la configuracion de la base de datos"""
    DATABASE_CLOUD_USER: str = Field(min_length=1)
    DATABASE_CLOUD_PASSWORD: str = Field(min_length=1)
    DATABASE_CLOUD_HOST: str = Field(min_length=1)
    DATABASE_CLOUD_PORT: int = Field(ge=1, le=65535)
    DATABASE_CLOUD_NAME: str = Field(min_length=1)

    @field_validator(
        "DATABASE_CLOUD_USER",
        "DATABASE_CLOUD_PASSWORD",
        "DATABASE_CLOUD_HOST",
        "DATABASE_CLOUD_NAME",
    )
    @classmethod
    def validate_non_empty_text(cls, value):
        if not value or not value.strip():
            raise ValueError("Este campo no puede estar vacio")
        return value.strip()


class OtherConfigUpdate(BaseModel):
    """Schema para actualizar las demas variables de configuracion (sin contraseña de BD)"""
    SYNC_AUTO_ENABLED: bool | None = None
    SYNC_INTERVAL_MINUTES: int | None = Field(None, ge=1)
    MOBILE_PRINT: bool | None = None
    ENTRY_TICKET_CODE_TYPE: str | None = None
    PUBLIC_STATUS_BASE_URL: str | None = Field(None, min_length=1)
    AVISO_ENTRADA: str | None = None
    AVISO_SALIDA: str | None = None

    @field_validator("PUBLIC_STATUS_BASE_URL")
    @classmethod
    def validate_non_empty_text(cls, value):
        if value is not None and (not value or not value.strip()):
            raise ValueError("PUBLIC_STATUS_BASE_URL no puede estar vacio")
        return value.strip() if value else None

    @field_validator("ENTRY_TICKET_CODE_TYPE")
    @classmethod
    def validate_entry_ticket_code_type(cls, value):
        if value is None:
            return None
        mode = value.strip().upper()
        if mode not in {"BARCODE", "QR"}:
            raise ValueError("ENTRY_TICKET_CODE_TYPE debe ser BARCODE o QR")
        return mode

    @field_validator("AVISO_ENTRADA", "AVISO_SALIDA")
    @classmethod
    def normalize_notice_text(cls, value):
        if value is None:
            return None
        return value.replace("\r\n", "\n").replace("\r", "\n").strip()


class ConfiguracionUpdate(BaseModel):
    """Schema deprecado - mantener para retrocompatibilidad"""
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
    AVISO_ENTRADA: str = ""
    AVISO_SALIDA: str = ""

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

    @field_validator("AVISO_ENTRADA", "AVISO_SALIDA")
    @classmethod
    def normalize_notice_text(cls, value):
        return value.replace("\r\n", "\n").replace("\r", "\n").strip()


class CortesConfiguracionResponse(BaseModel):
    AUTOSEND_REPORT: bool
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_USE_TLS: bool
    SMTP_TIMEOUT_SECONDS: int
    REPORT_FROM_NAME: str
    REPORT_SUBJECT_TEMPLATE: str


class CortesConfiguracionUpdate(BaseModel):
    AUTOSEND_REPORT: bool | None = None
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = Field(None, ge=1, le=65535)
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool | None = None
    SMTP_TIMEOUT_SECONDS: int | None = Field(None, ge=1)
    REPORT_FROM_NAME: str | None = None
    REPORT_SUBJECT_TEMPLATE: str | None = None

    @field_validator(
        "SMTP_HOST",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "REPORT_FROM_NAME",
        "REPORT_SUBJECT_TEMPLATE",
    )
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        return value.strip()


class PrinterNetworkConfig(BaseModel):
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    timeout: int = Field(ge=1)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value):
        host = value.strip()
        if not host:
            raise ValueError("host no puede estar vacio")
        return host


class PrinterUsbConfig(BaseModel):
    mode: str = "WINDOWS_DEFAULT"
    printer_name: str = ""

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value):
        mode = value.strip().upper()
        if mode != "WINDOWS_DEFAULT":
            raise ValueError("mode actualmente solo soporta WINDOWS_DEFAULT")
        return mode

    @field_validator("printer_name")
    @classmethod
    def normalize_printer_name(cls, value):
        return value.strip()


class PrinterConfigResponse(BaseModel):
    method: str
    network: PrinterNetworkConfig
    usb: PrinterUsbConfig

    @field_validator("method")
    @classmethod
    def validate_method(cls, value):
        method = value.strip().upper()
        if method not in {"NETWORK", "USB"}:
            raise ValueError("method debe ser NETWORK o USB")
        return method


class PrinterNetworkConfigUpdate(BaseModel):
    host: str | None = None
    port: int | None = Field(None, ge=1, le=65535)
    timeout: int | None = Field(None, ge=1)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value):
        if value is None:
            return None
        host = value.strip()
        if not host:
            raise ValueError("host no puede estar vacio")
        return host


class PrinterUsbConfigUpdate(BaseModel):
    mode: str | None = None
    printer_name: str | None = None

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value):
        if value is None:
            return None
        mode = value.strip().upper()
        if mode != "WINDOWS_DEFAULT":
            raise ValueError("mode actualmente solo soporta WINDOWS_DEFAULT")
        return mode

    @field_validator("printer_name")
    @classmethod
    def normalize_printer_name(cls, value):
        if value is None:
            return None
        return value.strip()


class PrinterConfigUpdate(BaseModel):
    method: str | None = None
    network: PrinterNetworkConfigUpdate | None = None
    usb: PrinterUsbConfigUpdate | None = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, value):
        if value is None:
            return None
        method = value.strip().upper()
        if method not in {"NETWORK", "USB"}:
            raise ValueError("method debe ser NETWORK o USB")
        return method
