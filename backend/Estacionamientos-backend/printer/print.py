import os
import json
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import quote

from core import config as app_config
import escpos.printer as escpos_printer
from escpos.printer import Network


_PRINTER_DIR = Path(__file__).resolve().parent
_PRINTER_CONFIG_PATH = _PRINTER_DIR.parent / "config" / "config_printer.json"
_ENCABEZADO_ENTRADA = _PRINTER_DIR / "encabezado_entrada.png"
_ENCABEZADO_SALIDA = _PRINTER_DIR / "encabezado_salida.png"
_ANCHO_AVISO_80MM = 42
_PRINTER_METHOD_NETWORK = "NETWORK"
_PRINTER_METHOD_USB = "USB"


def _default_printer_config() -> dict:
	return {
		"method": _PRINTER_METHOD_NETWORK,
		"network": {
			"host": os.getenv("PRINTER_HOST", "192.168.1.130").strip(),
			"port": int(os.getenv("PRINTER_PORT", "9100")),
			"timeout": int(os.getenv("PRINTER_TIMEOUT", "10")),
		},
		"usb": {
			"mode": "WINDOWS_DEFAULT",
			"printer_name": "",
		},
	}


def _load_printer_config() -> dict:
	default_cfg = _default_printer_config()

	if not _PRINTER_CONFIG_PATH.exists():
		return default_cfg

	try:
		raw_text = _PRINTER_CONFIG_PATH.read_text(encoding="utf-8").strip()
		if not raw_text:
			return default_cfg
		loaded = json.loads(raw_text)
		if not isinstance(loaded, dict):
			return default_cfg
	except Exception:
		return default_cfg

	method = str(loaded.get("method", default_cfg["method"])).strip().upper()
	if method not in {_PRINTER_METHOD_NETWORK, _PRINTER_METHOD_USB}:
		method = _PRINTER_METHOD_NETWORK

	network_candidate = loaded.get("network")
	usb_candidate = loaded.get("usb")
	network_loaded = network_candidate if isinstance(network_candidate, dict) else {}
	usb_loaded = usb_candidate if isinstance(usb_candidate, dict) else {}

	try:
		port = int(network_loaded.get("port", default_cfg["network"]["port"]))
	except (TypeError, ValueError):
		port = int(default_cfg["network"]["port"])

	try:
		timeout = int(network_loaded.get("timeout", default_cfg["network"]["timeout"]))
	except (TypeError, ValueError):
		timeout = int(default_cfg["network"]["timeout"])

	host = str(network_loaded.get("host", default_cfg["network"]["host"]))
	printer_name = str(usb_loaded.get("printer_name", "") or "").strip()
	usb_mode = str(usb_loaded.get("mode", "WINDOWS_DEFAULT") or "WINDOWS_DEFAULT").strip().upper()

	return {
		"method": method,
		"network": {
			"host": host.strip(),
			"port": max(1, port),
			"timeout": max(1, timeout),
		},
		"usb": {
			"mode": usb_mode,
			"printer_name": printer_name,
		},
	}


def _save_printer_config(config_data: dict) -> None:
	_PRINTER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
	_PRINTER_CONFIG_PATH.write_text(
		json.dumps(config_data, ensure_ascii=True, indent=2) + "\n",
		encoding="utf-8",
	)


def get_printer_config_values() -> dict:
	"""Obtiene la configuracion actual de impresion desde config/config_printer.json."""
	return _load_printer_config()


