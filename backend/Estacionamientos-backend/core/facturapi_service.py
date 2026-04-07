import os
from datetime import datetime
from typing import Dict, Optional

import requests

from core.invoice_provider import (
    CancelInvoiceResult,
    IssueInvoiceInput,
    IssueInvoiceResult,
    normalize_to_json,
)


class FacturapiService:
    provider_name = "facturapi"

    def __init__(self):
        self.api_key = os.getenv("FACTURAPI_API_KEY", "").strip()
        self.base_url = os.getenv("FACTURAPI_BASE_URL", "https://www.facturapi.io/v2").strip().rstrip("/")
        self.default_tax_included = os.getenv("FACTURAPI_TAX_INCLUDED", "true").strip().lower() in {"1", "true", "yes", "on"}
        self.default_payment_form = os.getenv("FACTURAPI_PAYMENT_FORM", "01").strip()
        self.default_use = os.getenv("FACTURAPI_USE", "S01").strip().upper()
        self.default_product_key = os.getenv("FACTURAPI_PRODUCT_KEY", "78111808").strip()
        self.default_unit_key = os.getenv("FACTURAPI_UNIT_KEY", "E48").strip().upper()
        self.default_series = os.getenv("FACTURAPI_SERIE", "F").strip()

        if not self.api_key:
            raise ValueError("FACTURAPI_API_KEY no configurado en .env")

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
        }

    def _auth(self) -> tuple[str, str]:
        # Facturapi usa API key como username en Basic Auth.
        return (self.api_key, "")

    def _compact(self, value):
        if isinstance(value, dict):
            return {
                key: self._compact(inner)
                for key, inner in value.items()
                if inner is not None and inner != ""
            }
        if isinstance(value, list):
            return [self._compact(item) for item in value if item is not None]
        return value

    def _raise_facturapi_error(self, response: requests.Response) -> None:
        try:
            body = response.json()
        except Exception:
            body = response.text or "Error desconocido"
        raise ValueError(f"Facturapi error {response.status_code}: {body}")

    def issue_invoice(self, payload: IssueInvoiceInput) -> IssueInvoiceResult:
        customer_data = payload.customer

        invoice_payload = {
            "payment_form": payload.payment_form or self.default_payment_form,
            "use": customer_data.get("uso_cfdi_receptor") or self.default_use,
            "customer": {
                "legal_name": customer_data.get("razon_social"),
                "tax_id": customer_data.get("rfc"),
                "tax_system": customer_data.get("regimen_fiscal"),
                "address": {
                    "zip": customer_data.get("codigo_postal"),
                },
                "email": customer_data.get("email"),
            },
            "items": [
                {
                    "quantity": 1,
                    "product": {
                        "description": payload.description,
                        "product_key": self.default_product_key,
                        "unit_key": self.default_unit_key,
                        "price": round(float(payload.amount), 2),
                        "tax_included": self.default_tax_included,
                    },
                }
            ],
            "series": self.default_series,
            "currency": payload.currency,
            "external_id": payload.external_id,
        }

        compact_payload = self._compact(invoice_payload)

        response = requests.post(
            f"{self.base_url}/invoices",
            json=compact_payload,
            headers=self._headers(),
            auth=self._auth(),
            timeout=20,
        )
        if response.status_code >= 400:
            self._raise_facturapi_error(response)

        body = response.json() if response.content else {}

        uuid = body.get("uuid")
        provider_invoice_id = body.get("id")
        issued_at = body.get("date")
        status = "issued" if uuid else "processing"

        return IssueInvoiceResult(
            provider_invoice_id=provider_invoice_id,
            status=status,
            uuid_fiscal=uuid,
            serie=body.get("series"),
            folio=str(body.get("folio")) if body.get("folio") is not None else None,
            issued_at=issued_at,
            subtotal=float(body.get("subtotal", 0.0)) if body.get("subtotal") is not None else None,
            taxes=float(body.get("total_tax", 0.0)) if body.get("total_tax") is not None else None,
            total=float(body.get("total", 0.0)) if body.get("total") is not None else None,
            currency=body.get("currency"),
            xml_url=body.get("xml_url"),
            pdf_url=body.get("pdf_url"),
            verification_url=body.get("verification_url"),
            raw_response=body,
        )

    def cancel_invoice(self, provider_invoice_id: str, motivo: str, comentario: Optional[str]) -> CancelInvoiceResult:
        payload = {
            "motive": motivo,
            "comments": comentario,
        }
        response = requests.post(
            f"{self.base_url}/invoices/{provider_invoice_id}/cancel",
            json=payload,
            headers=self._headers(),
            auth=self._auth(),
            timeout=20,
        )
        response.raise_for_status()

        body = response.json() if response.content else {}
        cancelled_at = body.get("cancel_date") or datetime.utcnow().isoformat()

        return CancelInvoiceResult(
            status="cancelled",
            cancelled_at=cancelled_at,
            raw_response=body,
        )

    def get_invoice_xml(self, provider_invoice_id: str) -> tuple[bytes, str]:
        response = requests.get(
            f"{self.base_url}/invoices/{provider_invoice_id}/xml",
            headers=self._headers(),
            auth=self._auth(),
            timeout=20,
        )
        if response.status_code >= 400:
            self._raise_facturapi_error(response)

        content_type = response.headers.get("Content-Type", "application/xml")
        return response.content, content_type

    def get_invoice_pdf(self, provider_invoice_id: str) -> tuple[bytes, str]:
        response = requests.get(
            f"{self.base_url}/invoices/{provider_invoice_id}/pdf",
            headers=self._headers(),
            auth=self._auth(),
            timeout=20,
        )
        if response.status_code >= 400:
            self._raise_facturapi_error(response)

        content_type = response.headers.get("Content-Type", "application/pdf")
        return response.content, content_type

    def send_invoice_by_email(self, provider_invoice_id: str, email: Optional[str] = None) -> dict:
        payload = {}
        if email:
            payload["email"] = email

        response = requests.post(
            f"{self.base_url}/invoices/{provider_invoice_id}/email",
            json=payload or None,
            headers=self._headers(),
            auth=self._auth(),
            timeout=20,
        )
        if response.status_code >= 400:
            self._raise_facturapi_error(response)

        return response.json() if response.content else {"ok": True}

    def serialize_event(self, event_data: Dict) -> str:
        return normalize_to_json(event_data)
