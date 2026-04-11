import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.parking_exit_service import _resolver_accion_transicion
from models.payment_transaction import PaymentTransaction


class TestResolverAccionTransicion(unittest.TestCase):
    def test_estado_cancelado_siempre_ignored_cancelled(self) -> None:
        accion = _resolver_accion_transicion(
            estado_actual=PaymentTransaction.ESTADO_CANCELADO,
            normalized_status="completado",
        )
        self.assertEqual("ignored_cancelled", accion)

    def test_completado_sobre_completado_es_processed_already(self) -> None:
        accion = _resolver_accion_transicion(
            estado_actual=PaymentTransaction.ESTADO_COMPLETADO,
            normalized_status="completado",
        )
        self.assertEqual("processed_already", accion)

    def test_completado_sobre_pendiente_es_mark_completed(self) -> None:
        accion = _resolver_accion_transicion(
            estado_actual=PaymentTransaction.ESTADO_PENDIENTE,
            normalized_status="completado",
        )
        self.assertEqual("mark_completed", accion)

    def test_rechazado_sobre_completado_es_keep_current(self) -> None:
        accion = _resolver_accion_transicion(
            estado_actual=PaymentTransaction.ESTADO_COMPLETADO,
            normalized_status="rechazado",
        )
        self.assertEqual("keep_current", accion)

    def test_rechazado_sobre_pendiente_es_mark_rejected(self) -> None:
        accion = _resolver_accion_transicion(
            estado_actual=PaymentTransaction.ESTADO_PENDIENTE,
            normalized_status="rechazado",
        )
        self.assertEqual("mark_rejected", accion)

    def test_cancelado_sobre_completado_es_keep_current(self) -> None:
        accion = _resolver_accion_transicion(
            estado_actual=PaymentTransaction.ESTADO_COMPLETADO,
            normalized_status="cancelado",
        )
        self.assertEqual("keep_current", accion)

    def test_cancelado_sobre_pendiente_es_mark_cancelled(self) -> None:
        accion = _resolver_accion_transicion(
            estado_actual=PaymentTransaction.ESTADO_PENDIENTE,
            normalized_status="cancelado",
        )
        self.assertEqual("mark_cancelled", accion)

    def test_status_desconocido_sobre_completado_es_keep_current(self) -> None:
        accion = _resolver_accion_transicion(
            estado_actual=PaymentTransaction.ESTADO_COMPLETADO,
            normalized_status="otro_estado",
        )
        self.assertEqual("keep_current", accion)

    def test_status_desconocido_sobre_pendiente_es_mark_pending(self) -> None:
        accion = _resolver_accion_transicion(
            estado_actual=PaymentTransaction.ESTADO_PENDIENTE,
            normalized_status="otro_estado",
        )
        self.assertEqual("mark_pending", accion)


if __name__ == "__main__":
    unittest.main(argv=["test_parking_exit_state_machine"])