def update_printer_config_values(updates: dict) -> dict:
	"""Actualiza parcialmente la configuracion de impresion y la persiste en config/config_printer.json."""
	if not isinstance(updates, dict):
		raise ValueError("Payload de configuracion de impresora invalido")

	current = _load_printer_config()
	method = current["method"]
	network = dict(current["network"])
	usb = dict(current["usb"])

	if "method" in updates:
		candidate_method = str(updates.get("method", "")).strip().upper()
		if candidate_method not in {_PRINTER_METHOD_NETWORK, _PRINTER_METHOD_USB}:
			raise ValueError("method debe ser NETWORK o USB")
		method = candidate_method

	if "network" in updates:
		network_updates = updates.get("network")
		if not isinstance(network_updates, dict):
			raise ValueError("network debe ser un objeto")

		if "host" in network_updates:
			host = str(network_updates.get("host", "")).strip()
			if not host:
				raise ValueError("network.host no puede estar vacio")
			network["host"] = host

		if "port" in network_updates:
			port_value = network_updates.get("port")
			if port_value is None:
				raise ValueError("network.port debe ser un entero")
			try:
				port = int(port_value)
			except (TypeError, ValueError):
				raise ValueError("network.port debe ser un entero")
			if port < 1 or port > 65535:
				raise ValueError("network.port debe estar entre 1 y 65535")
			network["port"] = port

		if "timeout" in network_updates:
			timeout_value = network_updates.get("timeout")
			if timeout_value is None:
				raise ValueError("network.timeout debe ser un entero")
			try:
				timeout = int(timeout_value)
			except (TypeError, ValueError):
				raise ValueError("network.timeout debe ser un entero")
			if timeout < 1:
				raise ValueError("network.timeout debe ser mayor o igual a 1")
			network["timeout"] = timeout

	if "usb" in updates:
		usb_updates = updates.get("usb")
		if not isinstance(usb_updates, dict):
			raise ValueError("usb debe ser un objeto")

		if "mode" in usb_updates:
			usb_mode = str(usb_updates.get("mode", "")).strip().upper()
			if usb_mode != "WINDOWS_DEFAULT":
				raise ValueError("usb.mode actualmente solo soporta WINDOWS_DEFAULT")
			usb["mode"] = usb_mode

		if "printer_name" in usb_updates:
			usb["printer_name"] = str(usb_updates.get("printer_name", "") or "").strip()

	new_data = {
		"method": method,
		"network": {
			"host": str(network.get("host", "")).strip(),
			"port": int(network.get("port", 9100)),
			"timeout": int(network.get("timeout", 10)),
		},
		"usb": {
			"mode": str(usb.get("mode", "WINDOWS_DEFAULT") or "WINDOWS_DEFAULT").strip().upper(),
			"printer_name": str(usb.get("printer_name", "") or "").strip(),
		},
	}

	_save_printer_config(new_data)
	return _load_printer_config()


def _imprimir_ticket_network(
	ticket_bytes: bytes,
	copias: int,
	tipo_ticket: str,
	network_cfg: dict,
) -> tuple[bool, str]:
	host = str(network_cfg.get("host", "")).strip()
	port = int(network_cfg.get("port", 9100))
	timeout = int(network_cfg.get("timeout", 10))
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
		return True, f"Ticket enviado a impresora ({copias} copia(s)) por RED"
	except Exception as exc:
		return False, f"No se pudo imprimir en red: {exc}"
	finally:
		if impresora is not None:
			try:
				impresora.close()
			except Exception:
				pass


def _imprimir_tickets_network(
	ticket_lote: Sequence[bytes],
	tipo_ticket: str,
	network_cfg: dict,
) -> tuple[bool, str]:
	host = str(network_cfg.get("host", "")).strip()
	port = int(network_cfg.get("port", 9100))
	timeout = int(network_cfg.get("timeout", 10))

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
		return True, f"Tickets enviados a impresora ({len(lote)} ticket(s)) por RED"
	except Exception as exc:
		return False, f"No se pudo imprimir en red: {exc}"
	finally:
		if impresora is not None:
			try:
				impresora.close()
			except Exception:
				pass


def _build_usb_windows_printer(usb_cfg: dict):
	if os.name != "nt":
		raise RuntimeError("La impresion USB tipo WINDOWS_DEFAULT solo esta soportada en Windows")

	win32_raw_cls = getattr(escpos_printer, "Win32Raw", None)
	if win32_raw_cls is None:
		raise RuntimeError("No esta disponible Win32Raw. Verifique pywin32 en el entorno de Windows")

	printer_name = str(usb_cfg.get("printer_name", "") or "").strip() or None
	return win32_raw_cls(printer_name=printer_name)


