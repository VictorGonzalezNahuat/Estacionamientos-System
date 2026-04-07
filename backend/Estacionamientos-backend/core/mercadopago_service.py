import hashlib
import hmac
import json
import os
from typing import Dict, Optional, Tuple

import requests

from core.payment_provider import ParsedWebhookEvent, normalize_to_json


class MercadoPagoService:
    provider_name = "mercadopago"

    def __init__(self):
        self.access_token = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
        self.public_key = os.getenv("MERCADO_PAGO_PUBLIC_KEY")
        self.webhook_secret = os.getenv("MERCADO_PAGO_WEBHOOK_SECRET")
        self.webhook_url = os.getenv("WEBHOOK_URL")
        self.currency = os.getenv("MERCADO_PAGO_CURRENCY", "MXN")
        self.api_base_url = "https://api.mercadopago.com"

        if not self.access_token:
            raise ValueError("MERCADO_PAGO_ACCESS_TOKEN no configurado en .env")
        if not self.webhook_url:
            raise ValueError("WEBHOOK_URL no configurado en .env")

    def create_checkout(self, placa: str, monto: float, email: Optional[str] = None) -> Tuple[str, str]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "items": [
                {
                    "title": f"Estacionamiento - Vehiculo {placa}",
                    "description": f"Pago de estacionamiento para placa {placa}",
                    "quantity": 1,
                    "unit_price": round(monto, 2),
                    "currency_id": self.currency,
                }
            ],
            "payer": {"email": email or "cliente@estacionamiento.com"},
            "external_reference": placa,
            "notification_url": f"{self.webhook_url}/pagos/webhook",
            "back_urls": {
                "success": f"{self.webhook_url}/pago-exitoso",
                "failure": f"{self.webhook_url}/pago-fallido",
                "pending": f"{self.webhook_url}/pago-pendiente",
            },
            "auto_return": "approved",
        }

        response = requests.post(
            f"{self.api_base_url}/checkout/preferences",
            json=payload,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        preferencia_id = data.get("id")
        checkout_url = data.get("init_point")

        if not preferencia_id or not checkout_url:
            raise ValueError("Respuesta inesperada de Mercado Pago")

        return preferencia_id, checkout_url

    def validate_webhook_signature(self, headers: Dict[str, str], payload: str) -> bool:
        signature = headers.get("X-Signature") or headers.get("x-signature")
        if not self.webhook_secret or not signature:
            return False

        parts = {}
        for part in signature.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                parts[key.strip()] = value.strip()

        timestamp = parts.get("ts")
        signature_v1 = parts.get("v1")
        if not timestamp or not signature_v1:
            return False

        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            f"{timestamp}.{payload}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature_v1, expected)

    def _obtener_pago(self, payment_id: int) -> Dict:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(
            f"{self.api_base_url}/v1/payments/{payment_id}",
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def parse_webhook_event(self, payload: str) -> ParsedWebhookEvent:
        try:
            webhook_event = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Payload de webhook invalido") from exc

        topic = webhook_event.get("topic") or webhook_event.get("type")
        resource = webhook_event.get("resource")

        if topic != "payment" or not resource:
            return ParsedWebhookEvent(should_process=False, event_payload=webhook_event)

        try:
            payment_id = int(str(resource).split("/")[-1])
        except (ValueError, IndexError) as exc:
            raise ValueError("Webhook de MercadoPago sin payment_id valido") from exc

        payment_info = self._obtener_pago(payment_id)
        payment_status = payment_info.get("status")
        external_reference = payment_info.get("external_reference")

        status_map = {
            "approved": "completado",
            "rejected": "rechazado",
            "cancelled": "cancelado",
            "refunded": "cancelado",
        }

        normalized = status_map.get(payment_status, "pendiente")
        merged_payload = {
            "webhook": webhook_event,
            "payment": payment_info,
        }

        return ParsedWebhookEvent(
            should_process=True,
            lookup_field="placa",
            lookup_value=external_reference,
            normalized_status=normalized,
            event_payload=merged_payload,
        )

    def serialize_event(self, event_data: Dict) -> str:
        return normalize_to_json(event_data)

    def cancel_checkout(self, checkout_id: str) -> Dict:
        # MercadoPago preference cancellation is not used in the current flow.
        return {
            "supported": False,
            "cancelled_remote": False,
            "checkout_id": checkout_id,
            "message": "Cancelacion remota no soportada para mercadopago en este flujo",
        }
