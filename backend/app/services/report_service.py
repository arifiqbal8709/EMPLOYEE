import io
from typing import Optional
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from backend.app.models.user import User
from backend.app.models.camera import Camera
from backend.app.models.activity import KeyboardMouseActivity, ProductivityLog
from backend.app.models.ai_log import AlertLog

class ReportService:
    def get_aggregate_stats(self, db: Session, start_date: datetime, end_date: datetime, user_id: Optional[int] = None):
        """
        Aggregate logs over the given date range for a specific user, or all users.
        """
        query_users = db.query(User).filter(User.role == "employee")
        if user_id:
            query_users = query_users.filter(User.id == user_id)
        
        employees = query_users.all()
        stats = []

        for emp in employees:
            # Query productivity logs in date range
            logs = db.query(ProductivityLog).filter(
                ProductivityLog.user_id == emp.id,
                ProductivityLog.timestamp >= start_date,
                ProductivityLog.timestamp <= end_date
            ).all()

            # Query alert logs in date range
            alerts_count = db.query(AlertLog).filter(
                AlertLog.user_id == emp.id,
                AlertLog.timestamp >= start_date,
                AlertLog.timestamp <= end_date
            ).count()

            total_intervals = len(logs)
            if total_intervals == 0:
                stats.append({
                    "username": emp.username,
                    "employee_id": emp.employee_id or "N/A",
                    "department": emp.department or "N/A",
                    "working_hours": 0.0,
                    "idle_hours": 0.0,
                    "avg_score": 0,
                    "phone_usage_mins": 0.0,
                    "attendance_percentage": 0.0,
                    "alerts_count": 0
                })
                continue

            # Calculations: each interval is approx 10 seconds of log
            present_intervals = sum(1 for log in logs if log.is_present)
            idle_intervals = sum(1 for log in logs if log.is_present and (not log.keyboard_active and not log.mouse_active))
            phone_intervals = sum(1 for log in logs if log.phone_detected)
            
            working_hours = round((present_intervals * 10) / 3600.0, 2)
            idle_hours = round((idle_intervals * 10) / 3600.0, 2)
            phone_usage_mins = round((phone_intervals * 10) / 60.0, 1)
            
            avg_score = round(sum(log.score for log in logs) / total_intervals)
            
            # Attendance: count unique days with logs / total days in range (min 1)
            delta_days = (end_date - start_date).days + 1
            unique_days_count = db.query(func.date(ProductivityLog.timestamp)).filter(
                ProductivityLog.user_id == emp.id,
                ProductivityLog.timestamp >= start_date,
                ProductivityLog.timestamp <= end_date
            ).distinct().count()
            
            attendance_percentage = round((unique_days_count / delta_days) * 100.0, 1)
            attendance_percentage = min(attendance_percentage, 100.0)

            stats.append({
                "username": emp.username,
                "employee_id": emp.employee_id or "N/A",
                "department": emp.department or "N/A",
                "working_hours": working_hours,
                "idle_hours": idle_hours,
                "avg_score": avg_score,
                "phone_usage_mins": phone_usage_mins,
                "attendance_percentage": attendance_percentage,
                "alerts_count": alerts_count
            })
            
        return stats

    def generate_excel_report(self, db: Session, start_date: datetime, end_date: datetime, user_id: Optional[int] = None) -> io.BytesIO:
        stats = self.get_aggregate_stats(db, start_date, end_date, user_id)
        
        # Convert to Pandas DataFrame
        df = pd.DataFrame(stats)
        df.rename(columns={
            "username": "Employee Name",
            "employee_id": "Employee ID",
            "department": "Department",
            "working_hours": "Working Hours",
            "idle_hours": "Idle Hours",
            "avg_score": "Average Productivity Score",
            "phone_usage_mins": "Phone Usage (Mins)",
            "attendance_percentage": "Attendance %",
            "alerts_count": "Total Alerts"
        }, inplace=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name="Productivity Report", index=False)
            
            # Auto-adjust columns width
            workbook = writer.book
            worksheet = writer.sheets["Productivity Report"]
            for col in worksheet.columns:
                max_len = max(len(str(val or '')) for val in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 10)

        output.seek(0)
        return output

    def generate_pdf_report(self, db: Session, start_date: datetime, end_date: datetime, user_id: Optional[int] = None) -> io.BytesIO:
        stats = self.get_aggregate_stats(db, start_date, end_date, user_id)
        
        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output, 
            pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=40, bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        
        # Add custom Styles
        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=colors.HexColor("#1A1A40"),
            spaceAfter=15
        )
        
        meta_style = ParagraphStyle(
            name="MetaStyle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#555555"),
            spaceAfter=25
        )

        elements = []
        
        # 1. Header
        elements.append(Paragraph("Employee Productivity & Focus Report", title_style))
        date_str = f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elements.append(Paragraph(f"{date_str} | Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style))
        elements.append(Spacer(1, 10))

        # 2. Table of Stats
        # Build Table Matrix
        table_data = [[
            "Employee Name", "ID", "Department", "Work Hrs", "Idle Hrs", "Focus Score", "Phone Min", "Atten %", "Alerts"
        ]]
        
        for row in stats:
            table_data.append([
                row["username"],
                row["employee_id"],
                row["department"],
                str(row["working_hours"]),
                str(row["idle_hours"]),
                f"{row['avg_score']}%",
                str(row["phone_usage_mins"]),
                f"{row['attendance_percentage']}%",
                str(row["alerts_count"])
            ])

        stats_table = Table(table_data, colWidths=[90, 50, 110, 55, 50, 65, 55, 50, 45])
        
        # Beautiful table styles matching admin grid look
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1F1F3D")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            # Alternate rows background color
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F5F5FC")),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor("#2B2B2B")),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'), # Left align department column
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        
        elements.append(stats_table)
        elements.append(Spacer(1, 40))
        
        # 3. Footer summary text
        summary_style = ParagraphStyle(
            name="SummaryStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=colors.HexColor("#777777")
        )
        elements.append(Paragraph("This PDF report is generated from the secure PostgreSQL database logs of the Employee Productivity Monitoring System. Confidential - Internal Use Only.", summary_style))

        doc.build(elements)
        output.seek(0)
        return output

report_service = ReportService()
