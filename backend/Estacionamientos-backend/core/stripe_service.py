import hmac
import hashlib
import json
import os
from typing import Dict, Optional, Tuple

import requests

from core.payment_provider import ParsedWebhookEvent, normalize_to_json


class StripeService:
    """Servicio de integracion con Stripe usando su API REST."""
    provider_name = "stripe"

    def __init__(self):
        self.secret_key = os.getenv("STRIPE_SECRET_KEY")
        self.publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        self.base_url = os.getenv("WEBHOOK_URL")
        self.success_url = os.getenv("STRIPE_SUCCESS_URL")
        self.cancel_url = os.getenv("STRIPE_CANCEL_URL")
        self.currency = os.getenv("STRIPE_CURRENCY", "mxn").lower()
        self.api_base_url = "https://api.stripe.com/v1"

        if not self.secret_key:
            raise ValueError("STRIPE_SECRET_KEY no configurado en .env")
        if not self.base_url:
            raise ValueError("WEBHOOK_URL no configurado en .env")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def create_checkout(self, placa: str, monto: float, email: Optional[str] = None) -> Tuple[str, str]:
        """Crea una sesion de Checkout y retorna (session_id, checkout_url)."""
        monto_centavos = int(round(monto * 100))
        if monto_centavos <= 0:
            raise ValueError("El monto debe ser mayor a 0")

        success = self.success_url or f"{self.base_url}/pago-exitoso?session_id={{CHECKOUT_SESSION_ID}}"
        cancel = self.cancel_url or f"{self.base_url}/pago-cancelado"

        data = {
            "mode": "payment",
            "success_url": success,
            "cancel_url": cancel,
            "line_items[0][price_data][currency]": self.currency,
            "line_items[0][price_data][product_data][name]": f"Estacionamiento - Vehiculo {placa}",
            "line_items[0][price_data][product_data][description]": f"Pago de estacionamiento para placa {placa}",
            "line_items[0][price_data][unit_amount]": str(monto_centavos),
            "line_items[0][quantity]": "1",
            "metadata[placa]": placa,
        }

        if email:
            data["customer_email"] = email

        response = requests.post(
            f"{self.api_base_url}/checkout/sessions",
            data=data,
            headers=self._headers(),
            timeout=15,
        )
        response.raise_for_status()
        session = response.json()

        session_id = session.get("id")
        checkout_url = session.get("url")
        if not session_id or not checkout_url:
            raise ValueError("Respuesta inesperada de Stripe al crear checkout session")

        return session_id, checkout_url

    def obtener_checkout_session(self, session_id: str) -> Dict:
        response = requests.get(
            f"{self.api_base_url}/checkout/sessions/{session_id}",
            headers={"Authorization": f"Bearer {self.secret_key}"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def validate_webhook_signature(self, headers: Dict[str, str], payload: str) -> bool:
        """Valida Stripe-Signature con HMAC SHA256."""
        stripe_signature = headers.get("Stripe-Signature") or headers.get("stripe-signature")
        if not self.webhook_secret or not stripe_signature:
            return False

        parts = {}
        for part in stripe_signature.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                parts[k] = v

        timestamp = parts.get("t")
        signature_v1 = parts.get("v1")
        if not timestamp or not signature_v1:
            return False

        signed_payload = f"{timestamp}.{payload}".encode("utf-8")
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature_v1)

    def parse_webhook_event(self, payload: str) -> ParsedWebhookEvent:
        try:
            event_data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Payload de webhook invalido") from exc

        event_type = event_data.get("type")
        data_object = event_data.get("data", {}).get("object", {})

        if event_type not in {
            "checkout.session.completed",
            "checkout.session.expired",
            "checkout.session.async_payment_failed",
        }:
            return ParsedWebhookEvent(should_process=False, event_payload=event_data)

        session_id = data_object.get("id")
        if not session_id:
            raise ValueError("Evento de Stripe sin session id")

        if event_type == "checkout.session.completed" and data_object.get("payment_status") == "paid":
            normalized_status = "completado"
        elif event_type == "checkout.session.async_payment_failed":
            normalized_status = "rechazado"
        elif event_type == "checkout.session.expired":
            normalized_status = "cancelado"
        else:
            normalized_status = "pendiente"

        return ParsedWebhookEvent(
            should_process=True,
            lookup_field="preferencia_id",
            lookup_value=session_id,
            normalized_status=normalized_status,
            event_payload=event_data,
        )

    def serialize_event(self, event_data: Dict) -> str:
        return normalize_to_json(event_data)
