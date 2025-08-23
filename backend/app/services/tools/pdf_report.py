#!/usr/bin/env python3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    Flowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, Polygon, Path
from reportlab.graphics import renderPDF
from datetime import datetime
from pathlib import Path


class ShieldLogo(Flowable):
    """Custom flowable for rendering a shield logo"""
    def __init__(self, width=1*inch, height=1.2*inch):
        Flowable.__init__(self)
        self.width = width
        self.height = height
    
    def draw(self):
        # Draw a shield shape
        canvas = self.canv
        
        # Shield color (dark gray)
        shield_color = HexColor('#4B5563')
        
        # Create shield path
        path = canvas.beginPath()
        
        # Shield shape coordinates (normalized to fit in width x height)
        w, h = self.width, self.height
        
        # Start from top center
        path.moveTo(w/2, 0)
        # Top right corner
        path.lineTo(w*0.9, h*0.1)
        # Right side
        path.lineTo(w*0.9, h*0.5)
        # Bottom right curve
        path.curveTo(w*0.9, h*0.7, w*0.7, h*0.85, w/2, h)
        # Bottom left curve (mirror)
        path.curveTo(w*0.3, h*0.85, w*0.1, h*0.7, w*0.1, h*0.5)
        # Left side
        path.lineTo(w*0.1, h*0.1)
        # Top left corner
        path.lineTo(w/2, 0)
        path.close()
        
        # Fill the shield
        canvas.setFillColor(shield_color)
        canvas.drawPath(path, fill=1, stroke=0)
        
        # Add some detail lines
        canvas.setStrokeColor(HexColor('#6B7280'))
        canvas.setLineWidth(2)
        
        # Vertical line
        canvas.line(w/2, h*0.15, w/2, h*0.85)
        
        # Horizontal line
        canvas.line(w*0.25, h*0.4, w*0.75, h*0.4)


class SeverityBox(Flowable):
    """Custom flowable for rendering severity summary boxes"""
    def __init__(self, severity, count, description, width=2.5*inch, height=1.5*inch):
        Flowable.__init__(self)
        self.severity = severity
        self.count = count
        self.description = description
        self.width = width
        self.height = height
        
        # Define colors for each severity
        self.colors = {
            'Critical': {'bg': HexColor('#FDEBEC'), 'text': HexColor('#DC2626'), 'bar': HexColor('#DC2626')},
            'High': {'bg': HexColor('#FFF1E6'), 'text': HexColor('#EA580C'), 'bar': HexColor('#EA580C')},
            'Medium': {'bg': HexColor('#FFF8DB'), 'text': HexColor('#D97706'), 'bar': HexColor('#F59E0B')},
            'Low': {'bg': HexColor('#EAF8F1'), 'text': HexColor('#065F46'), 'bar': HexColor('#10B981')}
        }
    
    def draw(self):
        canvas = self.canv
        colors = self.colors.get(self.severity, self.colors['Medium'])
        
        # Draw rounded rectangle background
        canvas.setFillColor(colors['bg'])
        canvas.roundRect(0, 0, self.width, self.height, 10, fill=1, stroke=0)
        
        # Draw severity label
        canvas.setFont("Times-Bold", 11)
        canvas.setFillColor(black)
        canvas.drawString(10, self.height - 25, self.severity)
        
        # Draw count (reduced size, raised to avoid overlap with bar)
        canvas.setFont("Times-Bold", 26)
        canvas.setFillColor(black)
        canvas.drawString(10, self.height - 50, str(self.count))
        
        # Draw progress bar
        bar_y = 18
        bar_height = 7
        bar_width = self.width - 20
        
        # Background bar
        canvas.setFillColor(HexColor('#E5E7EB'))
        canvas.rect(10, bar_y, bar_width, bar_height, fill=1, stroke=0)
        
        # Filled bar (percentage based on severity)
        fill_percentages = {'Critical': 0.8, 'High': 0.6, 'Medium': 0.3, 'Low': 0.1}
        fill_percent = fill_percentages.get(self.severity, 0.5)
        
        if self.count > 0:
            canvas.setFillColor(colors['bar'])
            canvas.rect(10, bar_y, bar_width * fill_percent, bar_height, fill=1, stroke=0)


