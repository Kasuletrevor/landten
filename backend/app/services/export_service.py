"""
Export service for generating Excel and PDF reports of payment data.
"""

from typing import List, Optional
from datetime import date
from io import BytesIO
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.models.payment import Payment, PaymentStatus


class ExportService:
    """Service for exporting payment data to various formats."""

    # LandTen brand colors
    PRIMARY_COLOR = "6C5DD3"  # Purple
    SECONDARY_COLOR = "8B5CF6"  # Light purple
    BG_COLOR = "F3F4F6"  # Light gray
    TEXT_COLOR = "1F2937"  # Dark gray

    @staticmethod
    def generate_excel(
        payments: List[Payment],
        start_date: date,
        end_date: date,
        landlord_name: str,
    ) -> BytesIO:
        """
        Generate Excel workbook with payment data.

        Args:
            payments: List of Payment objects to export
            start_date: Start of date range
            end_date: End of date range
            landlord_name: Name of the landlord for header

        Returns:
            BytesIO: Excel file as bytes buffer
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "Payment Report"

        # Define styles
        header_font = Font(bold=True, size=12, color="FFFFFF")
        header_fill = PatternFill(
            start_color=ExportService.PRIMARY_COLOR,
            end_color=ExportService.PRIMARY_COLOR,
            fill_type="solid",
        )
        subheader_font = Font(bold=True, size=11)
        subheader_fill = PatternFill(
            start_color=ExportService.BG_COLOR,
            end_color=ExportService.BG_COLOR,
            fill_type="solid",
        )
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Report Header
        ws["A1"] = f"Payment Report"
        ws["A1"].font = Font(bold=True, size=16, color=ExportService.PRIMARY_COLOR)
        ws["A2"] = f"Landlord: {landlord_name}"
        ws["A2"].font = Font(size=11)
        ws["A3"] = (
            f"Period: {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        )
        ws["A3"].font = Font(size=11)
        ws["A4"] = f"Generated: {date.today().strftime('%B %d, %Y')}"
        ws["A4"].font = Font(size=10, italic=True)

        # Empty row
        current_row = 6

        # Summary Section
        ws[f"A{current_row}"] = "Summary"
        ws[f"A{current_row}"].font = Font(
            bold=True, size=14, color=ExportService.PRIMARY_COLOR
        )
        current_row += 1

        # Calculate summary stats
        total_expected = sum(p.amount_due for p in payments)
        total_received = sum(
            p.amount_due
            for p in payments
            if p.status in [PaymentStatus.ON_TIME, PaymentStatus.LATE]
        )
        total_outstanding = sum(
            p.amount_due
            for p in payments
            if p.status in [PaymentStatus.PENDING, PaymentStatus.OVERDUE]
        )
        total_waived = sum(
            p.amount_due for p in payments if p.status == PaymentStatus.WAIVED
        )

        summary_data = [
            ["Total Payments", len(payments)],
            ["Total Expected", ExportService._format_currency(total_expected, "USD")],
            ["Total Received", ExportService._format_currency(total_received, "USD")],
            [
                "Total Outstanding",
                ExportService._format_currency(total_outstanding, "USD"),
            ],
            ["Total Waived", ExportService._format_currency(total_waived, "USD")],
        ]

        for label, value in summary_data:
            ws[f"A{current_row}"] = label
            ws[f"A{current_row}"].font = subheader_font
            ws[f"B{current_row}"] = value
            ws[f"B{current_row}"].alignment = Alignment(horizontal="right")
            current_row += 1

        current_row += 2  # Empty rows

        # Detailed Payments Section
        ws[f"A{current_row}"] = "Detailed Payments"
        ws[f"A{current_row}"].font = Font(
            bold=True, size=14, color=ExportService.PRIMARY_COLOR
        )
        current_row += 1

        # Column headers
        headers = [
            "Tenant Name",
            "Email",
            "Phone",
            "Property",
            "Room",
            "Period Start",
            "Period End",
            "Amount Due",
            "Currency",
            "Due Date",
            "Paid Date",
            "Status",
            "Days Overdue",
            "Reference",
            "Notes",
        ]

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col_num)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )
            cell.border = border

        current_row += 1
        data_start_row = current_row

        # Data rows
        for payment in payments:
            # Get related data
            from app.models.tenant import Tenant
            from app.models.room import Room
            from app.models.property import Property
            from sqlmodel import Session
            from app.core.database import engine

            with Session(engine) as session:
                tenant = session.get(Tenant, payment.tenant_id)
                room = session.get(Room, tenant.room_id) if tenant else None
                property_obj = session.get(Property, room.property_id) if room else None

                # Calculate days overdue
                days_overdue = None
                if payment.status == PaymentStatus.OVERDUE:
                    days_overdue = (date.today() - payment.due_date).days

                row_data = [
                    tenant.name if tenant else "Unknown",
                    tenant.email if tenant else "",
                    tenant.phone if tenant else "",
                    property_obj.name if property_obj else "Unknown",
                    room.name if room else "Unknown",
                    payment.period_start.strftime("%Y-%m-%d"),
                    payment.period_end.strftime("%Y-%m-%d"),
                    payment.amount_due,
                    room.currency if room else "USD",
                    payment.due_date.strftime("%Y-%m-%d"),
                    payment.paid_date.strftime("%Y-%m-%d") if payment.paid_date else "",
                    payment.status.value,
                    days_overdue if days_overdue else "",
                    payment.payment_reference or "",
                    payment.notes or "",
                ]

                for col_num, value in enumerate(row_data, 1):
                    cell = ws.cell(row=current_row, column=col_num)
                    cell.value = value
                    cell.border = border

                    # Formatting
                    if col_num == 8:  # Amount Due column
                        cell.number_format = "#,##0.00"
                        cell.alignment = Alignment(horizontal="right")
                    elif col_num in [12, 13]:  # Status, Days Overdue
                        cell.alignment = Alignment(horizontal="center")
                    else:
                        cell.alignment = Alignment(horizontal="left")

                current_row += 1

        # Adjust column widths
        column_widths = [20, 25, 15, 20, 15, 12, 12, 12, 10, 12, 12, 12, 13, 20, 30]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width

        # Freeze header row
        ws.freeze_panes = f"A{data_start_row}"

        # Save to buffer
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_pdf(
        payments: List[Payment],
        start_date: date,
        end_date: date,
        landlord_name: str,
    ) -> BytesIO:
        """
        Generate PDF report with payment data.

        Args:
            payments: List of Payment objects to export
            start_date: Start of date range
            end_date: End of date range
            landlord_name: Name of the landlord for header

        Returns:
            BytesIO: PDF file as bytes buffer
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )

        # Container for elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=20,
            textColor=colors.HexColor(ExportService.PRIMARY_COLOR),
            spaceAfter=12,
            alignment=1,  # Center
        )
        subtitle_style = ParagraphStyle(
            "CustomSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            spaceAfter=6,
            alignment=1,  # Center
        )
        summary_style = ParagraphStyle(
            "SummaryTitle",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor(ExportService.PRIMARY_COLOR),
            spaceAfter=10,
        )

        # Header
        elements.append(Paragraph("Payment Report", title_style))
        elements.append(Paragraph(f"<b>Landlord:</b> {landlord_name}", subtitle_style))
        elements.append(
            Paragraph(
                f"<b>Period:</b> {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}",
                subtitle_style,
            )
        )
        elements.append(
            Paragraph(
                f"<b>Generated:</b> {date.today().strftime('%B %d, %Y')}",
                subtitle_style,
            )
        )
        elements.append(Spacer(1, 0.2 * inch))

        # Summary Section
        elements.append(Paragraph("Summary", summary_style))

        # Calculate summary stats
        total_expected = sum(p.amount_due for p in payments)
        total_received = sum(
            p.amount_due
            for p in payments
            if p.status in [PaymentStatus.ON_TIME, PaymentStatus.LATE]
        )
        total_outstanding = sum(
            p.amount_due
            for p in payments
            if p.status in [PaymentStatus.PENDING, PaymentStatus.OVERDUE]
        )
        total_waived = sum(
            p.amount_due for p in payments if p.status == PaymentStatus.WAIVED
        )

        summary_data = [
            ["Metric", "Value"],
            ["Total Payments", str(len(payments))],
            ["Total Expected", ExportService._format_currency(total_expected, "USD")],
            ["Total Received", ExportService._format_currency(total_received, "USD")],
            [
                "Total Outstanding",
                ExportService._format_currency(total_outstanding, "USD"),
            ],
            ["Total Waived", ExportService._format_currency(total_waived, "USD")],
        ]

        summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(ExportService.PRIMARY_COLOR),
                    ),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    (
                        "BACKGROUND",
                        (0, 1),
                        (-1, -1),
                        colors.HexColor(ExportService.BG_COLOR),
                    ),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ]
            )
        )
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Detailed Payments Section
        if payments:
            elements.append(Paragraph("Detailed Payments", summary_style))

            # Table headers
            table_data = [
                ["Tenant", "Property", "Room", "Period", "Amount", "Due Date", "Status"]
            ]

            # Add payment data
            from app.models.tenant import Tenant
            from app.models.room import Room
            from app.models.property import Property
            from sqlmodel import Session
            from app.core.database import engine

            for payment in payments:
                with Session(engine) as session:
                    tenant = session.get(Tenant, payment.tenant_id)
                    room = session.get(Room, tenant.room_id) if tenant else None
                    property_obj = (
                        session.get(Property, room.property_id) if room else None
                    )

                    period = f"{payment.period_start.strftime('%b %d')} - {payment.period_end.strftime('%b %d')}"
                    amount = ExportService._format_currency(
                        payment.amount_due, room.currency if room else "USD"
                    )

                    table_data.append(
                        [
                            tenant.name if tenant else "Unknown",
                            property_obj.name if property_obj else "Unknown",
                            room.name if room else "Unknown",
                            period,
                            amount,
                            payment.due_date.strftime("%b %d, %Y"),
                            payment.status.value,
                        ]
                    )

            # Create table
            payments_table = Table(
                table_data,
                colWidths=[
                    1.4 * inch,
                    1.2 * inch,
                    0.9 * inch,
                    1.3 * inch,
                    1.1 * inch,
                    1.0 * inch,
                    0.8 * inch,
                ],
            )
            payments_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor(ExportService.PRIMARY_COLOR),
                        ),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("ALIGN", (4, 1), (4, -1), "RIGHT"),
                        ("ALIGN", (6, 1), (6, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor(ExportService.BG_COLOR)],
                        ),
                    ]
                )
            )
            elements.append(payments_table)
        else:
            elements.append(
                Paragraph(
                    "No payments found for the selected criteria.", styles["Normal"]
                )
            )

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _format_currency(amount: float, currency: str) -> str:
        """Format amount with currency code."""
        if amount is None:
            return "-"
        return f"{currency} {amount:,.2f}"
