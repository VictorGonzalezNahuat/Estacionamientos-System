import os
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import quote

from core import config as app_config
from escpos.printer import Network


_PRINTER_DIR = Path(__file__).resolve().parent
_ENCABEZADO_ENTRADA = _PRINTER_DIR / "encabezado_entrada.png"
_ENCABEZADO_SALIDA = _PRINTER_DIR / "encabezado_salida.png"
_ANCHO_AVISO_80MM = 42


def _texto_escpos(texto: str) -> bytes:
	return texto.encode("cp437", errors="replace")


def _formatear_fecha_ddmmaaaa(fecha_hora: datetime) -> str:
	return fecha_hora.strftime("%d/%m/%Y")


def _formatear_hora_12h(fecha_hora: datetime) -> str:
	return fecha_hora.strftime("%I:%M:%S %p")


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


def _agregar_aviso_personalizado(buffer: bytearray, aviso: str) -> None:
	"""Agrega un bloque de aviso multi-linea si existe texto configurado."""
	texto = (aviso or "").replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()
	texto = texto.replace("\\n", "\n")
	if not texto:
		return

	buffer += _texto_escpos("\n")
	for bloque in texto.split("\n"):
		linea = bloque.strip()
		if not linea:
			buffer += _texto_escpos("\n")
			continue

		for linea_envuelta in textwrap.wrap(
			linea,
			width=_ANCHO_AVISO_80MM,
			break_long_words=True,
			break_on_hyphens=False,
		):
			buffer += _texto_escpos(f"{linea_envuelta}\n")


def _obtener_encabezado_ticket(tipo_ticket: str) -> Optional[Path]:
	"""Retorna la ruta del encabezado segun el tipo de ticket.
	
	Args:
		tipo_ticket: "entrada" o "salida"
	"""
	if tipo_ticket == "entrada":
		return _ENCABEZADO_ENTRADA
	elif tipo_ticket == "salida":
		return _ENCABEZADO_SALIDA
	return None


def _imprimir_encabezado_ticket(impresora: Network, encabezado_path: Optional[Path]) -> None:
	"""Imprime el encabezado del ticket cuando existe; si falla, no interrumpe el flujo."""
	if not encabezado_path or not encabezado_path.exists():
		return

	try:
		# Centra el encabezado antes del contenido del ticket.
		impresora._raw(b"\x1b\x61\x01")
		impresora.image(str(encabezado_path), impl="bitImageRaster")
		impresora._raw(b"\n")
	except Exception:
		# Si no se puede imprimir imagen, continua con el ticket de texto.
		return


def imprimir_ticket_red(ticket_bytes: bytes, copias: int = 1, tipo_ticket: str = "salida") -> tuple[bool, str]:
	"""Envia un ticket ESC/POS a impresora de red usando host/puerto por entorno.
	
	Args:
		ticket_bytes: Contenido del ticket en formato ESC/POS
		copias: Numero de copias a imprimir
		tipo_ticket: "entrada" o "salida" para seleccionar el encabezado correcto
	"""
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
			encabezado_path = _obtener_encabezado_ticket(tipo_ticket)
			_imprimir_encabezado_ticket(impresora, encabezado_path)
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


def imprimir_tickets_red(ticket_lote: Sequence[bytes], tipo_ticket: str = "salida") -> tuple[bool, str]:
	"""Imprime varios tickets en una sola sesion de impresora para mayor confiabilidad."""
	host = os.getenv("PRINTER_HOST", "192.168.1.130").strip()
	port = int(os.getenv("PRINTER_PORT", "9100"))
	timeout = int(os.getenv("PRINTER_TIMEOUT", "10"))

	if not host:
		return False, "PRINTER_HOST no esta configurado"

	lote = [tb for tb in ticket_lote if tb]
	if not lote:
		return False, "No hay tickets para imprimir"

	impresora = None
	try:
		impresora = Network(host=host, port=port, timeout=timeout)
		encabezado_path = _obtener_encabezado_ticket(tipo_ticket)
		for ticket_bytes in lote:
			_imprimir_encabezado_ticket(impresora, encabezado_path)
			impresora._raw(ticket_bytes)
		return True, f"Tickets enviados a impresora ({len(lote)} ticket(s))"
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
	metodo_pago: str = "Efectivo",
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
	if etiqueta:
		buffer += bold_on
		buffer += _texto_escpos(f"{etiqueta}\n")
		buffer += bold_off
	buffer += _texto_escpos("--------------------------------\n")

	buffer += align_left
	buffer += _texto_escpos(f"Placa        : {placa}\n")
	buffer += _texto_escpos(
		f"Entrada      : {_formatear_fecha_ddmmaaaa(fecha_entrada)} {_formatear_hora_12h(fecha_entrada)}\n"
	)
	buffer += _texto_escpos(
		f"Salida       : {_formatear_fecha_ddmmaaaa(fecha_salida)} {_formatear_hora_12h(fecha_salida)}\n"
	)
	buffer += _texto_escpos(f"Tiempo total : {minutos_estadia} min\n")
	buffer += _texto_escpos(f"Total pagado : ${total_pagado:.2f}\n")
	buffer += _texto_escpos(f"Metodo pago  : {metodo_pago}\n")
	buffer += _texto_escpos(f"Encargado       : {cajero}\n")
	_agregar_aviso_personalizado(buffer, app_config.AVISO_SALIDA)

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
	buffer += _texto_escpos("--------------------------------\n")

	buffer += align_left
	buffer += _texto_escpos(f"Placa        : {placa}\n")
	buffer += _texto_escpos(
		f"Entrada      : {_formatear_fecha_ddmmaaaa(fecha_entrada)} {_formatear_hora_12h(fecha_entrada)}\n"
	)
	buffer += _texto_escpos(f"Tarifa       : {tarifa_nombre}\n")
	buffer += _texto_escpos(f"Encargado       : {cajero}\n")
	_agregar_aviso_personalizado(buffer, app_config.AVISO_ENTRADA)
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


