"""
OrthoBraceForge — Export & Audit PDF Generator
ISO 13485 §4.2.5 compliant audit report generation.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from config import EXPORT_DIR, APP_CLASSIFICATION, APP_VERSION, REGULATORY_BANNER


class AuditPDFGenerator:
    """Generate comprehensive audit PDF reports for design traceability."""

    def __init__(self, db):
        self.db = db

    def generate(self, patient_id: str, design_id: str,
                 state: Dict[str, Any]) -> str:
        """
        Generate a complete audit PDF for a design.
        Returns path to generated PDF.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.colors import red, black, gray, HexColor
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table,
                TableStyle, PageBreak, HRFlowable,
            )

            pdf_path = str(EXPORT_DIR / f"audit_{design_id[:8]}.pdf")
            doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                                    leftMargin=0.75*inch, rightMargin=0.75*inch,
                                    topMargin=0.75*inch, bottomMargin=0.75*inch)

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle', parent=styles['Title'],
                fontSize=18, spaceAfter=6,
            )
            heading_style = ParagraphStyle(
                'CustomHeading', parent=styles['Heading2'],
                fontSize=13, spaceAfter=4, spaceBefore=12,
            )
            warning_style = ParagraphStyle(
                'Warning', parent=styles['Normal'],
                textColor=red, fontSize=10, spaceBefore=6, spaceAfter=6,
            )
            normal = styles['Normal']

            story = []
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            # Header
            story.append(Paragraph("OrthoBraceForge — Design Audit Report", title_style))
            story.append(Paragraph(REGULATORY_BANNER, warning_style))
            story.append(HRFlowable(width="100%", color=gray))
            story.append(Spacer(1, 12))

            # Report metadata
            meta_data = [
                ["Report Generated:", now],
                ["Software Version:", APP_VERSION],
                ["Classification:", APP_CLASSIFICATION],
                ["Patient ID:", patient_id[:8] + "…"],
                ["Design ID:", design_id[:8] + "…"],
                ["Run ID:", state.get("run_id", "N/A")[:8] + "…"],
            ]
            meta_table = Table(meta_data, colWidths=[2*inch, 4.5*inch])
            meta_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(meta_table)
            story.append(Spacer(1, 12))

            # Section 1: Patient Summary
            story.append(Paragraph("1. Patient Summary", heading_style))
            patient = state.get("patient", {})
            patient_data = [
                ["Age:", f"{patient.get('age', 'N/A')} years"],
                ["Weight:", f"{patient.get('weight_kg', 'N/A')} kg"],
                ["Height:", f"{patient.get('height_cm', 'N/A')} cm"],
                ["Diagnosis:", "Idiopathic Toe Walking (Equinus Gait)"],
                ["Laterality:", state.get("laterality", "N/A")],
                ["Severity:", state.get("severity", "N/A")],
            ]
            pt_table = Table(patient_data, colWidths=[1.5*inch, 5*inch])
            pt_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(pt_table)

            # Section 2: Design Parameters
            story.append(Paragraph("2. Design Parameters", heading_style))
            constraints = state.get("constraints", {})
            if constraints:
                param_data = [[str(k), str(v)] for k, v in constraints.items()]
                param_table = Table(param_data, colWidths=[2.5*inch, 4*inch])
                param_table.setStyle(TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('GRID', (0, 0), (-1, -1), 0.5, gray),
                ]))
                story.append(param_table)

            # Section 3: Compliance Check
            story.append(Paragraph("3. Regulatory Compliance Check", heading_style))
            compliance = state.get("compliance_result", {})
            comp_status = "PASSED" if compliance.get("passed") else "FAILED / BLOCKED"
            story.append(Paragraph(f"Status: <b>{comp_status}</b>", normal))
            flags = state.get("regulatory_flags", [])
            if flags:
                story.append(Paragraph(f"Flags: {', '.join(flags)}", normal))
            for issue in compliance.get("blocking_issues", []):
                story.append(Paragraph(f"BLOCKING: {issue}", warning_style))
            for warn in compliance.get("warnings", []):
                story.append(Paragraph(f"Warning: {warn}", normal))

            # Section 4: CAD Generation
            story.append(Paragraph("4. CAD Generation", heading_style))
            story.append(Paragraph(f"Engine: {state.get('cad_engine', 'N/A')}", normal))
            story.append(Paragraph(f"Iterations: {state.get('iteration_count', 0)}", normal))
            story.append(Paragraph(f"STL Path: {state.get('stl_path', 'N/A')}", normal))

            # Section 5: FEA Results
            story.append(Paragraph("5. FEA Stress Analysis", heading_style))
            fea = state.get("fea_result", {})
            if fea:
                fea_status = "PASSED" if fea.get("passed") else "FAILED"
                fea_data = [
                    ["Status:", fea_status],
                    ["Max Von Mises (MPa):", str(fea.get("max_von_mises_mpa", "N/A"))],
                    ["% of Yield:", str(fea.get("von_mises_pct_yield", "N/A"))],
                    ["Safety Factor:", str(fea.get("safety_factor", "N/A"))],
                    ["Required SF:", str(fea.get("required_safety_factor", "N/A"))],
                    ["Dynamic Load (N):", str(fea.get("dynamic_load_n", "N/A"))],
                ]
                fea_table = Table(fea_data, colWidths=[2.5*inch, 4*inch])
                fea_table.setStyle(TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(fea_table)

            # Section 6: Lattice Evaluation
            story.append(Paragraph("6. Lattice Reinforcement Evaluation", heading_style))
            lattice = state.get("lattice_evaluation", {})
            needs_lattice = lattice.get("needs_reinforcement", False)
            story.append(Paragraph(
                f"Reinforcement Needed: <b>{'YES' if needs_lattice else 'NO'}</b>", normal
            ))

            # Section 7: Human Review
            story.append(Paragraph("7. Human Review Gate", heading_style))
            story.append(Paragraph(
                f"Approved: <b>{'YES' if state.get('human_approved') else 'PENDING'}</b>",
                normal
            ))
            if state.get("human_reviewer"):
                story.append(Paragraph(f"Reviewer: {state['human_reviewer']}", normal))
            if state.get("review_notes"):
                story.append(Paragraph(f"Notes: {state['review_notes']}", normal))

            # Section 8: Warnings
            warnings = state.get("warnings", [])
            if warnings:
                story.append(Paragraph("8. Warnings & Advisories", heading_style))
                for w in warnings:
                    story.append(Paragraph(f"• {w}", normal))

            # Section 9: Audit Trail
            story.append(PageBreak())
            story.append(Paragraph("9. Complete Audit Trail", heading_style))
            audit_entries = self.db.get_audit_trail(patient_id)
            if audit_entries:
                audit_data = [["Timestamp", "Action", "Actor", "Details"]]
                for entry in audit_entries:
                    audit_data.append([
                        str(entry.timestamp)[:19],
                        entry.action,
                        entry.actor,
                        entry.details[:80],
                    ])
                audit_table = Table(audit_data, colWidths=[1.3*inch, 0.8*inch, 0.8*inch, 3.6*inch])
                audit_table.setStyle(TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor("#333333")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
                    ('GRID', (0, 0), (-1, -1), 0.5, gray),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(audit_table)

            # Footer disclaimer
            story.append(Spacer(1, 24))
            story.append(HRFlowable(width="100%", color=gray))
            story.append(Paragraph(
                f"This report was auto-generated by OrthoBraceForge v{APP_VERSION}. "
                f"{APP_CLASSIFICATION}. All designs require review by a licensed "
                f"orthotist or physician before clinical use.",
                ParagraphStyle('Footer', parent=normal, fontSize=8, textColor=gray),
            ))

            doc.build(story)
            return pdf_path

        except ImportError:
            # reportlab not available — generate text report
            return self._generate_text_report(patient_id, design_id, state)

    def _generate_text_report(self, patient_id: str, design_id: str,
                               state: Dict) -> str:
        """Fallback text-based audit report when reportlab unavailable."""
        txt_path = str(EXPORT_DIR / f"audit_{design_id[:8]}.txt")
        lines = [
            "=" * 70,
            "OrthoBraceForge — Design Audit Report",
            REGULATORY_BANNER,
            "=" * 70,
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Patient ID: {patient_id[:8]}…",
            f"Design ID: {design_id[:8]}…",
            f"Engine: {state.get('cad_engine', 'N/A')}",
            f"Compliance: {'PASSED' if state.get('compliance_result', {}).get('passed') else 'FAILED'}",
            f"FEA: {'PASSED' if state.get('fea_result', {}).get('passed') else 'FAILED'}",
            f"Human Approved: {state.get('human_approved', False)}",
            f"Reviewer: {state.get('human_reviewer', 'N/A')}",
            "",
            "--- Trace Log ---",
        ]
        lines.extend(state.get("trace_log", []))
        Path(txt_path).write_text("\n".join(lines), encoding="utf-8")
        return txt_path
