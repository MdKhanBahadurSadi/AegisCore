"""ReportLab styling definitions, fonts, callout boxes, and custom widgets
for the AEGISCORE AI Master Thesis Study Book.
"""

from __future__ import annotations

import os
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, HRFlowable

# Fonts
FONTS_DIR = r"C:\Windows\Fonts"
vrinda_path = os.path.join(FONTS_DIR, "vrinda.ttf")
vrindab_path = os.path.join(FONTS_DIR, "vrindab.ttf")

if os.path.exists(vrinda_path) and os.path.exists(vrindab_path):
    pdfmetrics.registerFont(TTFont("Vrinda", vrinda_path))
    pdfmetrics.registerFont(TTFont("VrindaBold", vrindab_path))
    FONT_NORMAL = "Vrinda"
    FONT_BOLD = "VrindaBold"
else:
    FONT_NORMAL = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"

# Color Palette (Dark Slate Cyber Theme)
COLOR_PRIMARY = colors.HexColor("#0F172A")    # Slate 900
COLOR_SECONDARY = colors.HexColor("#1E3A8A")  # Blue 900
COLOR_ACCENT = colors.HexColor("#0284C7")     # Sky 600
COLOR_TEXT = colors.HexColor("#1E293B")       # Slate 800
COLOR_MUTED = colors.HexColor("#64748B")      # Slate 500
COLOR_BG_LIGHT = colors.HexColor("#F8FAFC")   # Slate 50
COLOR_BORDER = colors.HexColor("#E2E8F0")     # Slate 200
COLOR_SUCCESS = colors.HexColor("#059669")    # Emerald 600
COLOR_WARNING = colors.HexColor("#D97706")    # Amber 600
COLOR_DANGER = colors.HexColor("#DC2626")     # Red 600

# Base Stylesheet
_base = getSampleStyleSheet()

STYLE_TITLE = ParagraphStyle(
    "DocTitle",
    parent=_base["Title"],
    fontName=FONT_BOLD,
    fontSize=26,
    leading=32,
    textColor=COLOR_PRIMARY,
    alignment=1,  # Centered
    spaceAfter=15,
)

STYLE_SUBTITLE = ParagraphStyle(
    "DocSubTitle",
    parent=_base["Normal"],
    fontName=FONT_NORMAL,
    fontSize=14,
    leading=20,
    textColor=COLOR_SECONDARY,
    alignment=1,
    spaceAfter=25,
)

STYLE_H1 = ParagraphStyle(
    "Heading1_Custom",
    parent=_base["Heading1"],
    fontName=FONT_BOLD,
    fontSize=18,
    leading=24,
    textColor=COLOR_PRIMARY,
    spaceBefore=18,
    spaceAfter=10,
    keepWithNext=True,
)

STYLE_H2 = ParagraphStyle(
    "Heading2_Custom",
    parent=_base["Heading2"],
    fontName=FONT_BOLD,
    fontSize=13,
    leading=18,
    textColor=COLOR_SECONDARY,
    spaceBefore=12,
    spaceAfter=6,
    keepWithNext=True,
)

STYLE_H3 = ParagraphStyle(
    "Heading3_Custom",
    parent=_base["Heading3"],
    fontName=FONT_BOLD,
    fontSize=11,
    leading=15,
    textColor=COLOR_ACCENT,
    spaceBefore=8,
    spaceAfter=4,
    keepWithNext=True,
)

STYLE_BODY = ParagraphStyle(
    "Body_Custom",
    parent=_base["Normal"],
    fontName=FONT_NORMAL,
    fontSize=9.5,
    leading=14.5,
    textColor=COLOR_TEXT,
    spaceAfter=7,
)

STYLE_BODY_BOLD = ParagraphStyle(
    "BodyBold_Custom",
    parent=STYLE_BODY,
    fontName=FONT_BOLD,
)

STYLE_CODE = ParagraphStyle(
    "Code_Custom",
    parent=_base["Code"],
    fontName="Courier",
    fontSize=8,
    leading=11,
    textColor=colors.HexColor("#0F172A"),
    backColor=COLOR_BG_LIGHT,
    borderPadding=6,
    spaceAfter=8,
)

