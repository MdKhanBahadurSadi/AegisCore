"""Master PDF Compiler for AEGISCORE AI Thesis Study Book.
Compiles all 30 chapters into a publication-ready PDF using ReportLab.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Ensure pdf_builder package can be imported
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pdf_builder.styles import (
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_ACCENT,
    COLOR_BG_LIGHT,
    COLOR_BORDER,
    COLOR_MUTED,
    FONT_NORMAL,
    FONT_BOLD,
    STYLE_TITLE,
    STYLE_SUBTITLE,
    STYLE_H1,
    STYLE_H2,
    STYLE_BODY,
    STYLE_BODY_BOLD,
)
from scripts.pdf_builder.chapter_content_1_to_10 import get_chapters_1_to_10
from scripts.pdf_builder.chapter_content_11_to_20 import get_chapters_11_to_20
from scripts.pdf_builder.chapter_content_21_to_26 import get_chapters_21_to_26
from scripts.pdf_builder.viva_questions_200 import get_viva_chapter
from scripts.pdf_builder.chapter_content_28_to_30 import get_chapters_28_to_30


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page count."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber > 1:
            self.saveState()
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#4B5563"))
            self.drawString(54, 750, "AEGISCORE AI: Master Thesis Defense Guide & Study Book")

            self.setFont("Helvetica", 8)
            self.drawRightString(612 - 54, 750, "M.Sc. / B.Sc. Cybersecurity Thesis")

            # Running Top Line
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.6)
            self.line(54, 742, 612 - 54, 742)

            # Running Bottom Line
            self.line(54, 48, 612 - 54, 48)

            # Footer
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(54, 36, "CONFIDENTIAL & ACADEMIC DEFENSE MANUAL — FOR THESIS USE ONLY")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(612 - 54, 36, page_text)
            self.restoreState()


def build_cover_page():
    story = []
    story.append(Spacer(1, 40))

    # Badge Box
    badge = Table(
        [[Paragraph("<b>ACADEMIC RESEARCH & THESIS DEFENSE MANUAL</b>", ParagraphStyle("B", parent=STYLE_BODY, fontName="Helvetica-Bold", textColor=colors.HexColor("#0284C7"), fontSize=9, alignment=1))]],
        colWidths=[320]
    )
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F9FF")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0284C7")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(badge)
    story.append(Spacer(1, 25))

    # Main Titles
    story.append(Paragraph("AEGISCORE AI", STYLE_TITLE))
    story.append(Paragraph("Complete Thesis Understanding, AI Agent, Cybersecurity & Defense Preparation", STYLE_SUBTITLE))

    tagline_style = ParagraphStyle("Tagline", parent=STYLE_BODY, fontName=FONT_BOLD, fontSize=13, leading=18, textColor=colors.HexColor("#059669"), alignment=1)
    story.append(Paragraph("সহজ বাংলা গাইড — Zero to Thesis Defense Ready", tagline_style))
    story.append(Spacer(1, 25))

    # Metadata Card
    meta_data = [
        [Paragraph("<b>Project Domain:</b>", STYLE_BODY_BOLD), Paragraph("AI-Powered Web Application Vulnerability Assessment", STYLE_BODY)],
        [Paragraph("<b>Technology Stack:</b>", STYLE_BODY_BOLD), Paragraph("Python 3.13, FastAPI, Flutter M3, Riverpod, SQLite, RAG Engine", STYLE_BODY)],
        [Paragraph("<b>Verification Status:</b>", STYLE_BODY_BOLD), Paragraph("<b>646 Unit/Contract Tests Passed (100%)</b> in 22.92 seconds", STYLE_BODY)],
        [Paragraph("<b>Codebase Size:</b>", STYLE_BODY_BOLD), Paragraph("14,243 lines Python Backend + 8,384 lines Flutter Frontend", STYLE_BODY)],
        [Paragraph("<b>Thesis Readiness Score:</b>", STYLE_BODY_BOLD), Paragraph("<b>82 / 100 (Grade: A-)</b> | Offline Verified Engineering Prototype", STYLE_BODY)],
        [Paragraph("<b>Governance Status:</b>", STYLE_BODY_BOLD), Paragraph("DEC-01 to DEC-08 Decision Gates Formally Cataloged", STYLE_BODY)],
        [Paragraph("<b>Publication Date:</b>", STYLE_BODY_BOLD), Paragraph("Academic Year 2026-2027", STYLE_BODY)],
    ]
    t_meta = Table(meta_data, colWidths=[150, 330])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 40))

    # Pedagogical Mission Note
    mission_text = (
        "<b>বইটির লক্ষ্য ও উদ্দেশ্য (Pedagogical Mission):</b><br/>"
        "এই বইটি কেবল মুখস্থ করার কোনো গাইড নয়। এটি শিক্ষার্থীকে জটিল প্রযুক্তিগত পরিভাষাগুলোর পেছনের যুক্তি, "
        "বাস্তব জীবনের রূপক এবং কোডবেসের বাস্তব বাস্তবায়ন বোঝাতে তৈরি। "
        "ফাইনম্যান টেকনিক (Feynman Technique) অনুসরণ করে প্রতিটি জটিল টপিক অত্যন্ত সহজ ভাষায় উপস্থাপন করা হয়েছে, "
        "যাতে পরীক্ষকদের যেকোনো অপ্রত্যাশিত প্রশ্ন শিক্ষার্থী শতভাগ আত্মবিশ্বাসের সাথে ডিফেন্ড করতে পারেন।"
    )
    p_mission = Table([[Paragraph(mission_text, STYLE_BODY)]], colWidths=[480])
    p_mission.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, COLOR_SECONDARY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(p_mission)

    story.append(PageBreak())
    return story


def build_table_of_contents():
    story = []
    story.append(Paragraph("সূচিপত্র (Table of Contents)", STYLE_H1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_SECONDARY, spaceBefore=4, spaceAfter=12))

    toc_items = [
        ("১. AEGISCORE AI পরিচিতি (Introduction & Mission)", "চ্যাপ্টার ১"),
        ("২. আমার Thesis-এর মূল সমস্যা (Problem Statement & RQ)", "চ্যাপ্টার ২"),
        ("৩. Cybersecurity একদম শুরু থেকে (CIA Triad & Threats)", "চ্যাপ্টার ৩"),
        ("৪. AI, ML, Deep Learning ও LLM (Evolution of AI)", "চ্যাপ্টার ৪"),
        ("৫. AI Agent কী এবং কীভাবে কাজ করে (Agentic AI vs Chatbots)", "চ্যাপ্টার ৫"),
        ("৬. LangGraph ও Custom State Machine Architecture", "চ্যাপ্টার ৬"),
        ("৭. Multi-Agent Workflow & Specialist Roles", "চ্যাপ্টার ৭"),
        ("৮. Full Project Architecture & Layered Design (7 Layers)", "চ্যাপ্টার ৮"),
        ("৯. Frontend Architecture (Flutter M3, Riverpod & UI)", "চ্যাপ্টার ৯"),
        ("১০. Backend Architecture (FastAPI, Python 3.13, Loopback)", "চ্যাপ্টার ১০"),
        ("১১. API Layer & REST Endpoints (Read-Only Gateways)", "চ্যাপ্টার ১১"),
        ("১২. Database & Local Persistence (SQLite Engine)", "চ্যাপ্টার ১২"),
        ("১৩. RAG (Retrieval-Augmented Generation) Architecture", "চ্যাপ্টার ১৩"),
        ("১৪. Vector Database ও Lexical Retrieval (ChromaDB vs SQLite)", "চ্যাপ্টার ১৪"),
        ("১৫. Vulnerability Assessment Engine (SQLi, XSS, BAC)", "চ্যাপ্টার ১৫"),
        ("১৬. OWASP Standards & Knowledge Corpus (ASVS, WSTG, CWE)", "চ্যাপ্টার ১৬"),
        ("১৭. Security Analysis of AegisCore Platform (Self-Audit)", "চ্যাপ্টার ১৭"),
        ("১৮. Source Code Deep-Dive (Key Modules & Logic)", "চ্যাপ্টার ১৮"),
        ("১৯. End-to-End Data Flow (User Click to Result)", "চ্যাপ্টার ১৯"),
        ("২০. Testing Framework & 646 Passing Tests", "চ্যাপ্টার ২০"),
        ("২১. Research Methodology & Hypotheses (RQ1, RQ2, RQ3)", "চ্যাপ্টার ২১"),
        ("২২. Experimentation, Benchmarking & Evaluation Protocol", "চ্যাপ্টার ২২"),
        ("২৩. Thesis Writing & Chapter-by-Chapter Guide", "চ্যাপ্টার ২৩"),
        ("২৪. Research Limitations & Supervisor Decision Register", "চ্যাপ্টার ২৪"),
        ("২৫. Future Improvements Roadmap (P0, P1, P2 Priorities)", "চ্যাপ্টার ২৫"),
        ("২৬. Thesis Defense Preparation Strategy (Facing Examiners)", "চ্যাপ্টার ২৬"),
        ("২৭. ২০০+ ভাইভা প্রশ্ন ও মডেল উত্তর (200+ Viva Defense Q&A)", "চ্যাপ্টার ২৭"),
        ("২৮. ডিফেন্স প্রেজেন্টেশন স্ক্রিপ্ট (3, 5, 10, 15 Minutes)", "চ্যাপ্টার ২৮"),
        ("২৯. সাইবার সিকিউরিটি ও এআই গ্লোসারি (Bilingual Glossary)", "চ্যাপ্টার ২৯"),
        ("৩০. ফাইনাল রিভিশন গাইড ও থিসিস রেডিনেস স্কোরকার্ড (82/100)", "চ্যাপ্টার ৩০"),
    ]

    toc_rows = []
    for title, ch_num in toc_items:
        toc_rows.append([
            Paragraph(f"<b>{title}</b>", STYLE_BODY),
            Paragraph(f"<b>{ch_num}</b>", ParagraphStyle("TOC_R", parent=STYLE_BODY, alignment=2, textColor=COLOR_MUTED))
        ])

    t_toc = Table(toc_rows, colWidths=[420, 84])
    t_toc.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_toc)
    story.append(PageBreak())
    return story


def generate_pdf():
    pdf_filename = "AEGISCORE_AI_MASTER_STUDY_BOOK.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    story = []

    print("Generating Cover Page...")
    story.extend(build_cover_page())

    print("Generating Table of Contents...")
    story.extend(build_table_of_contents())

    print("Generating Chapters 1 to 10...")
    story.extend(get_chapters_1_to_10())

    print("Generating Chapters 11 to 20...")
    story.extend(get_chapters_11_to_20())

    print("Generating Chapters 21 to 26...")
    story.extend(get_chapters_21_to_26())

    print("Generating Chapter 27 (Viva Q&A)...")
    story.extend(get_viva_chapter())

    print("Generating Chapters 28 to 30 (Presentation, Glossary & Readiness Score)...")
    story.extend(get_chapters_28_to_30())

    print(f"Building PDF document: {pdf_filename} with NumberedCanvas...")
    doc.build(story, canvasmaker=NumberedCanvas)

    file_size = os.path.getsize(pdf_filename)
    print(f"SUCCESS: {pdf_filename} generated successfully! Size: {file_size:,} bytes")
    return pdf_filename


if __name__ == "__main__":
    generate_pdf()
