"""
Phase 2 — Report Service
PDF (reportlab) and Excel (openpyxl) generation.
Server-side, no browser dependencies.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
from typing import Optional, List
import os

from app.schemas.report import MealReportResponse


# ── PDF Generation ─────────────────────────────────────────────────────────────

def generate_meal_report_pdf(
    report: MealReportResponse,
    tenant_name: str,
    tenant_phone: Optional[str],
    tenant_address: Optional[str],
    tenant_tax_no: Optional[str],
    logo_path: Optional[str] = None,
) -> bytes:
    """
    Generates a professional Turkish-formatted PDF meal/ledger statement.
    Returns raw PDF bytes.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Yemek Raporu",
    )

    primary = HexColor("#1d4ed8")
    header_bg = HexColor("#1e3a5f")
    row_alt = HexColor("#f1f5f9")
    text_muted = HexColor("#64748b")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=14, textColor=primary, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "subtitle", fontName="Helvetica", fontSize=9, textColor=text_muted, spaceAfter=2
    )
    header_cell = ParagraphStyle(
        "header_cell", fontName="Helvetica-Bold", fontSize=8, textColor=white
    )
    normal_cell = ParagraphStyle("normal_cell", fontName="Helvetica", fontSize=8)

    def tr_decimal(v: Decimal) -> str:
        """Turkish-formatted decimal: 1.234,56"""
        formatted = f"{float(v):,.2f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    # Logo + company info
    header_data = []
    company_block = [
        Paragraph(f"<b>{tenant_name}</b>", ParagraphStyle("co", fontName="Helvetica-Bold", fontSize=11)),
    ]
    if tenant_tax_no:
        company_block.append(Paragraph(f"VKN: {tenant_tax_no}", subtitle_style))
    if tenant_phone:
        company_block.append(Paragraph(f"Tel: {tenant_phone}", subtitle_style))
    if tenant_address:
        company_block.append(Paragraph(tenant_address[:80], subtitle_style))

    doc_title_block = [
        Paragraph("YEMEK RAPORU", title_style),
        Paragraph(
            f"Dönem: {report.date_from.strftime('%d.%m.%Y')} — {report.date_to.strftime('%d.%m.%Y')}",
            subtitle_style,
        ),
        Paragraph(
            f"Oluşturulma: {report.generated_at.strftime('%d.%m.%Y %H:%M')}",
            subtitle_style,
        ),
    ]
    if report.customer_name:
        doc_title_block.append(
            Paragraph(f"Müşteri: <b>{report.customer_name}</b>", subtitle_style)
        )

    header_tbl = Table(
        [[company_block, doc_title_block]],
        colWidths=["50%", "50%"],
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_tbl)
    story.append(HRFlowable(width="100%", thickness=2, color=primary, spaceAfter=8))

    # ── Data Table ───────────────────────────────────────────────────────────
    col_labels = [
        Paragraph("Tarih", header_cell),
        Paragraph("Müşteri / Lokasyon", header_cell),
        Paragraph("Yemek", header_cell),
        Paragraph("Adet", header_cell),
        Paragraph("Birim Fiyat", header_cell),
        Paragraph("KDV %", header_cell),
        Paragraph("Net", header_cell),
        Paragraph("KDV", header_cell),
        Paragraph("Toplam", header_cell),
    ]
    table_data = [col_labels]

    for i, row in enumerate(report.rows):
        bg = row_alt if i % 2 == 0 else white
        loc = f" / {row.location_name}" if row.location_name else ""
        table_data.append([
            Paragraph(row.business_date.strftime("%d.%m.%Y"), normal_cell),
            Paragraph(f"{row.customer_name}{loc}", normal_cell),
            Paragraph(row.meal_type_name, normal_cell),
            Paragraph(str(int(row.total_quantity)), ParagraphStyle("rc", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
            Paragraph(tr_decimal(row.unit_price), ParagraphStyle("rc", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
            Paragraph(f"%{tr_decimal(row.vat_rate)}", ParagraphStyle("rc", fontName="Helvetica", fontSize=8, alignment=TA_CENTER)),
            Paragraph(tr_decimal(row.total_net), ParagraphStyle("rc", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
            Paragraph(tr_decimal(row.total_vat), ParagraphStyle("rc", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
            Paragraph(tr_decimal(row.total_gross), ParagraphStyle("rcb", fontName="Helvetica-Bold", fontSize=8, alignment=TA_RIGHT)),
        ])

    col_widths = [2.0*cm, 4.5*cm, 2.0*cm, 1.2*cm, 2.2*cm, 1.2*cm, 2.2*cm, 1.8*cm, 2.2*cm]
    data_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, row_alt]),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])
    data_table.setStyle(ts)
    story.append(data_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── Totals ────────────────────────────────────────────────────────────────
    s = report.summary
    totals_table = Table(
        [
            ["", "", "", "", "", "", "Toplam Net:", "", tr_decimal(s.total_net) + " TL"],
            ["", "", "", "", "", "", "Toplam KDV:", "", tr_decimal(s.total_vat) + " TL"],
            ["", "", "", "", "", "", "GENEL TOPLAM:", "", tr_decimal(s.total_gross) + " TL"],
        ],
        colWidths=col_widths,
    )
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (6, 0), (6, 1), "Helvetica-Bold"),
        ("FONTNAME", (6, 2), (-1, 2), "Helvetica-Bold"),
        ("BACKGROUND", (0, 2), (-1, 2), HexColor("#dbeafe")),
        ("ALIGN", (6, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LINEABOVE", (6, 0), (-1, 0), 1, primary),
    ]))
    story.append(totals_table)

    # ── Meal Type Summary ─────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#cbd5e1"), spaceAfter=6))
    story.append(Paragraph("Yemek Türü Özeti", ParagraphStyle("sec", fontName="Helvetica-Bold", fontSize=9, textColor=primary)))
    story.append(Spacer(1, 0.2 * cm))

    if s.by_meal_type:
        sum_data = [[
            Paragraph("Yemek Türü", header_cell),
            Paragraph("Toplam Adet", header_cell),
            Paragraph("Net Tutar", header_cell),
            Paragraph("KDV", header_cell),
            Paragraph("Brüt Tutar", header_cell),
        ]]
        for code, vals in s.by_meal_type.items():
            sum_data.append([
                Paragraph(vals.get("name", code), normal_cell),
                Paragraph(str(int(vals.get("qty", 0))), ParagraphStyle("r", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(tr_decimal(Decimal(str(vals.get("net", 0)))), ParagraphStyle("r", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(tr_decimal(Decimal(str(vals.get("vat", 0)))), ParagraphStyle("r", fontName="Helvetica", fontSize=8, alignment=TA_RIGHT)),
                Paragraph(tr_decimal(Decimal(str(vals.get("gross", 0)))), ParagraphStyle("rb", fontName="Helvetica-Bold", fontSize=8, alignment=TA_RIGHT)),
            ])
        sum_table = Table(sum_data, colWidths=[5*cm, 3*cm, 4*cm, 3*cm, 4.3*cm])
        sum_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, row_alt]),
            ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(sum_table)

    doc.build(story)
    return buf.getvalue()


# ── Excel Generation ───────────────────────────────────────────────────────────

def generate_meal_report_excel(report: MealReportResponse, tenant_name: str) -> bytes:
    """
    Generates XLSX meal report.
    Returns raw bytes.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Yemek Raporu"

    header_fill = PatternFill(start_color="1e3a5f", end_color="1e3a5f", fill_type="solid")
    alt_fill = PatternFill(start_color="f1f5f9", end_color="f1f5f9", fill_type="solid")
    total_fill = PatternFill(start_color="dbeafe", end_color="dbeafe", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=9)
    bold_font = Font(bold=True, size=9)
    normal_font = Font(size=9)
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    # Title row
    ws.merge_cells("A1:I1")
    ws["A1"] = f"{tenant_name} — Yemek Raporu"
    ws["A1"].font = Font(bold=True, size=12)
    ws.merge_cells("A2:I2")
    ws["A2"] = f"Dönem: {report.date_from.strftime('%d.%m.%Y')} — {report.date_to.strftime('%d.%m.%Y')}"
    ws["A2"].font = Font(size=9, color="64748b")

    # Headers
    headers = ["Tarih", "Müşteri", "Lokasyon", "Yemek Türü", "Adet", "Birim Fiyat", "Net", "KDV %", "KDV", "Toplam"]
    col_widths = [13, 28, 22, 14, 8, 12, 12, 8, 12, 14]

    header_row = 4
    for col_idx, (h, w) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    ws.row_dimensions[header_row].height = 20

    # Data rows
    for i, row in enumerate(report.rows):
        r = header_row + 1 + i
        fill = alt_fill if i % 2 == 0 else PatternFill()
        values = [
            row.business_date.strftime("%d.%m.%Y"),
            row.customer_name,
            row.location_name or "",
            row.meal_type_name,
            int(row.total_quantity),
            float(row.unit_price),
            float(row.total_net),
            float(row.vat_rate),
            float(row.total_vat),
            float(row.total_gross),
        ]
        for col_idx, val in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col_idx, value=val)
            cell.font = normal_font
            cell.fill = fill
            cell.border = thin_border
            if col_idx >= 5:
                cell.alignment = Alignment(horizontal="right")
                if col_idx >= 6:
                    cell.number_format = '#,##0.00'

    # Totals
    total_row = header_row + 1 + len(report.rows) + 1
    ws.cell(row=total_row, column=6, value="TOPLAM NET:").font = bold_font
    ws.cell(row=total_row, column=7, value=float(report.summary.total_net)).font = bold_font
    ws.cell(row=total_row, column=9, value=float(report.summary.total_vat)).font = bold_font
    ws.cell(row=total_row, column=10, value=float(report.summary.total_gross)).font = bold_font
    for col_idx in range(6, 11):
        cell = ws.cell(row=total_row, column=col_idx)
        cell.fill = total_fill
        cell.border = thin_border
        if isinstance(cell.value, float):
            cell.number_format = '#,##0.00'

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
