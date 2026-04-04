from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


_PRINTER_DIR = Path(__file__).resolve().parent
_LOGO_PATH = _PRINTER_DIR / "pdf" / "logo.png"

_HEADER_BG = colors.HexColor("#1F2937")
_HEADER_TEXT = colors.white
_TITLE_TEXT = colors.HexColor("#111827")
_TEXT = colors.HexColor("#111827")
_MUTED = colors.HexColor("#4B5563")
_BORDER = colors.HexColor("#D1D5DB")
_ROW_ALT = colors.HexColor("#F9FAFB")
_SUCCESS = colors.HexColor("#166534")
_DANGER = colors.HexColor("#B91C1C")
_ACCENT_CALCULADO_BG = colors.HexColor("#DBEAFE")
_ACCENT_DECLARADO_BG = colors.HexColor("#E0F2FE")
_ACCENT_EFECTIVO_BG = colors.HexColor("#FEF3C7")
_ACCENT_TARJETA_BG = colors.HexColor("#DBEAFE")
_IMPORTE_BG = colors.HexColor("#DCFCE7")
_IMPORTE_TEXT = colors.HexColor("#166534")


def _money(value: float | Decimal) -> str:
    return f"${float(value):,.2f}"


def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "-"
    return dt.strftime("%d/%m/%Y %I:%M:%S %p")


def _fit_text(pdf: canvas.Canvas, text: str, font_name: str, font_size: float, max_width: float) -> str:
    value = (text or "-").strip()
    if pdf.stringWidth(value, font_name, font_size) <= max_width:
        return value

    ellipsis = "..."
    available_width = max_width - pdf.stringWidth(ellipsis, font_name, font_size)
    if available_width <= 0:
        return ellipsis

    while value and pdf.stringWidth(value, font_name, font_size) > available_width:
        value = value[:-1]
    return f"{value}{ellipsis}"


def _draw_logo(pdf: canvas.Canvas, x: float, y: float, width_mm: float = 28, height_mm: float = 18) -> None:
    if not _LOGO_PATH.exists():
        return

    try:
        image = ImageReader(str(_LOGO_PATH))
        image_width, image_height = image.getSize()
        box_width = width_mm * mm
        box_height = height_mm * mm
        scale = min(box_width / image_width, box_height / image_height)
        draw_width = image_width * scale
        draw_height = image_height * scale
        pdf.drawImage(
            image,
            x + (box_width - draw_width) / 2,
            y + (box_height - draw_height) / 2,
            width=draw_width,
            height=draw_height,
            mask="auto",
            preserveAspectRatio=True,
        )
    except Exception:
        return


def _draw_page_base(pdf: canvas.Canvas, width: float, height: float) -> None:
    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)


def _draw_header(pdf: canvas.Canvas, width: float, height: float, *, corte_id: int, turno_id: int, cajero: str) -> float:
    margin_x = 16 * mm
    top_band_h = 13 * mm

    pdf.saveState()
    pdf.setFillColor(_HEADER_BG)
    pdf.rect(0, height - top_band_h, width, top_band_h, fill=1, stroke=0)
    pdf.setFillColor(_HEADER_TEXT)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(margin_x, height - 8.5 * mm, "REPORTE DE CORTE DE CAJA")
    pdf.restoreState()

    logo_y = height - 28 * mm
    _draw_logo(pdf, margin_x, logo_y, width_mm=22, height_mm=12)

    text_x = margin_x + 28 * mm
    pdf.setFillColor(_TITLE_TEXT)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(text_x, height - 18 * mm, "Resumen de Operacion")

    pdf.setFillColor(_MUTED)
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(text_x, height - 23.5 * mm, f"Corte: {corte_id}   Turno: {turno_id}   Encargado: {cajero or 'SISTEMA'}")

    pdf.setStrokeColor(_BORDER)
    pdf.setLineWidth(0.8)
    pdf.line(margin_x, height - 30 * mm, width - margin_x, height - 30 * mm)

    return height - 35 * mm


def _draw_footer(pdf: canvas.Canvas, width: float, page_number: int) -> None:
    margin_x = 16 * mm
    footer_y = 10 * mm

    pdf.saveState()
    pdf.setStrokeColor(_BORDER)
    pdf.setLineWidth(0.7)
    pdf.line(margin_x, footer_y + 6 * mm, width - margin_x, footer_y + 6 * mm)

    pdf.setFont("Helvetica", 7.6)
    pdf.setFillColor(_MUTED)
    pdf.drawString(margin_x, footer_y + 2 * mm, f"Generado: {_fmt_dt(datetime.now())}")
    pdf.drawRightString(width - margin_x, footer_y + 2 * mm, f"Página {page_number}")
    pdf.restoreState()


