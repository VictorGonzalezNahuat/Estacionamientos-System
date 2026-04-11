#!/usr/bin/env python3
"""Cliente de terminal para integrarse con /terminal/pluma en backend FastAPI.

Comportamiento:
- Hace polling de estado cada 3 segundos.
- Espera Enter en consola.
- Si el modo es active, solicita ticket binario al backend.
- Simula impresion guardando los bytes en la carpeta printed/.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import ctypes
import queue
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from urllib import error, request

try:
    from PIL import Image  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    Image = None


STATUS_PATH = "/terminal/pluma/status"
ENTRY_TICKET_PATH = "/terminal/pluma/entry-ticket"
SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass
class AppConfig:
    backend_base_url: str
    terminal_api_key: str
    poll_interval_seconds: float = 3.0
    request_timeout_seconds: float = 10.0
    printed_dir: Path = Path("printed")


class BackendError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class BackendClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _build_url(self, path: str) -> str:
        return f"{self.config.backend_base_url.rstrip('/')}{path}"

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Terminal-Api-Key": self.config.terminal_api_key,
            "Accept": "application/json",
        }

    def get_status(self) -> Dict[str, Any]:
        req = request.Request(
            self._build_url(STATUS_PATH),
            headers=self._headers(),
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=self.config.request_timeout_seconds) as resp:
                raw = resp.read()
                return json.loads(raw.decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise BackendError("Error HTTP consultando status", status_code=exc.code, body=body) from exc
        except error.URLError as exc:
            raise BackendError(f"No se pudo consultar status: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise BackendError(f"Respuesta invalida en status: {exc}") from exc

    def create_entry_ticket(self) -> Tuple[bytes, Dict[str, str], int]:
        headers = self._headers()
        headers["Accept"] = "application/octet-stream"
        req = request.Request(
            self._build_url(ENTRY_TICKET_PATH),
            data=b"{}",
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.config.request_timeout_seconds) as resp:
                payload = resp.read()
                response_headers = {k: v for k, v in resp.headers.items()}
                return payload, response_headers, resp.status
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise BackendError("Error HTTP creando entrada", status_code=exc.code, body=body) from exc
        except error.URLError as exc:
            raise BackendError(f"No se pudo crear la entrada: {exc.reason}") from exc


class FileSpoolOutput:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_ticket(self, binary_payload: bytes, prefix: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{prefix}_{timestamp}.bin"
        path = self.output_dir / filename
        path.write_bytes(binary_payload)
        return str(path)


class WindowsDefaultRawPrinter:
    _winspool: Any

    class _DOC_INFO_1(ctypes.Structure):
        _fields_ = [
            ("pDocName", ctypes.c_wchar_p),
            ("pOutputFile", ctypes.c_wchar_p),
            ("pDatatype", ctypes.c_wchar_p),
        ]

    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError("WindowsDefaultRawPrinter solo esta disponible en Windows")
        self._winspool: Any = ctypes.WinDLL("winspool.drv", use_last_error=True)

    @staticmethod
    def _raise_winspool_error(action: str) -> None:
        raise OSError(f"Error de impresion Windows en {action}")

    def _get_default_printer_name(self) -> str:
        needed = ctypes.c_uint32(0)
        self._winspool.GetDefaultPrinterW(None, ctypes.byref(needed))
        if needed.value == 0:
            raise OSError("No hay impresora predeterminada configurada")
        buffer = ctypes.create_unicode_buffer(needed.value)
        ok = self._winspool.GetDefaultPrinterW(buffer, ctypes.byref(needed))
        if not ok:
            self._raise_winspool_error("GetDefaultPrinterW")
        return buffer.value

    def print_ticket(self, binary_payload: bytes, doc_name: str) -> str:
        printer_name = self._get_default_printer_name()
        handle = ctypes.c_void_p()

        opened = self._winspool.OpenPrinterW(printer_name, ctypes.byref(handle), None)
        if not opened:
            self._raise_winspool_error("OpenPrinterW")

        started_doc = False
        started_page = False
        try:
            doc_info = self._DOC_INFO_1(doc_name, None, "RAW")
            job_id = self._winspool.StartDocPrinterW(handle, 1, ctypes.byref(doc_info))
            if job_id == 0:
                self._raise_winspool_error("StartDocPrinterW")
            started_doc = True

            if not self._winspool.StartPagePrinter(handle):
                self._raise_winspool_error("StartPagePrinter")
            started_page = True

            written = ctypes.c_uint32(0)
            data = ctypes.create_string_buffer(binary_payload)
            if not self._winspool.WritePrinter(handle, data, len(binary_payload), ctypes.byref(written)):
                self._raise_winspool_error("WritePrinter")
            if written.value != len(binary_payload):
                raise OSError(
                    "No se enviaron todos los bytes a la impresora "
                    f"({written.value}/{len(binary_payload)})"
                )

            if not self._winspool.EndPagePrinter(handle):
                self._raise_winspool_error("EndPagePrinter")
            started_page = False

            if not self._winspool.EndDocPrinter(handle):
                self._raise_winspool_error("EndDocPrinter")
            started_doc = False

            return f"impresora={printer_name} job_id={job_id}"
        finally:
            if started_page:
                self._winspool.EndPagePrinter(handle)
            if started_doc:
                self._winspool.EndDocPrinter(handle)
            self._winspool.ClosePrinter(handle)


class WindowsGlobalEnterListener:
    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012
    VK_RETURN = 0x0D
    HOTKEY_ID = 1
    _on_enter: Callable[[], None]
    _user32: Any
    _kernel32: Any
    _thread: Optional[threading.Thread]
    _thread_id: int
    _stop_event: threading.Event
    _start_event: threading.Event
    _start_error: Optional[str]

    class _MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("message", ctypes.c_uint),
            ("wParam", ctypes.c_size_t),
            ("lParam", ctypes.c_ssize_t),
            ("time", ctypes.c_uint32),
            ("pt_x", ctypes.c_long),
            ("pt_y", ctypes.c_long),
            ("lPrivate", ctypes.c_uint32),
        ]

    def __init__(self, on_enter: Callable[[], None]) -> None:
        if os.name != "nt":
            raise OSError("WindowsGlobalEnterListener solo esta disponible en Windows")
        self._on_enter = on_enter
        self._user32: Any = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32: Any = ctypes.WinDLL("kernel32", use_last_error=True)
        self._thread: Optional[threading.Thread] = None
        self._thread_id = 0
        self._stop_event = threading.Event()
        self._start_event = threading.Event()
        self._start_error: Optional[str] = None

    def _message_loop(self) -> None:
        self._thread_id = int(self._kernel32.GetCurrentThreadId())
        ok = self._user32.RegisterHotKey(None, self.HOTKEY_ID, 0, self.VK_RETURN)
        if not ok:
            self._start_error = "No se pudo registrar hotkey global Enter"
            self._start_event.set()
            return

        self._start_event.set()
        msg = self._MSG()
        try:
            while not self._stop_event.is_set():
                result = self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result <= 0:
                    break
                if msg.message == self.WM_HOTKEY and msg.wParam == self.HOTKEY_ID:
                    self._on_enter()
                self._user32.TranslateMessage(ctypes.byref(msg))
                self._user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self._user32.UnregisterHotKey(None, self.HOTKEY_ID)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._message_loop, name="global-enter-listener", daemon=True)
        self._thread.start()
        self._start_event.wait(timeout=2.0)
        if self._start_error:
            raise OSError(self._start_error)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread_id:
            self._user32.PostThreadMessageW(self._thread_id, self.WM_QUIT, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=2.0)


class TicketOutput:
    def __init__(self, printed_dir: Path) -> None:
        self._file_spool = FileSpoolOutput(printed_dir)
        self._win_printer: Optional[WindowsDefaultRawPrinter] = None
        self._asset_dir = SCRIPT_DIR / "assets"
        self._header_cache: Dict[str, bytes] = {}
        self._warned_missing_pillow = False
        if os.name == "nt":
            try:
                self._win_printer = WindowsDefaultRawPrinter()
            except Exception as exc:  # noqa: BLE001
                print(
                    "[WARN] No se pudo inicializar impresion Windows. "
                    f"Se usara fallback a archivo. detalle={exc}"
                )

    def _build_escpos_image_header(self, image_path: Path) -> bytes:
        if Image is None:
            if not self._warned_missing_pillow:
                print("[WARN] Pillow no esta instalado. Los encabezados PNG no se imprimiran.")
                self._warned_missing_pillow = True
            return b""
        if not image_path.exists():
            print(f"[WARN] No existe imagen de encabezado: {image_path}")
            return b""

        cache_key = str(image_path)
        if cache_key in self._header_cache:
            return self._header_cache[cache_key]

        try:
            img = Image.open(image_path).convert("L")
            max_width = 384
            if img.width > max_width:
                new_height = max(1, int(img.height * (max_width / float(img.width))))
                img = img.resize((max_width, new_height))

            bw = img.point(lambda p: 0 if p < 180 else 255, mode="1")
            width = bw.width
            height = bw.height
            width_bytes = (width + 7) // 8

            raster = bytearray()
            pixels = bw.load()
            for y in range(height):
                for xb in range(width_bytes):
                    byte = 0
                    for bit in range(8):
                        x = xb * 8 + bit
                        if x < width and pixels[x, y] == 0:
                            byte |= 1 << (7 - bit)
                    raster.append(byte)

            x_l = width_bytes & 0xFF
            x_h = (width_bytes >> 8) & 0xFF
            y_l = height & 0xFF
            y_h = (height >> 8) & 0xFF
            escpos = b"\x1dv0\x00" + bytes([x_l, x_h, y_l, y_h]) + bytes(raster) + b"\n"
            self._header_cache[cache_key] = escpos
            return escpos
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] No se pudo procesar encabezado PNG {image_path}: {exc}")
            return b""

    def build_entry_payload(self, payload: bytes) -> bytes:
        header = self._build_escpos_image_header(self._asset_dir / "encabezado_entrada.png")
        return header + payload

    def build_status_payload(self, status: Dict[str, Any]) -> bytes:
        header = self._build_escpos_image_header(self._asset_dir / "encabezado_printer.png")
        mode = str(status.get("mode", "unknown")).lower()
        turno = status.get("turno")

        turno_label = "SIN TURNO"
        if isinstance(turno, dict):
            for key in ("numero", "nro", "id", "turno_id"):
                value = turno.get(key)
                if value is not None:
                    turno_label = str(value)
                    break
        elif turno is not None:
            turno_label = str(turno)

        if mode == "active":
            main_line = f"TURNO {turno_label} ACTIVO"
            sub_line = "PLUMA CONFIGURADA Y ESPERANDO VEHICULOS"
        elif mode == "inactive":
            main_line = "PLUMA INACTIVA"
            sub_line = "NO RECIBE VEHICULOS"
        else:
            main_line = "ESTADO DE PLUMA"
            sub_line = f"MODO {mode.upper()}"

        # ESC/POS: centrar + negrita + doble tamano para linea principal.
        body = (
            b"\x1ba\x01"
            + b"\x1bE\x01"
            + b"\x1d!\x11"
            + main_line.encode("utf-8")
            + b"\n"
            + b"\x1d!\x00"
            + b"\x1bE\x00"
            + sub_line.encode("utf-8")
            + b"\n"
            + b"\x1ba\x00"
            + b"\n"
            + b"\n"
        )
        return header + body + b"\n\n\n\x1dV\x00"

    def write_ticket(self, binary_payload: bytes, prefix: str) -> str:
        if self._win_printer is not None:
            try:
                return self._win_printer.print_ticket(binary_payload, doc_name=prefix)
            except Exception as exc:  # noqa: BLE001
                print(
                    "[WARN] Fallo imprimiendo en impresora predeterminada. "
                    f"Se guarda en archivo. detalle={exc}"
                )
        return self._file_spool.write_ticket(binary_payload, prefix)

    def write_status_notice(self, status: Dict[str, Any]) -> str:
        mode = str(status.get("mode", "unknown")).lower()
        payload = self.build_status_payload(status)
        return self.write_ticket(payload, f"status_{mode}")


class TerminalPlumaApp:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.backend = BackendClient(config)
        self.spool = TicketOutput(config.printed_dir)

        self._status_lock = threading.Lock()
        self._status: Dict[str, Any] = {
            "mode": "unknown",
            "status_version": None,
            "message": "Sin datos iniciales",
            "turno": None,
        }
        self._enter_events: "queue.Queue[None]" = queue.Queue()
        self._global_enter_listener: Optional[WindowsGlobalEnterListener] = None
        self._stop_event = threading.Event()

    def _queue_enter_event(self) -> None:
        self._enter_events.put(None)

    def _set_status(self, status: Dict[str, Any]) -> None:
        with self._status_lock:
            self._status = status

    def _get_status(self) -> Dict[str, Any]:
        with self._status_lock:
            return dict(self._status)

    def _initial_sync(self) -> None:
        status = self.backend.get_status()
        self._set_status(status)
        notice_path = self.spool.write_status_notice(status)
        print(f"[INIT] Estado inicial: {status.get('mode')} | aviso guardado en {notice_path}")

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                latest = self.backend.get_status()
                current = self._get_status()
                if latest.get("status_version") != current.get("status_version"):
                    notice_path = self.spool.write_status_notice(latest)
                    print(
                        "[STATUS] Cambio detectado "
                        f"{current.get('status_version')} -> {latest.get('status_version')} "
                        f"| aviso guardado en {notice_path}"
                    )
                self._set_status(latest)
            except BackendError as exc:
                detail = f" (HTTP {exc.status_code})" if exc.status_code else ""
                print(f"[ERROR] Polling status fallido{detail}: {exc}")
                if exc.body:
                    print(f"[ERROR] Detalle backend: {exc.body}")
            self._stop_event.wait(self.config.poll_interval_seconds)

    def _handle_enter_event(self) -> None:
        status = self._get_status()
        mode = str(status.get("mode", "unknown")).lower()

        if mode != "active":
            print(
                "[BLOCKED] Enter recibido, pero la pluma no esta activa. "
                f"mode={mode} mensaje={status.get('message')}"
            )
            return

        try:
            payload, headers, http_status = self.backend.create_entry_ticket()
            plate = headers.get("X-Entry-Plate", "SIN-PLACA")
            entry_id = headers.get("X-Entry-Id", "N/A")
            turno_id = headers.get("X-Turno-Id", "N/A")
            payload_with_header = self.spool.build_entry_payload(payload)
            out_file = self.spool.write_ticket(payload_with_header, f"entry_{plate}")
            print(
                f"[OK] Ticket recibido HTTP {http_status}. "
                f"placa={plate} entry_id={entry_id} turno_id={turno_id} "
                f"simulado en {out_file}"
            )
        except BackendError as exc:
            detail = f" (HTTP {exc.status_code})" if exc.status_code else ""
            print(f"[ERROR] No se pudo crear/imprimir ticket{detail}: {exc}")
            if exc.body:
                print(f"[ERROR] Respuesta backend: {exc.body}")

    def run(self) -> int:
        try:
            self._initial_sync()
        except BackendError as exc:
            detail = f" (HTTP {exc.status_code})" if exc.status_code else ""
            print(f"[FATAL] No se pudo iniciar por fallo en status{detail}: {exc}")
            if exc.body:
                print(f"[FATAL] Respuesta backend: {exc.body}")
            return 1

        poller = threading.Thread(target=self._poll_loop, name="status-poller", daemon=True)
        poller.start()

        use_global_enter = False
        if os.name == "nt":
            try:
                self._global_enter_listener = WindowsGlobalEnterListener(self._queue_enter_event)
                self._global_enter_listener.start()
                use_global_enter = True
                print("[READY] Enter global activo (aunque la ventana no tenga foco). Ctrl+C para salir.")
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] No se pudo activar Enter global. Se usa consola normal. detalle={exc}")

        if not use_global_enter:
            print("[READY] Presiona Enter para solicitar ticket. Ctrl+C para salir.")

        try:
            if use_global_enter:
                while True:
                    try:
                        _ = self._enter_events.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    self._handle_enter_event()
            else:
                while True:
                    _ = input()
                    self._handle_enter_event()
        except KeyboardInterrupt:
            print("\n[STOP] Finalizando programa...")
        except EOFError:
            print("\n[STOP] Entrada cerrada. Finalizando programa...")
        finally:
            self._stop_event.set()
            if self._global_enter_listener is not None:
                self._global_enter_listener.stop()
            poller.join(timeout=2.0)

        return 0


def _load_dotenv_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_config() -> AppConfig:
    file_env = _load_dotenv_file(SCRIPT_DIR / ".env")

    def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(key) or file_env.get(key) or default

    backend_base_url = get_setting("BACKEND_BASE_URL", "http://127.0.0.1:8000")
    api_key = get_setting("TERMINAL_API_KEY")
    poll_interval = float(get_setting("POLL_INTERVAL_SECONDS", "3") or "3")
    timeout = float(get_setting("REQUEST_TIMEOUT_SECONDS", "10") or "10")
    printed_dir_raw = get_setting("PRINTED_DIR", "printed") or "printed"
    printed_dir = Path(printed_dir_raw)
    if not printed_dir.is_absolute():
        printed_dir = SCRIPT_DIR / printed_dir

    if not api_key:
        raise ValueError("Falta TERMINAL_API_KEY en entorno o .env")
    if not backend_base_url:
        raise ValueError("Falta BACKEND_BASE_URL en entorno o .env")

    return AppConfig(
        backend_base_url=backend_base_url,
        terminal_api_key=api_key,
        poll_interval_seconds=poll_interval,
        request_timeout_seconds=timeout,
        printed_dir=printed_dir,
    )


def main() -> int:
    try:
        config = load_config()
    except Exception as exc:  # noqa: BLE001
        print(f"[FATAL] Configuracion invalida: {exc}")
        return 1

    app = TerminalPlumaApp(config)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
