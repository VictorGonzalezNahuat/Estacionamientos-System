from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FacturamaConfig:
    base_url: str
    username: str
    password: str
    tax_system: str
    certificate_path: str
    key_path: str


def get_facturama_config() -> FacturamaConfig:
    return FacturamaConfig(
        base_url=os.getenv("FACTURAMA_BASE_URL", "https://api.facturama.mx").strip(),
        username=os.getenv("FACTURAMA_USERNAME", "").strip(),
        password=os.getenv("FACTURAMA_PASSWORD", "").strip(),
        tax_system=os.getenv("FACTURAMA_TAX_SYSTEM", "").strip(),
        certificate_path=os.getenv("FACTURAMA_CERTIFICATE_PATH", "").strip(),
        key_path=os.getenv("FACTURAMA_KEY_PATH", "").strip(),
    )