def _draw_section_title(pdf: canvas.Canvas, x: float, y: float, title: str) -> float:
    pdf.setFillColor(_TITLE_TEXT)
    pdf.setFont("Helvetica-Bold", 10.8)
    pdf.drawString(x, y, title)
    pdf.setStrokeColor(_BORDER)
    pdf.setLineWidth(0.8)
    pdf.line(x, y - 2.2 * mm, x + 55 * mm, y - 2.2 * mm)
    return y - 6 * mm


def _draw_simple_table(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    table_width: float,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    col_widths: Sequence[float],
    aligns: Sequence[str] | None = None,
    row_bg_colors: Sequence[colors.Color | None] | None = None,
    column_bg_colors: Sequence[colors.Color | None] | None = None,
    column_text_colors: Sequence[colors.Color | None] | None = None,
    row_height: float = 8.0 * mm,
) -> float:
    if aligns is None:
        aligns = ["left"] * len(headers)

    header_h = row_height
    table_height = header_h + (len(rows) * row_height)

    pdf.saveState()
    pdf.setFillColor(_HEADER_BG)
    pdf.rect(x, y - header_h, table_width, header_h, fill=1, stroke=0)
    pdf.setStrokeColor(_BORDER)
    pdf.setLineWidth(0.7)
    pdf.rect(x, y - table_height, table_width, table_height, fill=0, stroke=1)
    pdf.restoreState()

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 8.5)
    cursor_x = x
    for header, col_w in zip(headers, col_widths):
        pdf.drawString(cursor_x + 2 * mm, y - 5.3 * mm, header)
        cursor_x += col_w

    for row_index, row in enumerate(rows):
        row_top = y - header_h - (row_index * row_height)
        row_bottom = row_top - row_height

        row_bg = None
        if row_bg_colors and row_index < len(row_bg_colors):
            row_bg = row_bg_colors[row_index]

        if row_bg is not None:
            pdf.setFillColor(row_bg)
            pdf.rect(x, row_bottom, table_width, row_height, fill=1, stroke=0)
        elif row_index % 2 == 1:
            pdf.setFillColor(_ROW_ALT)
            pdf.rect(x, row_bottom, table_width, row_height, fill=1, stroke=0)

        pdf.setStrokeColor(_BORDER)
        pdf.setLineWidth(0.5)
        pdf.line(x, row_bottom, x + table_width, row_bottom)

        cursor_x = x
        for col_index, (value, col_w) in enumerate(zip(row, col_widths)):
            align = aligns[col_index] if col_index < len(aligns) else "left"
            max_text_w = col_w - 4 * mm
            value_fit = _fit_text(pdf, str(value), "Helvetica", 8.2, max_text_w)

            if column_bg_colors and col_index < len(column_bg_colors):
                col_bg = column_bg_colors[col_index]
                if col_bg is not None:
                    pdf.setFillColor(col_bg)
                    pdf.rect(cursor_x, row_bottom, col_w, row_height, fill=1, stroke=0)
                    pdf.setStrokeColor(_BORDER)
                    pdf.setLineWidth(0.4)
                    pdf.line(cursor_x, row_bottom, cursor_x + col_w, row_bottom)

            text_color = _TEXT
            if column_text_colors and col_index < len(column_text_colors) and column_text_colors[col_index] is not None:
                text_color = column_text_colors[col_index]
            pdf.setFillColor(text_color)
            pdf.setFont("Helvetica", 8.2)
            if align == "right":
                pdf.drawRightString(cursor_x + col_w - 2 * mm, row_bottom + 3.0 * mm, value_fit)
            else:
                pdf.drawString(cursor_x + 2 * mm, row_bottom + 3.0 * mm, value_fit)
            cursor_x += col_w

    cursor_x = x
    pdf.setStrokeColor(_BORDER)
    pdf.setLineWidth(0.5)
    for col_w in col_widths[:-1]:
        cursor_x += col_w
        pdf.line(cursor_x, y - table_height, cursor_x, y)

    return y - table_height - 2 * mm


