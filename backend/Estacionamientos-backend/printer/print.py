import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from core import config as app_config
from escpos.printer import Network


_PRINTER_DIR = Path(__file__).resolve().parent
_LOGO_TICKET_ENTRADA = _PRINTER_DIR / "boleto.png"
_LOGO_TICKET_SALIDA = _PRINTER_DIR / "boleto_salida.png"


def _texto_escpos(texto: str) -> bytes:
	return texto.encode("cp437", errors="replace")


def _placa_para_code39(placa: str) -> str:
	permitidos = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%")
	placa_limpia = (placa or "").strip().upper().replace("_", "-")
	barcode = "".join(ch for ch in placa_limpia if ch in permitidos)
	return barcode or "SINPLACA"


def _barcode_code39(placa: str) -> bytes:
	"""Genera comandos ESC/POS para imprimir la placa como Code39."""
	gs = b"\x1d"
	barcode_data = _placa_para_code39(placa).encode("ascii", errors="ignore")

	# Altura, ancho y texto legible debajo del barcode.
	set_hri_pos = gs + b"H" + b"\x02"
	set_hri_font = gs + b"f" + b"\x00"
	set_height = gs + b"h" + b"\x50"
	set_width = gs + b"w" + b"\x02"

	# GS k m d NUL -> m=4 (Code39)
	print_code39 = gs + b"k" + b"\x04" + barcode_data + b"\x00"
	return set_hri_pos + set_hri_font + set_height + set_width + print_code39