class SecurityReportGenerator:
    def __init__(self, filename="security_report.pdf"):
        self.filename = filename
        self.doc = SimpleDocTemplate(filename, pagesize=letter,
                                   rightMargin=90, leftMargin=90,
                                   topMargin=50, bottomMargin=50)
        self.styles = getSampleStyleSheet()
        self.story = []
        # Available content width after margins
        self.content_width = self.doc.width
        
        # Define custom colors to match GuardAigis theme
        self.critical_color = HexColor('#DC2626')  # Red
        self.high_color = HexColor('#EA580C')      # Orange  
        self.medium_color = HexColor('#F59E0B')    # Yellow
        self.low_color = HexColor('#10B981')       # Green
        self.header_bg = HexColor('#F9FAFB')       # Light gray
        self.border_color = HexColor('#E5E7EB')    # Border gray
        self.text_color = HexColor('#1F2937')      # Dark gray text
        
        # Custom styles
        self._define_custom_styles()
    
    def _define_custom_styles(self):
        """Define custom paragraph styles to match GuardAigis design"""
        # Company name style (GuardAigis)
        self.company_style = ParagraphStyle(
            'CompanyName',
            parent=self.styles['Heading1'],
            fontSize=36,
            leading=42,  # prevent overlap
            spaceAfter=10,
            textColor=black,
            fontName='Times-Bold',
            alignment=TA_LEFT
        )
        
        # Report title style
        self.title_style = ParagraphStyle(
            'SecurityTitle',
            parent=self.styles['Normal'],
            fontSize=18,
            leading=22,
            spaceAfter=8,
            textColor=self.text_color,
            fontName='Times-Roman',
            alignment=TA_LEFT
        )
        
        # Subtitle style for date and support
        self.subtitle_style = ParagraphStyle(
            'SecuritySubtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=15,
            spaceAfter=6,
            textColor=self.text_color,
            fontName='Times-Roman',
            alignment=TA_LEFT
        )
        
        # Overall Summary heading
        self.summary_heading_style = ParagraphStyle(
            'SummaryHeading',
            parent=self.styles['Heading2'],
            fontSize=20,
            leading=24,
            spaceAfter=10,
            spaceBefore=10,
            textColor=black,
            fontName='Times-Bold',
            alignment=TA_LEFT
        )
        
        # Finding title style
        self.finding_title_style = ParagraphStyle(
            'FindingTitle',
            parent=self.styles['Heading3'],
            fontSize=16,
            leading=20,
            spaceAfter=12,
            spaceBefore=20,
            textColor=self.critical_color,
            fontName='Times-Bold',
            alignment=TA_LEFT
        )
        
        # Severity badge style
        self.severity_style = ParagraphStyle(
            'SeverityStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12,
            textColor=white,
            fontName='Times-Bold',
            alignment=TA_CENTER,
            borderPadding=6
        )
        
        # Body text style
        self.body_style = ParagraphStyle(
            'SecurityBody',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=10,
            textColor=self.text_color,
            fontName='Times-Roman',
            alignment=TA_JUSTIFY
        )
        
        # Info style for metadata
        self.info_style = ParagraphStyle(
            'InfoStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=13,
            spaceAfter=6,
            textColor=HexColor('#374151'),
            fontName='Times-Bold',
            alignment=TA_LEFT
        )
    
    def add_header(self, target_url, timestamp):
        """Add GuardAigis-style report header"""
        # Create a table for the header layout
        header_data = []
        
        # First row: Logo image (prefer PNG logo; fallback to vector shield if missing)
        logo_flowable = None
        try:
            here = Path(__file__).resolve()
            candidate_paths = [
                here.parents[3] / "logo-2.png",   # repo/backend root typical
                here.parents[2] / "logo-2.png",   # repo/app root inside some containers
                Path.cwd() / "logo-2.png",        # current working directory
            ]
            for p in candidate_paths:
                if p.exists():
                    logo_flowable = Image(str(p), width=0.8*inch, height=1*inch)
                    break
        except Exception:
            logo_flowable = None
        if logo_flowable is None:
            logo_flowable = ShieldLogo(width=0.8*inch, height=1*inch)
        
        # Company and report info
        company_info = []
        company_info.append(Paragraph("<b>GuardAigis</b>", self.company_style))
        company_info.append(Paragraph(f"Security Report for <b>{target_url}</b>", self.title_style))
        
        # Date and support info
        date_str = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d')
        info_text = f"<b>Date:</b> {date_str}&nbsp;&nbsp;&nbsp;&nbsp;<b>Support:</b> <font color='blue'>guardaigis@gmail.com</font>"
        company_info.append(Paragraph(info_text, self.subtitle_style))
        
        header_data.append([logo_flowable, company_info])
        
        # Create header table
        # Compute dynamic column widths based on available content width
        left_col_width = 1.0*inch
        header_table = Table(header_data, colWidths=[left_col_width, self.content_width - left_col_width])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (0,0), 0),
            ('RIGHTPADDING', (1,0), (1,0), 0),
        ]))
        
        self.story.append(header_table)
        
        # Add horizontal line
        self.story.append(Spacer(1, 10))
        line = Table([['']],  colWidths=[self.content_width])
        line.setStyle(TableStyle([
            ('LINEABOVE', (0,0), (-1,0), 1, black),
        ]))
        self.story.append(line)
        self.story.append(Spacer(1, 6))
    
    def add_summary(self, summary_data):
        """Add GuardAigis-style overall summary section with colored boxes"""
        self.story.append(Paragraph("Overall Summary", self.summary_heading_style))
        
        # Create severity boxes
        critical_count = summary_data.get('critical_findings', 0)
        high_count = summary_data.get('high_findings', 0)
        medium_count = summary_data.get('medium_findings', 0)
        low_count = summary_data.get('low_findings', 0)
        
        # Create boxes sized to fit two columns within the content width
        box_width = (self.content_width / 2) - 24  # account for table cell padding
        critical_box = SeverityBox('Critical', critical_count, 'Severe', width=box_width, height=1.1*inch)
        high_box = SeverityBox('High', high_count, 'Elevated', width=box_width, height=1.1*inch)
        medium_box = SeverityBox('Medium', medium_count, 'None', width=box_width, height=1.1*inch)
        low_box = SeverityBox('Low', low_count, 'None', width=box_width, height=1.1*inch)
        
        # Arrange in 2x2 grid
        summary_data = [
            [critical_box, high_box],
            [medium_box, low_box]
        ]
        
        summary_table = Table(summary_data, colWidths=[self.content_width/2, self.content_width/2], rowHeights=[1.25*inch, 1.25*inch])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        
        self.story.append(summary_table)
        self.story.append(Spacer(1, 12))
    
    def add_finding(self, finding):
        """Add individual finding with GuardAigis styling"""
        # Risk level color
        risk_colors = {
            'CRITICAL': self.critical_color,
            'HIGH': self.high_color,
            'MEDIUM': self.medium_color,
            'LOW': self.low_color
        }
        severity = finding.get('severity', 'MEDIUM')
        risk_color = risk_colors.get(severity, self.medium_color)
        
        # Palette to match Overall Summary severity boxes (background + text)
        severity_palettes = {
            'CRITICAL': {'bg': HexColor('#FDEBEC'), 'text': HexColor('#DC2626')},
            'HIGH': {'bg': HexColor('#FFF1E6'), 'text': HexColor('#EA580C')},
            'MEDIUM': {'bg': HexColor('#FFF8DB'), 'text': HexColor('#D97706')},
            'LOW': {'bg': HexColor('#EAF8F1'), 'text': HexColor('#065F46')},
        }
        severity_palette = severity_palettes.get(severity, severity_palettes['MEDIUM'])
        
        # Create finding title with colored text
        title_text = finding.get('title', 'Unknown Finding')
        title_style = ParagraphStyle(
            'FindingTitleColored',
            parent=self.finding_title_style,
            textColor=risk_color
        )
        title_para = Paragraph(title_text, title_style)

        # Create severity badge (use light background + colored text like Overall Summary)
        badge_text_style = ParagraphStyle(
            'SeverityBadgeText',
            parent=self.severity_style,
            textColor=severity_palette['text']
        )
        badge_data = [[Paragraph(severity, badge_text_style)]]
        badge_table = Table(badge_data, colWidths=[1.2*inch], rowHeights=[0.3*inch])
        badge_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), severity_palette['bg']),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
            ('VALIGN', (0,0), (0,0), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (0,0), 8),
            ('RIGHTPADDING', (0,0), (0,0), 8),
            ('TOPPADDING', (0,0), (0,0), 4),
            ('BOTTOMPADDING', (0,0), (0,0), 4),
            ('ROUNDEDCORNERS', [3]),
        ]))

        # Verification badge: BUG if verified, WARNING if attempted but failed, NO_VERIFY if no commands available
        verification = finding.get('verification', {})
        is_verified = bool(verification.get('verified', False))
        attempted = bool(verification.get('attempted', False))
        commands_available = bool(verification.get('commands', []))
        

        
        # Determine verification label based on actual state
        if is_verified:
            verify_label = 'BUG'
            verify_bg = HexColor('#FDEBEC')  # Red background
            verify_text = HexColor('#DC2626')  # Red text
        elif attempted and commands_available:
            verify_label = 'WARNING'
            verify_bg = HexColor('#FFF8DB')  # Yellow background
            verify_text = HexColor('#D97706')  # Orange text
        else:
            verify_label = 'NO_VERIFY'
            verify_bg = HexColor('#F3F4F6')  # Gray background
            verify_text = HexColor('#6B7280')  # Gray text
        verify_text_style = ParagraphStyle(
            'VerifyBadgeText',
            parent=self.severity_style,
            textColor=verify_text
        )
        verify_data = [[Paragraph(verify_label, verify_text_style)]]
        verify_badge_table = Table(verify_data, colWidths=[1.2*inch], rowHeights=[0.3*inch])
        verify_badge_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), verify_bg),
            ('ALIGN', (0,0), (0,0), 'CENTER'),
            ('VALIGN', (0,0), (0,0), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (0,0), 8),
            ('RIGHTPADDING', (0,0), (0,0), 8),
            ('TOPPADDING', (0,0), (0,0), 4),
            ('BOTTOMPADDING', (0,0), (0,0), 4),
            ('ROUNDEDCORNERS', [3]),
        ]))

        # Place badges vertically with WARNING on top and CRITICAL below
        badges_container = Table(
            [[verify_badge_table], [badge_table]],
            colWidths=[1.2*inch],
            rowHeights=[0.3*inch, 0.3*inch]
        )
        badges_container.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))

        # Place title on the left and badge to the right in the same row
        header_table = Table(
            [[title_para, badges_container]],
            colWidths=[self.content_width - 1.4*inch, 1.4*inch]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        self.story.append(header_table)
        self.story.append(Spacer(1, 10))
        
        # Create info row with Status, File (only if known), Risk Score, Confidence
        info_parts = []
        info_parts.append(f"<b>Status:</b> <b>{finding.get('status', 'Unknown')}</b>")
        
        # Show filename if available in evidence_data
        evidence_data = finding.get('evidence_data', [])
        if evidence_data and len(evidence_data) > 0:
            # Get the first filename found
            first_filename = evidence_data[0].get('filename', '').strip() or 'Unknown'
            if first_filename != 'Unknown':
                info_parts.append(f"<b>File:</b> <b>{first_filename}</b>")
        else:
            endpoint = finding.get('endpoint', 'Unknown')
            if endpoint != 'Unknown':
                info_parts.append(f"<b>Endpoint:</b> <b>{endpoint}</b>")
        
        info_parts.append(f"<b>Risk Score:</b> <b>{finding.get('risk_score', 0)*100:.0f}%</b>")
        info_parts.append(f"<b>Confidence:</b> <b>{finding.get('confidence_level', 'Unknown')}</b>")
        
        info_text = "&nbsp;&nbsp;&nbsp;&nbsp;".join(info_parts)
        self.story.append(Paragraph(info_text, self.info_style))
        self.story.append(Spacer(1, 12))
        
        # Description
        self.story.append(Paragraph("<b>Description</b>", self.body_style))
        self.story.append(Paragraph(finding.get('description', 'No description available'), self.body_style))
        self.story.append(Spacer(1, 10))
        
        # Impact
        self.story.append(Paragraph("<b>Impact</b>", self.body_style))
        self.story.append(Paragraph(finding.get('impact', 'No impact assessment available'), self.body_style))
        self.story.append(Spacer(1, 10))
        
        # Remediation Steps
        remediation_steps = finding.get('remediation_steps', [])
        if remediation_steps:
            self.story.append(Paragraph("<b>Remediation Steps</b>", self.body_style))
            # Numbered steps with bold prefixes and indentation
            for i, step in enumerate(remediation_steps, 1):
                step_text = f"<b>Step {i}:</b> {step}"
                step_style = ParagraphStyle(
                    'RemediationStep',
                    parent=self.body_style,
                    leftIndent=20
                )
                self.story.append(Paragraph(step_text, step_style))
            self.story.append(Spacer(1, 10))
        
        # Verification Commands and Results (if any)
        verification = finding.get('verification', {})
        
        # Add verification details if available (matching Markdown format)
        if verification.get('attempted', False):
            self.story.append(Paragraph("<b>Verification Attempted:</b> Yes", self.body_style))
            
            if verification.get('results'):
                self.story.append(Paragraph("<b>Verification Results:</b>", self.body_style))
                
                for i, result in enumerate(verification['results'][:2], 1):  # Show first 2 results
                    success = result.get('success', False)
                    status = "✅ SUCCESS" if success else "❌ FAILED"
                    
                    # Status line
                    status_text = f"  {i}. {status}"
                    status_para = Paragraph(status_text, ParagraphStyle('VerificationStatus', parent=self.body_style, fontSize=10, leading=14, leftIndent=20))
                    self.story.append(status_para)
                    
                    # Command (if available)
                    if result.get('command'):
                        # Show original command template
                        cmd_text = f"     Command Template: <code>{result['command']}</code>"
                        cmd_para = Paragraph(cmd_text, ParagraphStyle('VerificationCommand', parent=self.body_style, fontSize=9, leading=12, leftIndent=40))
                        self.story.append(cmd_para)
                        
                        # Show executed command if different from template
                        if result.get('executed_command') and result['executed_command'] != result['command']:
                            exec_cmd_text = f"     Executed Command: <code>{result['executed_command']}</code>"
                            exec_cmd_para = Paragraph(exec_cmd_text, ParagraphStyle('VerificationExecutedCommand', parent=self.body_style, fontSize=9, leading=12, leftIndent=40, textColor=HexColor('#059669')))
                            self.story.append(exec_cmd_para)
                    
                    # Output (if available)
                    if result.get('stdout'):
                        output_text = f"     Output: {result['stdout'][:200]}..."
                        output_para = Paragraph(output_text, ParagraphStyle('VerificationOutput', parent=self.body_style, fontSize=9, leading=12, leftIndent=40))
                        self.story.append(output_para)
                    
                    # AI Analysis (if available)
                    ai_status = result.get('ai_status')
                    ai_analysis = result.get('ai_analysis')
                    if ai_status and ai_analysis:
                        ai_text = f"     AI Analysis: {ai_status} - {ai_analysis}"
                        ai_para = Paragraph(ai_text, ParagraphStyle('VerificationAI', parent=self.body_style, fontSize=9, leading=12, leftIndent=40))
                        self.story.append(ai_para)
                    
                    self.story.append(Spacer(1, 6))
        
        # Evidence (if any)
        evidence_data = finding.get('evidence_data', [])  # Use the structured evidence data
        if evidence_data:
            self.story.append(Paragraph("<b>Evidence</b>", self.body_style))
            # Boxed evidence block with filenames and URLs
            box_data = []
            for ev_item in evidence_data[:10]:  # show up to 10
                filename = (ev_item.get('filename') or '').strip() or 'Unknown'
                evidence_text = ev_item.get('evidence', '')
                url = (ev_item.get('url') or '').strip() or 'Unknown'
                
                # Format: URL, filename: evidence
                if url != 'Unknown':
                    if filename != 'Unknown':
                        formatted_evidence = f"<b>URL:</b> {url}<br/><b>{filename}:</b> {evidence_text}"
                    else:
                        formatted_evidence = f"<b>URL:</b> {url}<br/>{evidence_text}"
                else:
                    if filename != 'Unknown':
                        formatted_evidence = f"<b>{filename}:</b> {evidence_text}"
                    else:
                        formatted_evidence = evidence_text
                box_data.append([Paragraph(formatted_evidence, ParagraphStyle('EvidenceLine', parent=self.body_style, fontSize=10, leading=14))])
            table = Table(box_data, colWidths=[self.content_width - 20])
            table.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 1, HexColor('#E5E7EB')),
                ('BACKGROUND', (0,0), (-1,-1), HexColor('#F9FAFB')),
                ('LEFTPADDING', (0,0), (-1,-1), 12),
                ('RIGHTPADDING', (0,0), (-1,-1), 12),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ]))
            self.story.append(table)
        else:
            # Fallback to old evidence format
            evidence = finding.get('evidence', [])
            if evidence:
                self.story.append(Paragraph("<b>Evidence</b>", self.body_style))
                # Boxed evidence block similar to screenshot
                box_data = []
                for ev in evidence[:10]:  # show up to 10
                    box_data.append([Paragraph(ev, ParagraphStyle('EvidenceLine', parent=self.body_style, fontSize=10, leading=14))])
                table = Table(box_data, colWidths=[self.content_width - 20])
                table.setStyle(TableStyle([
                    ('BOX', (0,0), (-1,-1), 1, HexColor('#E5E7EB')),
                    ('BACKGROUND', (0,0), (-1,-1), HexColor('#F9FAFB')),
                    ('LEFTPADDING', (0,0), (-1,-1), 12),
                    ('RIGHTPADDING', (0,0), (-1,-1), 12),
                    ('TOPPADDING', (0,0), (-1,-1), 8),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ]))
                self.story.append(table)
        
        self.story.append(Spacer(1, 30))
    
    def build(self):
        """Build the PDF document"""
        self.doc.build(self.story)
        print(f"✅ Security report generated: {self.filename}")