def generar_pdf_corte_caja(
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
) -> bytes:
    """Genera un reporte PDF de corte de caja y retorna el archivo en bytes."""

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 16 * mm
    content_width = width - (2 * margin_x)
    min_content_y = 24 * mm
    page_number = 1

    _draw_page_base(pdf, width, height)
    y = _draw_header(pdf, width, height, corte_id=corte_id, turno_id=turno_id, cajero=cajero)

    y = _draw_section_title(pdf, margin_x, y, "Datos generales")

    datos_rows = [
        ["Corte ID", str(corte_id)],
        ["Turno ID", str(turno_id)],
        ["Encargado", cajero or "SISTEMA"],
        ["Fecha inicio", _fmt_dt(fecha_inicio)],
        ["Fecha fin", _fmt_dt(fecha_fin)],
    ]
    datos_col_widths = [48 * mm, content_width - 48 * mm]
    y = _draw_simple_table(
        pdf,
        margin_x,
        y,
        content_width,
        headers=["Campo", "Valor"],
        rows=datos_rows,
        col_widths=datos_col_widths,
        aligns=["left", "left"],
        row_height=8 * mm,
    )

    y -= 3 * mm
    y = _draw_section_title(pdf, margin_x, y, "Movimientos")
    movimientos_col_widths = [24 * mm, 40 * mm, 40 * mm, 46 * mm, content_width - (24 * mm + 40 * mm + 40 * mm + 46 * mm)]
    row_height = 8.5 * mm

    movimientos_rows: list[list[str]] = []
    for movimiento in movimientos:
        metodo = str(movimiento.get("metodo_pago") or "efectivo")
        if metodo == "tarjeta" and not bool(movimiento.get("pagado", False)):
            metodo = "tarjeta (pendiente)"
        movimientos_rows.append(
            [
                str(movimiento.get("placa") or "SINPLACA"),
                _fmt_dt(movimiento.get("entrada")),
                _fmt_dt(movimiento.get("salida")),
                metodo,
                _money(float(movimiento.get("importe") or 0.0)),
            ]
        )

    if not movimientos_rows:
        y = _draw_simple_table(
            pdf,
            margin_x,
            y,
            content_width,
            headers=["Placa", "Entrada", "Salida", "Metodo de pago", "Importe"],
            rows=[["-", "-", "-", "No hay movimientos registrados", "-"]],
            col_widths=movimientos_col_widths,
            aligns=["left", "left", "left", "left", "right"],
            row_height=row_height,
        )
    else:
        row_index = 0
        while row_index < len(movimientos_rows):
            available_h = y - min_content_y
            rows_fit = int((available_h - 2 * mm) // row_height) - 1

            if rows_fit <= 0:
                _draw_footer(pdf, width, page_number)
                pdf.showPage()
                page_number += 1
                _draw_page_base(pdf, width, height)
                y = _draw_header(pdf, width, height, corte_id=corte_id, turno_id=turno_id, cajero=cajero)
                y = _draw_section_title(pdf, margin_x, y, "Movimientos (continuacion)")
                continue

            chunk = movimientos_rows[row_index : row_index + rows_fit]

            y = _draw_simple_table(
                pdf,
                margin_x,
                y,
                content_width,
                headers=["Placa", "Entrada", "Salida", "Metodo de pago", "Importe"],
                rows=chunk,
                col_widths=movimientos_col_widths,
                aligns=["left", "left", "left", "left", "right"],
                column_bg_colors=[None, None, None, None, _IMPORTE_BG],
                column_text_colors=[None, None, None, None, _IMPORTE_TEXT],
                row_height=row_height,
            )
            row_index += len(chunk)

    totals_required = 44 * mm
    if y - totals_required < min_content_y:
        _draw_footer(pdf, width, page_number)
        pdf.showPage()
        page_number += 1
        _draw_page_base(pdf, width, height)
        y = _draw_header(pdf, width, height, corte_id=corte_id, turno_id=turno_id, cajero=cajero)

    y -= 3 * mm
    y = _draw_section_title(pdf, margin_x, y, "Resumen financiero")

    resumen_rows = [
        ["Total calculado", _money(total_calculado)],
        ["Total declarado", _money(total_declarado)],
        ["Diferencia", _money(diferencia)],
    ]

    resumen_top_y = y
    resumen_width = (content_width - 6 * mm) / 2
    composicion_x = margin_x + resumen_width + 6 * mm

    y_resumen = _draw_simple_table(
        pdf,
        margin_x,
        resumen_top_y,
        resumen_width,
        headers=["Concepto", "Monto"],
        rows=resumen_rows,
        col_widths=[resumen_width * 0.62, resumen_width * 0.38],
        aligns=["left", "right"],
        row_bg_colors=[_ACCENT_CALCULADO_BG, _ACCENT_DECLARADO_BG, None],
        row_height=8 * mm,
    )

    composicion_rows = [
        ["Efectivo", _money(total_efectivo)],
        ["Tarjeta", _money(total_tarjeta)],
    ]
    y_composicion = _draw_simple_table(
        pdf,
        composicion_x,
        resumen_top_y,
        resumen_width,
        headers=["Composicion", "Monto"],
        rows=composicion_rows,
        col_widths=[resumen_width * 0.62, resumen_width * 0.38],
        aligns=["left", "right"],
        row_bg_colors=[_ACCENT_EFECTIVO_BG, _ACCENT_TARJETA_BG],
        row_height=8 * mm,
    )

    diff_y = min(y_resumen, y_composicion) - 2 * mm
    pdf.setFillColor(_DANGER if abs(diferencia) >= 0.01 else _SUCCESS)
    pdf.setFont("Helvetica-Bold", 8.4)
    estado = "REVISAR DIFERENCIA" if abs(diferencia) >= 0.01 else "CUADRE CORRECTO"
    pdf.drawString(margin_x, diff_y, f"Estado de cuadre: {estado}")

    y = diff_y - 4 * mm

    _draw_footer(pdf, width, page_number)
    pdf.save()
    buffer.seek(0)
    return buffer.read()