def _imprimir_ticket_usb_windows(
	ticket_bytes: bytes,
	copias: int,
	tipo_ticket: str,
	usb_cfg: dict,
) -> tuple[bool, str]:
	copias = max(1, int(copias))
	impresora = None
	try:
		impresora = _build_usb_windows_printer(usb_cfg)
		impresora.open(job_name="estacionamientos-ticket")
		for _ in range(copias):
			encabezado_path = _obtener_encabezado_ticket(tipo_ticket)
			_imprimir_encabezado_ticket(impresora, encabezado_path)
			impresora._raw(ticket_bytes)
		return True, f"Ticket enviado a impresora ({copias} copia(s)) por USB"
	except Exception as exc:
		return False, f"No se pudo imprimir por USB Windows: {exc}"
	finally:
		if impresora is not None:
			try:
				impresora.close()
			except Exception:
				pass


def _imprimir_tickets_usb_windows(
	ticket_lote: Sequence[bytes],
	tipo_ticket: str,
	usb_cfg: dict,
) -> tuple[bool, str]:
	lote = [tb for tb in ticket_lote if tb]
	if not lote:
		return False, "No hay tickets para imprimir"

	impresora = None
	try:
		impresora = _build_usb_windows_printer(usb_cfg)
		impresora.open(job_name="estacionamientos-ticket-lote")
		encabezado_path = _obtener_encabezado_ticket(tipo_ticket)
		for ticket_bytes in lote:
			_imprimir_encabezado_ticket(impresora, encabezado_path)
			impresora._raw(ticket_bytes)
		return True, f"Tickets enviados a impresora ({len(lote)} ticket(s)) por USB"
	except Exception as exc:
		return False, f"No se pudo imprimir por USB Windows: {exc}"
	finally:
		if impresora is not None:
			try:
				impresora.close()
			except Exception:
				pass


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
	config = _load_printer_config()
	return _imprimir_ticket_network(ticket_bytes, copias, tipo_ticket, config["network"])


def imprimir_tickets_red(ticket_lote: Sequence[bytes], tipo_ticket: str = "salida") -> tuple[bool, str]:
	"""Imprime varios tickets en una sola sesion de impresora para mayor confiabilidad."""
	config = _load_printer_config()
	return _imprimir_tickets_network(ticket_lote, tipo_ticket, config["network"])


def imprimir_ticket(ticket_bytes: bytes, copias: int = 1, tipo_ticket: str = "salida") -> tuple[bool, str]:
	"""Imprime un ticket usando el metodo configurado en config/config_printer.json."""
	config = _load_printer_config()
	method = config["method"]

	if method == _PRINTER_METHOD_USB:
		return _imprimir_ticket_usb_windows(ticket_bytes, copias, tipo_ticket, config["usb"])

	return _imprimir_ticket_network(ticket_bytes, copias, tipo_ticket, config["network"])


def imprimir_tickets(ticket_lote: Sequence[bytes], tipo_ticket: str = "salida") -> tuple[bool, str]:
	"""Imprime varios tickets usando el metodo configurado en config/config_printer.json."""
	config = _load_printer_config()
	method = config["method"]

	if method == _PRINTER_METHOD_USB:
		return _imprimir_tickets_usb_windows(ticket_lote, tipo_ticket, config["usb"])

	return _imprimir_tickets_network(ticket_lote, tipo_ticket, config["network"])


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
	leyenda_reimpresion: Optional[str] = None,
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
	buffer += _texto_escpos(f"Folio        : {folio}\n")
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
	if leyenda_reimpresion:
		buffer += _texto_escpos(f"{leyenda_reimpresion}\n")
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
	leyenda_reimpresion: Optional[str] = None,
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
	if leyenda_reimpresion:
		buffer += _texto_escpos(f"{leyenda_reimpresion}\n")
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
