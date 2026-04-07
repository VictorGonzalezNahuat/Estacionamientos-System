import json
import os
from dataclasses import dataclass
from typing import Dict, Optional, Protocol, Tuple


@dataclass
class ParsedWebhookEvent:
    should_process: bool
    lookup_field: Optional[str] = None  # "preferencia_id" | "placa"
    lookup_value: Optional[str] = None
    normalized_status: Optional[str] = None  # completado | rechazado | cancelado | pendiente
    provider_transaction_id: Optional[str] = None
    event_payload: Optional[Dict] = None


class PaymentProvider(Protocol):
    provider_name: str

    def create_checkout(self, placa: str, monto: float, email: Optional[str] = None) -> Tuple[str, str]:
        ...

    def validate_webhook_signature(self, headers: Dict[str, str], payload: str) -> bool:
        ...

    def parse_webhook_event(self, payload: str) -> ParsedWebhookEvent:
        ...

    def serialize_event(self, event_data: Dict) -> str:
        ...

    def cancel_checkout(self, checkout_id: str) -> Dict:
        ...


_provider_instances: Dict[str, PaymentProvider] = {}


def _normalize_provider(provider_name: Optional[str]) -> str:
    provider = (provider_name or os.getenv("PAYMENT_PROVIDER", "stripe")).strip().lower()
    if provider in {"mercadopago", "mercado_pago", "mp"}:
        return "mercadopago"
    if provider == "stripe":
        return "stripe"
    raise ValueError("PAYMENT_PROVIDER invalido. Usa 'stripe' o 'mercadopago'.")


def get_payment_provider(provider_name: Optional[str] = None) -> PaymentProvider:
    provider = _normalize_provider(provider_name)
    if provider in _provider_instances:
        return _provider_instances[provider]

    if provider == "stripe":
        from core.stripe_service import StripeService

        _provider_instances[provider] = StripeService()
        return _provider_instances[provider]

    if provider == "mercadopago":
        from core.mercadopago_service import MercadoPagoService

        _provider_instances[provider] = MercadoPagoService()
        return _provider_instances[provider]

    raise ValueError("No se pudo construir proveedor de pagos")


def normalize_to_json(data: Dict) -> str:
    return json.dumps(data, ensure_ascii=True)