def generar_ticket_corte_caja(
	folio: str,
	turno_id: int,
	fecha_inicio: datetime,
	fecha_fin: datetime,
	detalle_movimientos: Sequence[dict],
	total_calculado: float,
	total_declarado: float,
	diferencia: float,
	total_efectivo: float,
	total_tarjeta: float,
	cajero: str = "SISTEMA",
) -> bytes:
	"""Genera el ticket ESC/POS del corte de caja con desglose del turno."""

	esc = b"\x1b"
	gs = b"\x1d"

	init = esc + b"@"
	align_left = esc + b"a" + b"\x00"
	align_center = esc + b"a" + b"\x01"
	bold_on = esc + b"E" + b"\x01"
	bold_off = esc + b"E" + b"\x00"
	line_feed_3 = esc + b"d" + b"\x03"
	cut_full = gs + b"V" + b"\x00"

	buffer = bytearray()
	buffer += init
	buffer += align_center
	buffer += bold_on
	buffer += _texto_escpos("CORTE DE CAJA\n")
	buffer += bold_off
	buffer += _texto_escpos("--------------------------------\n")
	buffer += align_left
	buffer += _texto_escpos(f"Folio        : {folio}\n")
	buffer += _texto_escpos(f"Turno        : {turno_id}\n")
	buffer += _texto_escpos(f"Inicio       : {_formatear_fecha_ddmmaaaa(fecha_inicio)} {_formatear_hora_12h(fecha_inicio)}\n")
	buffer += _texto_escpos(f"Fin          : {_formatear_fecha_ddmmaaaa(fecha_fin)} {_formatear_hora_12h(fecha_fin)}\n")
	buffer += _texto_escpos(f"Cajero       : {cajero}\n")
	buffer += _texto_escpos("--------------------------------\n")

	for indice, movimiento in enumerate(detalle_movimientos, start=1):
		placa = str(movimiento.get("placa", "SINPLACA"))
		entrada = movimiento.get("entrada")
		salida = movimiento.get("salida")
		importe = float(movimiento.get("importe", 0) or 0)
		metodo_pago = str(movimiento.get("metodo_pago", "efectivo"))
		pagado = bool(movimiento.get("pagado", False))

		buffer += bold_on
		buffer += _texto_escpos(f"{indice:02d}. {placa}\n")
		buffer += bold_off
		if isinstance(entrada, datetime):
			buffer += _texto_escpos(f"  Entrada : {_formatear_fecha_ddmmaaaa(entrada)} {_formatear_hora_12h(entrada)}\n")
		if isinstance(salida, datetime):
			buffer += _texto_escpos(f"  Salida  : {_formatear_fecha_ddmmaaaa(salida)} {_formatear_hora_12h(salida)}\n")
		buffer += _texto_escpos(f"  Pago    : {metodo_pago}{' / pagado' if pagado else ' / pendiente'}\n")
		buffer += _texto_escpos(f"  Importe : ${importe:.2f}\n")

	buffer += _texto_escpos("--------------------------------\n")
	buffer += bold_on
	buffer += _texto_escpos(f"Total calculado : ${total_calculado:.2f}\n")
	buffer += _texto_escpos(f"Total declarado : ${total_declarado:.2f}\n")
	buffer += _texto_escpos(f"Diferencia      : ${diferencia:.2f}\n")
	buffer += _texto_escpos(f"Total efectivo  : ${total_efectivo:.2f}\n")
	buffer += _texto_escpos(f"Total tarjeta   : ${total_tarjeta:.2f}\n")
	buffer += bold_off
	buffer += _texto_escpos("--------------------------------\n")
	buffer += _texto_escpos("Corte generado correctamente\n")
	buffer += _texto_escpos("\n")
	buffer += _texto_escpos("\n")
	buffer += line_feed_3
	buffer += cut_full

	return bytes(buffer)