STYLE_CALLOUT_TEXT = ParagraphStyle(
    "Callout_Text",
    parent=STYLE_BODY,
    fontSize=9,
    leading=13.5,
    textColor=colors.HexColor("#0F172A"),
)

STYLE_VIVA_Q = ParagraphStyle(
    "Viva_Q",
    parent=STYLE_BODY,
    fontName=FONT_BOLD,
    fontSize=9.5,
    leading=14,
    textColor=COLOR_PRIMARY,
)

STYLE_VIVA_A = ParagraphStyle(
    "Viva_A",
    parent=STYLE_BODY,
    fontSize=9,
    leading=13.5,
    textColor=COLOR_TEXT,
)


def make_callout(text: str, title: str = "গুরুত্বপূর্ণ নোট / KEY CONCEPT", border_color=COLOR_ACCENT, bg_color=COLOR_BG_LIGHT) -> Table:
    """Create a styled callout box for pedagogical emphasis."""
    header = Paragraph(f"<b>{title}</b>", ParagraphStyle("H", parent=STYLE_BODY, fontName=FONT_BOLD, textColor=border_color, fontSize=10, leading=14))
    body = Paragraph(text, STYLE_CALLOUT_TEXT)
    content = [[header], [body]]
    t = Table(content, colWidths=[504])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def make_feynman_box(concept_name: str, simple_bangla: str, analogy: str, tech_reality: str, aegis_impl: str, viva_answer: str) -> Table:
    """Render a structured Feynman 8-step teaching block."""
    items = [
        [Paragraph(f"<b>FEYNMAN TEACHING BLOCK: {concept_name}</b>", ParagraphStyle("F1", parent=STYLE_BODY, fontName=FONT_BOLD, textColor=COLOR_SECONDARY, fontSize=10.5))],
        [Paragraph(f"<b>1. সহজ বাংলা সংজ্ঞা:</b> {simple_bangla}", STYLE_BODY)],
        [Paragraph(f"<b>2. বাস্তব জীবনের রূপক:</b> {analogy}", STYLE_BODY)],
        [Paragraph(f"<b>3. টেকনিক্যাল ব্যাখ্যা:</b> {tech_reality}", STYLE_BODY)],
        [Paragraph(f"<b>4. AegisCore AI বাস্তবায়ন:</b> {aegis_impl}", STYLE_BODY)],
        [Paragraph(f"<b>5. ভাইভাতে যেভাবে বলবেন (Viva Defense):</b> {viva_answer}", ParagraphStyle("FV", parent=STYLE_BODY, fontName=FONT_BOLD, textColor=COLOR_PRIMARY))],
    ]
    t = Table(items, colWidths=[504])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 1, COLOR_SECONDARY),
        ("LINEBEFORE", (0, 0), (0, -1), 4, COLOR_SECONDARY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def make_checkpoint_box(what_learned: list[str], quiz_q: str, quiz_a: str, memory_tip: str) -> Table:
    """Render an end-of-chapter knowledge checkpoint."""
    learned_bullets = "<br/>".join([f"• {x}" for x in what_learned])
    rows = [
        [Paragraph("<b>KNOWLEDGE CHECKPOINT & CONFIDENCE AUDIT</b>", ParagraphStyle("CK1", parent=STYLE_BODY, fontName=FONT_BOLD, textColor=COLOR_SUCCESS, fontSize=10))],
        [Paragraph(f"<b>কী শিখলাম (Key Learnings):</b><br/>{learned_bullets}", STYLE_BODY)],
        [Paragraph(f"<b>কুইজ (Self-Quiz):</b> {quiz_q}<br/><b>উত্তর:</b> {quiz_a}", STYLE_BODY)],
        [Paragraph(f"<b>মনে রাখার সহজ টেকনিক (Memory Anchor):</b> {memory_tip}", ParagraphStyle("CK2", parent=STYLE_BODY, fontName=FONT_BOLD, textColor=COLOR_PRIMARY))],
    ]
    t = Table(rows, colWidths=[504])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ECFDF5")),
        ("BOX", (0, 0), (-1, -1), 1, COLOR_SUCCESS),
        ("LINEBEFORE", (0, 0), (0, -1), 4, COLOR_SUCCESS),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t