def _qr_data(data_texto: str) -> bytes:
	"""Genera comandos ESC/POS para imprimir QR con texto UTF-8."""
	gs = b"\x1d"
	payload = (data_texto or "").strip() or "SINPLACA"
	data = payload.encode("utf-8", errors="replace")

	model = gs + b"(" + b"k" + b"\x04\x00" + b"1" + b"A" + b"2" + b"\x00"
	size = gs + b"(" + b"k" + b"\x03\x00" + b"1" + b"C" + b"\x06"
	error = gs + b"(" + b"k" + b"\x03\x00" + b"1" + b"E" + b"1"

	store_len = len(data) + 3
	pl_byte = bytes([store_len % 256])
	ph_byte = bytes([store_len // 256])
	store = gs + b"(" + b"k" + pl_byte + ph_byte + b"1" + b"P" + b"0" + data
	print_qr = gs + b"(" + b"k" + b"\x03\x00" + b"1" + b"Q" + b"0"

	return model + size + error + store + print_qr


def _qr_placa(placa: str) -> bytes:
	"""Genera comandos ESC/POS para imprimir QR con la placa."""
	pl = (placa or "").strip().upper() or "SINPLACA"
	return _qr_data(pl)


def _url_estado_publico(placa: str) -> str:
	placa_limpia = (placa or "").strip() or "SINPLACA"
	placa_encoded = quote(placa_limpia, safe="")
	base_url = app_config.PUBLIC_STATUS_BASE_URL.rstrip("/")
	return f"{base_url}/public/estado/{placa_encoded}/view"


def _modo_codigo_entrada() -> str:
	"""Define si ticket de entrada imprime BARCODE o QR segun config central."""
	modo = app_config.ENTRY_TICKET_CODE_TYPE
	if modo in {"QR", "BARCODE"}:
		return modo
	return "BARCODE"


def _detectar_logo_ticket(ticket_bytes: bytes) -> Optional[Path]:
	"""Determina el logo a imprimir segun el tipo de ticket."""
	if b"TICKET DE ENTRADA" in ticket_bytes:
		return _LOGO_TICKET_ENTRADA
	if b"TICKET DE SALIDA" in ticket_bytes:
		return _LOGO_TICKET_SALIDA
	return None


def _imprimir_logo_ticket(impresora: Network, logo_path: Optional[Path]) -> None:
	"""Imprime el logo del ticket cuando existe; si falla, no interrumpe el flujo."""
	if not logo_path or not logo_path.exists():
		return

	try:
		# Centra el logo antes del contenido del ticket.
		impresora._raw(b"\x1b\x61\x01")
		impresora.image(str(logo_path), impl="bitImageRaster")
		impresora._raw(b"\n")
	except Exception:
		# Si no se puede imprimir imagen, continua con el ticket de texto.
		return


def imprimir_ticket_red(ticket_bytes: bytes, copias: int = 1) -> tuple[bool, str]:
	"""Envia un ticket ESC/POS a impresora de red usando host/puerto por entorno."""
	host = os.getenv("PRINTER_HOST", "192.168.1.130").strip()
	port = int(os.getenv("PRINTER_PORT", "9100"))
	timeout = int(os.getenv("PRINTER_TIMEOUT", "10"))
	copias = max(1, int(copias))

	if not host:
		return False, "PRINTER_HOST no esta configurado"

	impresora = None
	try:
		impresora = Network(host=host, port=port, timeout=timeout)
		for _ in range(copias):
			logo_path = _detectar_logo_ticket(ticket_bytes)
			_imprimir_logo_ticket(impresora, logo_path)
			impresora._raw(ticket_bytes)
		return True, f"Ticket enviado a impresora ({copias} copia(s))"
	except Exception as exc:
		return False, f"No se pudo imprimir en red: {exc}"
	finally:
		if impresora is not None:
			try:
				impresora.close()
			except Exception:
				pass


def generar_ticket_salida_prueba(
	folio: str = "SAL-PRUEBA-001",
	placa: str = "ABC-123-A",
	fecha_entrada: Optional[datetime] = None,
	fecha_salida: Optional[datetime] = None,
	minutos_estadia: int = 90,
	total_pagado: float = 45.0,
	cajero: str = "SISTEMA",
	etiqueta: Optional[str] = None,
) -> bytes:
	"""Genera un ticket de salida de prueba con comandos ESC/POS."""
	fecha_entrada = fecha_entrada or datetime.now()
	fecha_salida = fecha_salida or datetime.now()

	# Comandos base ESC/POS.
	esc = b"\x1b"
	gs = b"\x1d"

	init = esc + b"@"
	align_left = esc + b"a" + b"\x00"
	align_center = esc + b"a" + b"\x01"
	bold_on = esc + b"E" + b"\x01"
	bold_off = esc + b"E" + b"\x00"
	size_normal = esc + b"!" + b"\x00"
	size_doble = esc + b"!" + b"\x30"
	line_feed_3 = esc + b"d" + b"\x03"
	cut_full = gs + b"V" + b"\x00"

	buffer = bytearray()
	buffer += init
	buffer += align_center
	buffer += bold_on + size_doble
	buffer += _texto_escpos("ESTACIONAMIENTO CENTRO\n")
	buffer += size_normal + bold_off
	buffer += _texto_escpos("TICKET DE SALIDA\n")
	if etiqueta:
		buffer += bold_on
		buffer += _texto_escpos(f"{etiqueta}\n")
		buffer += bold_off
	buffer += _texto_escpos("--------------------------------\n")

	buffer += align_left
	buffer += _texto_escpos(f"Folio        : {folio}\n")
	buffer += _texto_escpos(f"Placa        : {placa}\n")
	buffer += _texto_escpos(f"Entrada      : {fecha_entrada:%Y-%m-%d %H:%M:%S}\n")
	buffer += _texto_escpos(f"Salida       : {fecha_salida:%Y-%m-%d %H:%M:%S}\n")
	buffer += _texto_escpos(f"Tiempo total : {minutos_estadia} min\n")
	buffer += _texto_escpos(f"Total pagado : ${total_pagado:.2f}\n")
	buffer += _texto_escpos(f"Encargado       : {cajero}\n")

	buffer += align_center
	buffer += _texto_escpos("--------------------------------\n")
	buffer += _texto_escpos("Gracias por su preferencia\n")
	buffer += _texto_escpos("--------------------------------\n")
	buffer += _texto_escpos("\n")
	buffer += _texto_escpos("\n")
	buffer += line_feed_3
	buffer += cut_full

	return bytes(buffer)


def generar_ticket_entrada_prueba(
	folio: str = "ENT-PRUEBA-001",
	placa: str = "ABC-123-A",
	fecha_entrada: Optional[datetime] = None,
	tarifa_nombre: str = "Tarifa General",
	cajero: str = "SISTEMA",
) -> bytes:
	"""Genera un ticket de entrada de prueba con comandos ESC/POS."""
	fecha_entrada = fecha_entrada or datetime.now()

	# Comandos base ESC/POS.
	esc = b"\x1b"
	gs = b"\x1d"

	init = esc + b"@"
	align_left = esc + b"a" + b"\x00"
	align_center = esc + b"a" + b"\x01"
	bold_on = esc + b"E" + b"\x01"
	bold_off = esc + b"E" + b"\x00"
	size_normal = esc + b"!" + b"\x00"
	size_doble = esc + b"!" + b"\x30"
	line_feed_3 = esc + b"d" + b"\x03"
	cut_full = gs + b"V" + b"\x00"

	buffer = bytearray()
	buffer += init
	buffer += align_center
	buffer += bold_on + size_doble
	buffer += _texto_escpos("ESTACIONAMIENTO CENTRO\n")
	buffer += size_normal + bold_off
	buffer += _texto_escpos("TICKET DE ENTRADA\n")
	buffer += _texto_escpos("--------------------------------\n")

	buffer += align_left
	buffer += _texto_escpos(f"Folio        : {folio}\n")
	buffer += _texto_escpos(f"Placa        : {placa}\n")
	buffer += _texto_escpos(f"Entrada      : {fecha_entrada:%Y-%m-%d %H:%M:%S}\n")
	buffer += _texto_escpos(f"Tarifa       : {tarifa_nombre}\n")
	buffer += _texto_escpos(f"Encargado       : {cajero}\n")
	buffer += _texto_escpos("\n")
	buffer += align_center
	modo_codigo = _modo_codigo_entrada()
	if modo_codigo == "QR":
		buffer += _texto_escpos("CODIGO QR\n")
		buffer += _qr_placa(placa)
	else:
		buffer += _texto_escpos("CODIGO DE BARRA\n")
		buffer += _barcode_code39(placa)
	buffer += _texto_escpos("\n")
	if app_config.MOBILE_PRINT:
		buffer += _texto_escpos("Consulta el estado de tu vehiculo\n")
		buffer += _texto_escpos("escaneando abajo\n")
		buffer += _qr_data(_url_estado_publico(placa))
		buffer += _texto_escpos("\n")

	buffer += align_center
	buffer += _texto_escpos("--------------------------------\n")
	buffer += _texto_escpos("Conserve este ticket\n")
	buffer += _texto_escpos("para realizar su salida\n")
	buffer += _texto_escpos("--------------------------------\n")
	buffer += _texto_escpos("\n")
	buffer += _texto_escpos("\n")
	buffer += line_feed_3
	buffer += cut_full

	return bytes(buffer)
