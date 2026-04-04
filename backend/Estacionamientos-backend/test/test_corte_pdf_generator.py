from datetime import datetime, timedelta
from pathlib import Path
import argparse
import sys
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from printer.corte_pdf import generar_pdf_corte_caja


def _build_movimientos(cantidad: int) -> list[dict]:
    base = datetime.now()
    movimientos: list[dict] = []
    for i in range(cantidad):
        movimientos.append(
            {
                "placa": f"TEST{i:04d}",
                "entrada": base - timedelta(hours=9, minutes=i * 3),
                "salida": base - timedelta(minutes=i * 2),
                "metodo_pago": "tarjeta" if i % 2 else "efectivo",
                "pagado": i % 3 != 0,
                "importe": 25.0 + (i * 1.75),
            }
        )
    return movimientos


def generar_pdf_prueba(cantidad_movimientos: int = 30) -> bytes:
    return generar_pdf_corte_caja(
        corte_id=999,
        turno_id=7,
        cajero="CAJERO TEST",
        fecha_inicio=datetime.now() - timedelta(hours=10),
        fecha_fin=datetime.now(),
        total_calculado=1860.50,
        total_declarado=1850.50,
        diferencia=-10.0,
        total_efectivo=980.50,
        total_tarjeta=880.0,
        movimientos=_build_movimientos(cantidad_movimientos),
    )


class TestGeneradorCortePDF(unittest.TestCase):
    def test_generar_pdf_con_movimientos(self) -> None:
        pdf_bytes = generar_pdf_prueba(35)
        self.assertGreater(len(pdf_bytes), 1500)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


    def test_generar_pdf_sin_movimientos(self) -> None:
        pdf_bytes = generar_pdf_prueba(0)
        self.assertGreater(len(pdf_bytes), 1200)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pruebas y generacion manual del PDF de corte")
    parser.add_argument("--generate", action="store_true", help="Genera un PDF de muestra en printer/pdf/")
    parser.add_argument("--movimientos", type=int, default=35, help="Cantidad de movimientos para el PDF de muestra")
    args = parser.parse_args()

    if args.generate:
        salida = Path("printer/pdf/test_corte_pdf_generator_output.pdf")
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_bytes(generar_pdf_prueba(args.movimientos))
        print(f"PDF de prueba generado en: {salida.resolve()}")
    else:
        unittest.main(argv=["test_corte_pdf_generator"])
