import json
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Sequence

from core.cortes_config import load_cortes_config
from database import SessionLocal
from models.usuario import Usuario
from printer.corte_pdf import generar_pdf_corte_caja

logger = logging.getLogger(__name__)


def _is_admin_role(raw_role: str | None) -> bool:
    if not raw_role:
        return False

    role_data = raw_role
    if isinstance(raw_role, str):
        try:
            role_data = json.loads(raw_role)
        except (ValueError, TypeError):
            return False

    return isinstance(role_data, dict) and bool(role_data.get("admin", False))


def _get_admin_emails() -> list[str]:
    db = SessionLocal()
    try:
        users = db.query(Usuario).all()
        emails: list[str] = []
        for user in users:
            if not _is_admin_role(getattr(user, "rol", None)):
                continue
            email = (getattr(user, "email", "") or "").strip().lower()
            if email:
                emails.append(email)
        return sorted(set(emails))
    finally:
        db.close()


def _build_subject(template: str, corte_id: int, turno_id: int, fecha_inicio: datetime, fecha_fin: datetime) -> str:
    return template.format(
        corte_id=corte_id,
        turno_id=turno_id,
        fecha_inicio=fecha_inicio.strftime("%d/%m/%Y %I:%M:%S %p"),
        fecha_fin=fecha_fin.strftime("%d/%m/%Y %I:%M:%S %p"),
    )


def send_corte_report_email_task(
    *,
    corte_id: int,
    turno_id: int,
    cajero: str,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    total_calculado: float,
    total_declarado: float,
    diferencia: float,
    total_efectivo: float,
    total_tarjeta: float,
    movimientos: Sequence[dict],
) -> None:
    try:
        config = load_cortes_config()
        if not config.get("AUTOSEND_REPORT", False):
            return

        admin_emails = _get_admin_emails()
        if not admin_emails:
            logger.warning("Corte %s: AUTOSEND_REPORT activo pero no hay admins con email configurado", corte_id)
            return

        smtp_host = config.get("SMTP_HOST", "")
        smtp_port = int(config.get("SMTP_PORT", 587))
        smtp_username = config.get("SMTP_USERNAME", "")
        smtp_password = config.get("SMTP_PASSWORD", "")
        smtp_use_tls = bool(config.get("SMTP_USE_TLS", True))
        smtp_timeout = int(config.get("SMTP_TIMEOUT_SECONDS", 20))

        if not smtp_host or not smtp_username or not smtp_password:
            logger.warning("Corte %s: configuracion SMTP incompleta en config_cortes.json", corte_id)
            return

        pdf_bytes = generar_pdf_corte_caja(
            corte_id=corte_id,
            turno_id=turno_id,
            cajero=cajero,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            total_calculado=total_calculado,
            total_declarado=total_declarado,
            diferencia=diferencia,
            total_efectivo=total_efectivo,
            total_tarjeta=total_tarjeta,
            movimientos=movimientos,
        )

        subject_template = config.get("REPORT_SUBJECT_TEMPLATE", "Corte de caja #{corte_id} - Turno #{turno_id}")
        subject = _build_subject(subject_template, corte_id, turno_id, fecha_inicio, fecha_fin)

        from_name = config.get("REPORT_FROM_NAME", "Sistema de Estacionamiento")
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{smtp_username}>"
        msg["To"] = ", ".join(admin_emails)
        msg.set_content(
            "Se adjunta el reporte PDF del corte de caja.\n\n"
            f"Corte: {corte_id}\n"
            f"Turno: {turno_id}\n"
            f"Periodo: {fecha_inicio.strftime('%d/%m/%Y %I:%M:%S %p')} - {fecha_fin.strftime('%d/%m/%Y %I:%M:%S %p')}\n"
        )

        filename = f"corte_{turno_id}_{corte_id}.pdf"
        msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)

        with smtplib.SMTP(host=smtp_host, port=smtp_port, timeout=smtp_timeout) as server:
            if smtp_use_tls:
                server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        logger.info("Corte %s: reporte enviado a admins (%s)", corte_id, ", ".join(admin_emails))
    except Exception as exc:
        logger.exception("Corte %s: error enviando reporte por correo: %s", corte_id, exc)
