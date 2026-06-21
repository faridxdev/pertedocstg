"""
PerteDocsTG - Service de Génération des Récépissés PDF
"""

import io
import qrcode
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import base64
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


class ReceiptService:
    """Service de génération des récépissés officiels PDF."""

    # Couleurs officielles du Togo
    COLOR_RED = colors.HexColor('#D21034')
    COLOR_YELLOW = colors.HexColor('#FFCE00')
    COLOR_GREEN = colors.HexColor('#006B3F')
    COLOR_WHITE = colors.white
    COLOR_DARK = colors.HexColor('#1a1a2e')
    COLOR_GRAY = colors.HexColor('#6B7280')
    COLOR_LIGHT_GRAY = colors.HexColor('#F3F4F6')

    @classmethod
    def generate_receipt(cls, declaration) -> 'Receipt':
        """Génère le récépissé complet pour une déclaration validée."""
        from documents.models import Receipt

        # Créer ou récupérer le récépissé
        receipt, created = Receipt.objects.get_or_create(
            declaration=declaration,
            defaults={
                'issued_by': declaration.validated_by,
                'expires_at': (timezone.now() + timedelta(days=90)).date(),
            }
        )

        # Générer le QR Code
        qr_data = cls._generate_qr_data(declaration)
        qr_image_path = cls._generate_qr_image(declaration, qr_data)

        # Générer la signature numérique
        signature = cls._generate_digital_signature(declaration)

        # Générer le PDF
        pdf_buffer = cls._generate_pdf(declaration, receipt, qr_image_path, signature)

        # Sauvegarder le PDF
        from django.core.files.base import ContentFile
        receipt.file.save(
            f'recepisse-{declaration.declaration_number}.pdf',
            ContentFile(pdf_buffer.getvalue()),
            save=False,
        )

        if qr_image_path:
            try:
                with open(qr_image_path, 'rb') as qr_file:
                    receipt.qr_code_image.save(
                        f'qr-{declaration.declaration_number}.png',
                        ContentFile(qr_file.read()),
                        save=False,
                    )
            finally:
                try:
                    os.unlink(qr_image_path)
                except OSError:
                    pass

        receipt.qr_code_data = qr_data
        receipt.digital_signature = signature
        receipt.save()

        # Mettre à jour la déclaration
        declaration.receipt_generated = True
        declaration.receipt_generated_at = timezone.now()
        declaration.receipt_file = receipt.file
        declaration.save(update_fields=['receipt_generated', 'receipt_generated_at', 'receipt_file'])

        return receipt

    @classmethod
    def _generate_qr_data(cls, declaration) -> str:
        """Génère les données du QR Code."""
        base_url = getattr(settings, 'QR_CODE_BASE_URL', 'https://pertedocs.tg/verification/')
        return f'{base_url}{declaration.verification_token}'

    @classmethod
    def _generate_qr_image(cls, declaration, qr_data: str) -> str | None:
        """Génère l'image QR Code et retourne son chemin temporaire."""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=4,
                border=2,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(
                fill_color='#006B3F',
                back_color='white'
            )
            fd, temp_path = tempfile.mkstemp(suffix='.png', prefix='qr_')
            os.close(fd)
            img.save(temp_path, format='PNG')
            return temp_path
        except Exception as e:
            logger.error(f'Erreur génération QR Code: {e}')
            return None

    @classmethod
    def _generate_digital_signature(cls, declaration) -> str:
        """Génère une signature numérique pour le récépissé."""
        data = (
            f'{declaration.declaration_number}'
            f'{declaration.full_name}'
            f'{declaration.document_type.name if declaration.document_type else ""}'
            f'{declaration.processed_at}'
            f'{settings.SECRET_KEY[:20]}'
        )
        return hashlib.sha256(data.encode()).hexdigest()[:32].upper()

    @classmethod
    def _generate_pdf(cls, declaration, receipt, qr_image_path: str, signature: str) -> io.BytesIO:
        """Génère le PDF du récépissé."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=1.5*cm,
            bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        story = []

        # ── En-tête ───────────────────────────────────────────────────────────
        story.extend(cls._build_header(declaration, styles))

        # ── Bande de titre ────────────────────────────────────────────────────
        story.extend(cls._build_title_section(declaration, styles))

        # ── Informations du récépissé ─────────────────────────────────────────
        story.extend(cls._build_receipt_info(declaration, receipt, styles))

        # ── Informations du déclarant ─────────────────────────────────────────
        story.extend(cls._build_declarant_info(declaration, styles))

        # ── Informations sur le document ──────────────────────────────────────
        story.extend(cls._build_document_info(declaration, styles))

        # ── Circonstances ─────────────────────────────────────────────────────
        story.extend(cls._build_circumstances(declaration, styles))

        # ── Section QR Code + Signature ───────────────────────────────────────
        story.extend(cls._build_verification_section(declaration, receipt, qr_image_path, signature, styles))

        # ── Pied de page ──────────────────────────────────────────────────────
        story.extend(cls._build_footer(declaration, styles))

        doc.build(story, onFirstPage=cls._add_watermark, onLaterPages=cls._add_watermark)
        buffer.seek(0)
        return buffer

    @classmethod
    def _build_header(cls, declaration, styles) -> list:
        """Construit l'en-tête du récépissé."""
        elements = []

        # Tableau en-tête avec drapeaux et logo
        header_data = [[
            Paragraph('<b>REPUBLIQUE TOGOLAISE</b><br/><font size="8">Travail – Liberté – Patrie</font>',
                      ParagraphStyle('header_left', fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold')),
            Paragraph('<b>MINISTÈRE DE LA SÉCURITÉ ET DE LA PROTECTION CIVILE</b><br/>'
                      '<font size="7">Direction Générale de la Documentation Nationale</font>',
                      ParagraphStyle('header_center', fontSize=9, alignment=TA_CENTER)),
            Paragraph('<b>PerteDocsTG</b><br/><font size="7">Plateforme Nationale</font>',
                      ParagraphStyle('header_right', fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold')),
        ]]

        header_table = Table(header_data, colWidths=[5*cm, 9*cm, 3.5*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(header_table)

        # Ligne de séparation tricolore
        elements.append(Spacer(1, 3*mm))
        elements.append(cls._tricolor_separator())
        elements.append(Spacer(1, 5*mm))

        return elements

    @classmethod
    def _tricolor_separator(cls):
        """Crée une ligne tricolore du drapeau togolais."""
        data = [[' ', ' ', ' ']]
        table = Table(data, colWidths=[5.83*cm, 5.83*cm, 5.83*cm], rowHeights=[4*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), cls.COLOR_GREEN),
            ('BACKGROUND', (1, 0), (1, 0), cls.COLOR_YELLOW),
            ('BACKGROUND', (2, 0), (2, 0), cls.COLOR_RED),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return table

    @classmethod
    def _build_title_section(cls, declaration, styles) -> list:
        """Titre principal du récépissé."""
        elements = []

        title_style = ParagraphStyle(
            'receipt_title',
            fontSize=14,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            textColor=cls.COLOR_WHITE,
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            'receipt_subtitle',
            fontSize=10,
            alignment=TA_CENTER,
            textColor=cls.COLOR_WHITE,
        )

        title_data = [[
            Paragraph('RÉCÉPISSÉ DE DÉCLARATION DE PERTE', title_style),
        ], [
            Paragraph(f'Document : {declaration.document_type.name.upper()}', subtitle_style),
        ]]

        title_table = Table(title_data, colWidths=[17.5*cm])
        title_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), cls.COLOR_GREEN),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(title_table)
        elements.append(Spacer(1, 5*mm))
        return elements

    @classmethod
    def _build_receipt_info(cls, declaration, receipt, styles) -> list:
        """Informations de référence du récépissé."""
        elements = []

        label_style = ParagraphStyle('label', fontSize=8, fontName='Helvetica-Bold', textColor=cls.COLOR_GRAY)
        value_style = ParagraphStyle('value', fontSize=9, fontName='Helvetica-Bold', textColor=cls.COLOR_DARK)

        data = [
            [
                Paragraph('N° DÉCLARATION', label_style),
                Paragraph(declaration.declaration_number, ParagraphStyle('num', fontSize=11, fontName='Helvetica-Bold', textColor=cls.COLOR_GREEN)),
                Paragraph('N° RÉCÉPISSÉ', label_style),
                Paragraph(receipt.receipt_number, value_style),
            ],
            [
                Paragraph('DATE D\'ÉMISSION', label_style),
                Paragraph(timezone.now().strftime('%d/%m/%Y à %H:%M'), value_style),
                Paragraph('VALIDE JUSQU\'AU', label_style),
                Paragraph(receipt.expires_at.strftime('%d/%m/%Y') if receipt.expires_at else 'N/A', value_style),
            ],
        ]

        table = Table(data, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), cls.COLOR_LIGHT_GRAY),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, cls.COLOR_GRAY),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 4*mm))
        return elements

    @classmethod
    def _build_declarant_info(cls, declaration, styles) -> list:
        """Section informations personnelles du déclarant."""
        elements = []

        section_style = ParagraphStyle('section', fontSize=10, fontName='Helvetica-Bold',
                                       textColor=cls.COLOR_WHITE, alignment=TA_LEFT)

        # Titre section
        section_title = Table([[Paragraph(' INFORMATIONS DU DÉCLARANT', section_style)]],
                               colWidths=[17.5*cm])
        section_title.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), cls.COLOR_RED),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(section_title)
        elements.append(Spacer(1, 2*mm))

        # Données du déclarant
        lbl = ParagraphStyle('lbl', fontSize=8, fontName='Helvetica-Bold', textColor=cls.COLOR_GRAY)
        val = ParagraphStyle('val', fontSize=9)

        data = [
            [Paragraph('Nom et Prénom', lbl), Paragraph(declaration.full_name, val),
             Paragraph('Date de naissance', lbl), Paragraph(declaration.date_of_birth.strftime('%d/%m/%Y'), val)],
            [Paragraph('Lieu de naissance', lbl), Paragraph(declaration.place_of_birth, val),
             Paragraph('Nationalité', lbl), Paragraph(declaration.nationality, val)],
            [Paragraph('Téléphone', lbl), Paragraph(declaration.phone, val),
             Paragraph('Email', lbl), Paragraph(declaration.email, val)],
            [Paragraph('Profession', lbl), Paragraph(declaration.profession or '-', val),
             Paragraph('Adresse', lbl), Paragraph(declaration.address[:50], val)],
        ]

        table = Table(data, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5.5*cm])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [cls.COLOR_WHITE, cls.COLOR_LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E5E7EB')),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 4*mm))
        return elements

    @classmethod
    def _build_document_info(cls, declaration, styles) -> list:
        """Section informations sur le document perdu."""
        elements = []

        section_style = ParagraphStyle('section', fontSize=10, fontName='Helvetica-Bold',
                                       textColor=cls.COLOR_WHITE)
        section_title = Table([[Paragraph(' DOCUMENT PERDU', section_style)]], colWidths=[17.5*cm])
        section_title.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), cls.COLOR_RED),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(section_title)
        elements.append(Spacer(1, 2*mm))

        lbl = ParagraphStyle('lbl', fontSize=8, fontName='Helvetica-Bold', textColor=cls.COLOR_GRAY)
        val = ParagraphStyle('val', fontSize=9)

        data = [
            [Paragraph('Type de document', lbl), Paragraph(declaration.document_type.name, val),
             Paragraph('Numéro', lbl), Paragraph(declaration.document_number or 'N/A', val)],
            [Paragraph('Date de délivrance', lbl),
             Paragraph(declaration.document_issue_date.strftime('%d/%m/%Y') if declaration.document_issue_date else 'N/A', val),
             Paragraph('Lieu de délivrance', lbl), Paragraph(declaration.document_issue_place or 'N/A', val)],
            [Paragraph('Date de perte', lbl), Paragraph(declaration.loss_date.strftime('%d/%m/%Y'), val),
             Paragraph('Lieu de perte', lbl), Paragraph(declaration.loss_place[:50], val)],
        ]

        table = Table(data, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5.5*cm])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [cls.COLOR_WHITE, cls.COLOR_LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E5E7EB')),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 4*mm))
        return elements

    @classmethod
    def _build_circumstances(cls, declaration, styles) -> list:
        """Section circonstances de la perte."""
        elements = []

        section_style = ParagraphStyle('section', fontSize=10, fontName='Helvetica-Bold', textColor=cls.COLOR_WHITE)
        section_title = Table([[Paragraph(' CIRCONSTANCES DE LA PERTE', section_style)]], colWidths=[17.5*cm])
        section_title.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), cls.COLOR_RED),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(section_title)
        elements.append(Spacer(1, 2*mm))

        desc_style = ParagraphStyle('desc', fontSize=9, leading=13)
        desc_text = declaration.loss_circumstances[:300] + ('...' if len(declaration.loss_circumstances) > 300 else '')
        elements.append(Paragraph(desc_text, desc_style))
        elements.append(Spacer(1, 4*mm))
        return elements

    @classmethod
    def _make_qr_flowable(cls, qr_image_path: str | None, styles):
        """Crée un flowable QR Code dimensionné pour ReportLab."""
        if qr_image_path and os.path.exists(qr_image_path):
            with open(qr_image_path, 'rb') as qr_file:
                qr_data = qr_file.read()
            qr_img = Image(io.BytesIO(qr_data), width=2.5 * cm, height=2.5 * cm)
            qr_img.hAlign = 'CENTER'
            return qr_img
        return Paragraph('[QR Code]', styles['Normal'])

    @classmethod
    def _build_verification_section(cls, declaration, receipt, qr_image_path, signature, styles) -> list:
        """Section QR Code et signature électronique."""
        elements = []

        qr_img = cls._make_qr_flowable(qr_image_path, styles)
        scan_hint = Paragraph(
            '<font size="7">Scannez pour vérifier l\'authenticité</font>',
            ParagraphStyle('scan_hint', fontSize=7, alignment=TA_CENTER, textColor=cls.COLOR_GRAY),
        )

        sig_style = ParagraphStyle('sig', fontSize=8, textColor=cls.COLOR_DARK, leading=12)
        right_content = Paragraph(
            f'<b>Cachet et Signature Électronique</b><br/><br/>'
            f'Le Directeur Général<br/><br/>'
            f'<font size="7">Code de vérification :<br/>'
            f'{signature}</font><br/><br/>'
            f'<font size="7">Vérifié le {timezone.now().strftime("%d/%m/%Y à %H:%M")}</font>',
            sig_style,
        )

        honor_style = ParagraphStyle('honor', fontSize=7, textColor=cls.COLOR_DARK, leading=11)
        honor_text = Paragraph(
            'Je soussigné(e), <b>{}</b>, certifie sur l\'honneur que les informations '
            'ci-dessus sont exactes et sincères, et que j\'ai bien perdu le document mentionné. '
            'Cette déclaration a été faite en date du {}.'.format(
                declaration.full_name,
                declaration.submitted_at.strftime('%d/%m/%Y') if declaration.submitted_at else timezone.now().strftime('%d/%m/%Y')
            ),
            honor_style,
        )

        elements.append(Spacer(1, 4*mm))
        elements.append(cls._tricolor_separator())
        elements.append(Spacer(1, 3*mm))

        # QR à gauche, textes à droite — pas de KeepTogether (bug ReportLab avec Image)
        final_table = Table(
            [[qr_img, honor_text, right_content]],
            colWidths=[3.2 * cm, 8.3 * cm, 5 * cm],
        )
        final_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('ALIGN', (2, 0), (2, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 1, cls.COLOR_GREEN),
            ('LINEAFTER', (0, 0), (0, 0), 0.5, cls.COLOR_GRAY),
            ('LINEAFTER', (1, 0), (1, 0), 0.5, cls.COLOR_GRAY),
            ('BACKGROUND', (0, 0), (-1, -1), cls.COLOR_LIGHT_GRAY),
        ]))
        elements.append(final_table)
        elements.append(Spacer(1, 2*mm))
        elements.append(scan_hint)
        return elements

    @classmethod
    def _build_footer(cls, declaration, styles) -> list:
        """Pied de page."""
        elements = []
        elements.append(Spacer(1, 4*mm))
        footer_style = ParagraphStyle('footer', fontSize=7, textColor=cls.COLOR_GRAY, alignment=TA_CENTER)
        elements.append(Paragraph(
            'Ce document a été généré électroniquement par la plateforme PerteDocsTG. '
            'Il est valide sans signature manuscrite. '
            'Pour vérifier l\'authenticité, scannez le QR Code ou consultez pertedocs.tg/verification/',
            footer_style,
        ))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            f'© République Togolaise - PerteDocsTG v1.0 | '
            f'Généré le {timezone.now().strftime("%d/%m/%Y à %H:%M")} | '
            f'Réf. {declaration.declaration_number}',
            footer_style,
        ))
        return elements

    @staticmethod
    def _add_watermark(canvas_obj, doc):
        """Ajoute un filigrane diagonal sur le PDF."""
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 60)
        canvas_obj.setFillColorRGB(0, 107, 63, alpha=0.04)
        canvas_obj.translate(A4[0] / 2, A4[1] / 2)
        canvas_obj.rotate(45)
        canvas_obj.drawCentredString(0, 0, 'PERTEDOCSTG')
        canvas_obj.restoreState()