def _infer_target_url_from_output(output_path: Path) -> str | None:
    """Infer target URL/domain from the output filename if possible.

    Expected pattern: {domain}_api_exposure_report_{timestamp}.pdf
    We convert underscores back to dots for readability.
    """
    try:
        name = output_path.stem  # without extension
        marker = "_api_exposure_report_"
        if marker in name:
            domain_part = name.split(marker)[0]
            # Convert underscores back to dots (best-effort)
            inferred = domain_part.replace("_", ".")
            return inferred
    except Exception:
        pass
    return None


def build_pdf_report(report_data, output_path):
    """
    Build a PDF report from the provided data
    
    Args:
        report_data (dict): Report data containing findings and metadata
        output_path (Path): Path where to save the PDF
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create the report generator
        report = SecurityReportGenerator(str(output_path))
        
        # Add header
        target = report_data.get('target_url') or _infer_target_url_from_output(output_path) or 'Unknown'
        report.add_header(
            target_url=target,
            timestamp=report_data.get('timestamp', datetime.now().isoformat())
        )
        
        # Add summary
        if 'summary' in report_data:
            report.add_summary(report_data['summary'])
        
        # Add findings
        findings = report_data.get('findings', [])
        if findings:
            # No need for "Detailed Findings" header as each finding has its own styled title
            for finding in findings:
                report.add_finding(finding)
        
        # Build the PDF
        report.build()
        
        # Verify the file was created
        if output_path.exists():
            return True
        else:
            print(f"❌ PDF file was not created at {output_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error generating PDF report: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


