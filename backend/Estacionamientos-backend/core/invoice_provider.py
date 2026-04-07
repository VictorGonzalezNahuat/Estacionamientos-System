import json
import os
from dataclasses import dataclass
from typing import Dict, Optional, Protocol


@dataclass
class IssueInvoiceInput:
    external_id: str
    customer: Dict
    amount: float
    currency: str = "MXN"
    description: str = "Servicio de estacionamiento"
    payment_form: str = "01"
    send_email: bool = False


@dataclass
class IssueInvoiceResult:
    provider_invoice_id: Optional[str]
    status: str
    uuid_fiscal: Optional[str] = None
    serie: Optional[str] = None
    folio: Optional[str] = None
    issued_at: Optional[str] = None
    subtotal: Optional[float] = None
    taxes: Optional[float] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    xml_url: Optional[str] = None
    pdf_url: Optional[str] = None
    verification_url: Optional[str] = None
    raw_response: Optional[Dict] = None


@dataclass
class CancelInvoiceResult:
    status: str
    cancelled_at: Optional[str] = None
    raw_response: Optional[Dict] = None


class InvoiceProvider(Protocol):
    provider_name: str

    def issue_invoice(self, payload: IssueInvoiceInput) -> IssueInvoiceResult:
        ...

    def cancel_invoice(self, provider_invoice_id: str, motivo: str, comentario: Optional[str]) -> CancelInvoiceResult:
        ...

    def get_invoice_xml(self, provider_invoice_id: str) -> tuple[bytes, str]:
        ...

    def get_invoice_pdf(self, provider_invoice_id: str) -> tuple[bytes, str]:
        ...

    def send_invoice_by_email(self, provider_invoice_id: str, email: Optional[str] = None) -> dict:
        ...

    def serialize_event(self, event_data: Dict) -> str:
        ...


_provider_instances: Dict[str, InvoiceProvider] = {}


def _normalize_provider(provider_name: Optional[str]) -> str:
    provider = (provider_name or os.getenv("INVOICE_PROVIDER", "facturapi")).strip().lower()
    if provider in {"facturapi", "factura_api", "fapi"}:
        return "facturapi"
    raise ValueError("INVOICE_PROVIDER invalido. Usa 'facturapi'.")


def get_invoice_provider(provider_name: Optional[str] = None) -> InvoiceProvider:
    provider = _normalize_provider(provider_name)
    if provider in _provider_instances:
        return _provider_instances[provider]

    if provider == "facturapi":
        from core.facturapi_service import FacturapiService

        _provider_instances[provider] = FacturapiService()
        return _provider_instances[provider]

    raise ValueError("No se pudo construir proveedor de facturacion")


def normalize_to_json(data: Dict) -> str:
    return json.dumps(data, ensure_ascii=True)
