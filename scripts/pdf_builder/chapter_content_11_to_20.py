"""Chapters 11 to 20 for AEGISCORE AI Master Thesis Study Book.
"""

from __future__ import annotations

from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from .styles import (
    STYLE_H1, STYLE_H2, STYLE_H3, STYLE_BODY, STYLE_BODY_BOLD, STYLE_CODE,
    make_callout, make_feynman_box, make_checkpoint_box,
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_BG_LIGHT
)


def get_chapters_11_to_20():
    story = []

    # ==========================================
    # CHAPTER 11
    # ==========================================
    story.append(Paragraph("অধ্যায় ১১: API Layer & Endpoints (FastAPI REST Contracts)", STYLE_H1))
    story.append(Paragraph(
        "AegisCore AI-এর এপিআই স্তরটি `aegiscore/api/routes.py`-এ সংজ্ঞায়িত। "
        "এটি একটি ক্লায়েন্ট-সার্ভার চুক্তির (Contract) মতো কাজ করে। এপিআইটি মূলত অফলাইন রান এবং মূল্যায়নের ফলাফল পড়ার জন্য উন্মুক্ত।",
        STYLE_BODY
    ))

    api_endpoints = [
        [Paragraph("<b>HTTP মেথড ও রাউট</b>", STYLE_BODY_BOLD), Paragraph("<b>রেসপন্স মডেল</b>", STYLE_BODY_BOLD), Paragraph("<b>বিবরণ ও উদ্দেশ্য</b>", STYLE_BODY_BOLD)],
        [Paragraph("GET /health", STYLE_BODY), Paragraph("HealthStatusResponse", STYLE_BODY), Paragraph("সিস্টেম সক্রিয় আছে কি না এবং লোকাল স্টোর পথ চেক করে।", STYLE_BODY)],
        [Paragraph("POST /auth/login", STYLE_BODY), Paragraph("LoginResponse", STYLE_BODY), Paragraph("ইউজারনেম ও পাসওয়ার্ড নিয়ে ৩২-বাইটের সুরক্ষিত বেয়ারার টোকেন দেয়।", STYLE_BODY)],
        [Paragraph("GET /dashboard/summary", STYLE_BODY), Paragraph("DashboardSummary", STYLE_BODY), Paragraph("মোট ফাইন্ডিংস, সেশন সংখ্যা এবং সেফটি স্ট্যাটাস প্রদান করে।", STYLE_BODY)],
        [Paragraph("GET /findings", STYLE_BODY), Paragraph("FindingPageResponse", STYLE_BODY), Paragraph("সংরক্ষিত সমস্ত দুর্বলতার পেজিনেটেড তালিকা দেয়।", STYLE_BODY)],
        [Paragraph("GET /findings/{id}", STYLE_BODY), Paragraph("StoredFindingDetail", STYLE_BODY), Paragraph("নির্দিষ্ট দুর্বলতার ক্লেইম, সাইটেশন এবং রিভিউয়ার নোট দেয়।", STYLE_BODY)],
        [Paragraph("GET /evidence/approved", STYLE_BODY), Paragraph("EvidencePageResponse", STYLE_BODY), Paragraph("শুধুমাত্র হিউম্যান-অ্যাপ্রুভড নলেজ বেস চাংকগুলো প্রদর্শন করে।", STYLE_BODY)],
        [Paragraph("GET /reports", STYLE_BODY), Paragraph("ReportPageResponse", STYLE_BODY), Paragraph("অফলাইন ইভ্যালুয়েশন হর্নেসের স্ট্যাটিস্টিক্যাল রিপোর্ট দেয়।", STYLE_BODY)],
    ]
    t_api = Table(api_endpoints, colWidths=[130, 130, 244])
    t_api.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_api)
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "এপিআই রাউটগুলো অফলাইন মূল্যায়নের ডেটা রিড করার জন্য তৈরি।",
            "লগইন এপিআই ৩২-বাইট ক্রিপ্টোগ্রাফিক হেক্স টোকেন রিটার্ন করে।",
            "লাইভ অ্যাটাক ডিসপ্যাচের কোনো এপিআই রাউট রাখা হয়নি।"
        ],
        quiz_q="কেন এপিআই-তে স্ক্যান ট্রিগার করার POST রাউট নেই?",
        quiz_a="অটোমেটেড আক্রমণ প্রতিরোধ এবং অফলাইন সেফটি পলিসি বজায় রাখার জন্য।",
        memory_tip="API = Read-Only Evaluation Gateways + Token Auth."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 12
    # ==========================================
    story.append(Paragraph("অধ্যায় ১২: Database & Local Persistence (SQLite Engine)", STYLE_H1))
    story.append(Paragraph(
        "AegisCore AI ডেটা সংরক্ষণের জন্য <b>SQLite3</b> ব্যবহার করে (`aegiscore/local_persistence.py`)। "
        "কেন বাহ্যিক ডাটাবেজ (Postgres/MySQL) বাদ দিয়ে SQLite বেছে নেওয়া হলো, তা থিসিস ডিফেন্সে অত্যন্ত গুরুত্বপূর্ণ একটি প্রশ্ন।",
        STYLE_BODY
    ))

    story.append(make_feynman_box(
        concept_name="SQLite লোকাল পারসিস্টেন্স",
        simple_bangla="একটি একক ফাইল যা কম্পিউটারের কোনো সার্ভার সফটওয়্যার ছাড়াই সম্পূর্ণ রিলেশনাল ডাটাবেজের মতো কাজ করে।",
        analogy="একটি পোর্টেবল অফিশিয়াল ফাইল ক্যাবিনেট। অফিসের বাইরে কোথাও গেলে সম্পূর্ণ ক্যাবিনেটটি একটি ব্যাগে ভরে নিয়ে যাওয়া যায় এবং খোলার সাথে সাথে সব ফাইল পাওয়া যায়।",
        tech_reality="এটি সি-লাইব্রেরিতে তৈরি সার্ভারলেস, জিরো-কনফিগারেশন অ্যাসিড (ACID) ট্রানজেকশনাল ডাটাবেজ। aegiscore.db ফাইলের মাধ্যমে সব অডিট রেকর্ড সংরক্ষণ করা হয়।",
        aegis_impl="LocalRecordStore ক্লাস সেশন, ফাইন্ডিংস, রিপোর্ট এবং মেট্রিক্স সংরক্ষণ করে। প্রতিবার ডেটা সেভ করার সময় SHA-256 ফিঙ্গারপ্রিন্ট ট্র্যাক করা হয়।",
        viva_answer="We chose SQLite because it provides zero-configuration ACID persistence in a single portable file, ensuring complete offline experimental reproducibility and cryptographic provenance tracking for research evaluation."
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "SQLite একটি সার্ভারলেস, সেলফ-কন্টেইন্ড রিলেশনাল ডাটাবেজ।",
            "এটি কোনো নেটওয়ার্ক পোর্ট উন্মুক্ত করে না, ফলে লোকাল অ্যাটাক সারফেস শূন্য থাকে।",
            "ডেটাবেজ ফাইলটির SHA-256 হ্যাশ দিয়ে ডেটাসেটের অবিকৃত অবস্থা প্রমাণ করা যায়।"
        ],
        quiz_q="SQLite-এর প্রধান গবেষণা সুবিধা কী?",
        quiz_a="একক ফাইলে অ্যাসিড ট্রানজেকশন এবং পূর্ণাঙ্গ অফলাইন রিপেয়ারিবিলিটি।",
        memory_tip="SQLite = Single File + Zero Network Ports + Pure Reproducibility."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 13
    # ==========================================
    story.append(Paragraph("অধ্যায় ১৩: RAG (Retrieval-Augmented Generation) Architecture", STYLE_H1))
    story.append(Paragraph(
        "<b>RAG</b> হলো এমন একটি স্থাপত্য পদ্ধতি যেখানে লার্জ ল্যাঙ্গুয়েজ মডেলকে কোনো প্রশ্নের উত্তর তৈরি করার আগে একটি নির্দিষ্ট নলেজ বেস থেকে প্রাসঙ্গিক তথ্য খুঁজে এনে দেওয়া হয়। "
        "RAG মূলত তিনটি সমস্যা সমাধান করে:<br/>"
        "১. <b>হ্যালুসিনেশন হ্রাস:</b> মডেল নিজের মনগড়া তথ্য না দিয়ে দেওয়া তথ্যের ওপর ভিত্তি করে উত্তর দেয়।<br/>"
        "২. <b>সাম্প্রতিক ও সুনির্দিষ্ট জ্ঞান:</b> মডেল ট্রেনিংয়ের বাইরে থাকা প্রাইভেট স্ট্যান্ডার্ড (যেমন কোম্পানির নিজস্ব সিকিউরিটি পলিসি) সরবরাহ করা যায়।<br/>"
        "৩. <b>উৎস যাচাইযোগ্যতা (Provenance):</b> উত্তরের প্রতিটি লাইনের পেছনে কোন পৃষ্ঠা থেকে তথ্য নেওয়া হয়েছে তার রেফারেন্স থাকে।",
        STYLE_BODY
    ))

    story.append(make_callout(
        "<b>AegisCore RAG পাইপলাইন:</b><br/>"
        "ডকুমেন্ট ইনজেশন ➔ ডিটারমিনিস্টিক চাংকিং (Chunking) ➔ হিউম্যান সোর্স রিভিউ ➔ অনুমোদিত ফিল্টারিং ➔ লেক্সিকাল বিএম২৫ রিট্রিভাল ➔ সাইটেশন ভ্যালিডেশন ➔ স্পেশালিস্ট প্রম্পট তৈরি।",
        title="AEGISCORE RAG PIPELINE FLOW"
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "RAG মডেলের স্মৃতিভ্রম বা হ্যালুসিনেশন প্রতিরোধ করে।",
            "চাংকিংয়ের মাধ্যমে বড় ডকুমেন্টকে ছোট ছোট অর্থপূর্ণ অংশে ভাগ করা হয়।",
            "AegisCore-এ অনুমোদিত নয় এমন কোনো নথি রিট্রিভাল পাইপলাইনে ঢুকতে পারে না।"
        ],
        quiz_q="RAG কীভাবে হ্যালুসিনেশন কমায়?",
        quiz_a="মডেলের প্রম্পটে নির্ভরযোগ্য ডকুমেন্ট চাংক সরবরাহ করে এবং উত্তরের জন্য সাইটেশন বাধ্যবাধকতা আরোপ করে।",
        memory_tip="RAG = Retrieve Context ➔ Augment Prompt ➔ Generate Grounded Answer."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 14
    # ==========================================
    story.append(Paragraph("অধ্যায় ১৪: Vector Database ও Lexical Retrieval (ChromaDB vs SQLite)", STYLE_H1))
    story.append(Paragraph(
        "থিওরিটিক্যাল গবেষণায় ভেক্টর ডাটাবেজ (যেমন ChromaDB, Milvus) এবং এমবেডিংস মডেল ব্যবহার করে সিম্যান্টিক সার্চ (Semantic Search) করা হয়। "
        "কিন্তু AegisCore AI বাস্তবায়নে ভেক্টর ডাটাবেজের বদলে <b>লেক্সিকাল রিট্রিভার (Lexical Retriever)</b> বেছে নেওয়া হয়েছে। এটি একটি গুরুত্বপূর্ণ আর্কিটেকচারাল সিদ্ধান্ত।",
        STYLE_BODY
    ))

    db_comp = [
        [Paragraph("<b>তুলনার ক্ষেত্র</b>", STYLE_BODY_BOLD), Paragraph("<b>ভেক্টর ডাটাবেজ (ChromaDB)</b>", STYLE_BODY_BOLD), Paragraph("<b>AegisCore লেক্সিকাল রিট্রিভার (SQLite)</b>", STYLE_BODY_BOLD)],
        [Paragraph("সার্চের ধরন", STYLE_BODY), Paragraph("সিম্যান্টিক (অর্থের নৈকট্য বা কোসাইন সিমিলারিটি)", STYLE_BODY), Paragraph("লেক্সিকাল (শব্দ বা টোকেন ম্যাচিং / BM25)", STYLE_BODY)],
        [Paragraph("ডিপেন্ডেন্সি", STYLE_BODY), Paragraph("ভারী সি++ লাইব্রেরি ও ক্লাউড এমবেডিংস এপিআই", STYLE_BODY), Paragraph("জিরো ডিপেন্ডেন্সি, সম্পূর্ণ পাইথন স্ট্যান্ডার্ড লাইব্রেরি", STYLE_BODY)],
        [Paragraph("ডিটারমিনিজম", STYLE_BODY), Paragraph("ফ্লোটিং পয়েন্ট ভ্যারিয়েশন ও মডেল আপডেটে পরিবর্তনশীল", STYLE_BODY), Paragraph("১০০% ডিটারমিনিস্টিক ও বাইট-টু-বাইট রিপিটেবল", STYLE_BODY)],
        [Paragraph("অফলাইন ক্ষমতা", STYLE_BODY), Paragraph("এমবেডিং তৈরি করতে ইন্টারনেট বা লোকাল জিপিইউ লাগে", STYLE_BODY), Paragraph("সম্পূর্ণ অফলাইন, জিরো নেটওয়ার্ক বা জিপিইউ রিকোয়ারমেন্ট", STYLE_BODY)],
    ]
    t_comp = Table(db_comp, colWidths=[100, 200, 204])
    t_comp.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "ChromaDB ড্রাফটে থাকলেও অফলাইন ডিটারমিনিজমের জন্য লেক্সিকাল রিট্রিভাল ব্যবহৃত হয়েছে।",
            "ভেক্টর সার্চ নন-ডিটারমিনিস্টিক হতে পারে, যা বৈজ্ঞানিক গবেষণায় সমস্যা তৈরি করে।",
            "লেক্সিকাল সার্চে প্রতিটি টেস্ট প্রতিবার হুবহু একই ফলাফল দেয়।"
        ],
        quiz_q="কেন ভেক্টর ডাটাবেজের জায়গায় লেক্সিকাল রিট্রিভাল বেশি বৈজ্ঞানিক এই প্রজেক্টে?",
        quiz_a="কারণ এটি শতভাগ ডিটারমিনিস্টিক, অফলাইনে চলে এবং কোনো এক্সটার্নাল এপিআই বা জিপিইউ নির্ভরতা নেই।",
        memory_tip="Vector is probabilistic; Lexical is deterministic and reproducible."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 15
    # ==========================================
    story.append(Paragraph("অধ্যায় ১৫: Vulnerability Assessment Engine (SQLi, XSS, BAC Deep-Dive)", STYLE_H1))
    story.append(Paragraph(
        "AegisCore AI তিনটি প্রধান দুর্বলতার ওপর গভীর ডোমেন স্পেশালাইজেশন বাস্তবায়ন করেছে। নিচে প্রতিটি দুর্বলতার অ্যানাটমি তুলে ধরা হলো:",
        STYLE_BODY
    ))

    story.append(Paragraph("<b>১. SQL Injection (SQLi — CWE-89):</b><br/>"
        "• <i>আক্রমণ ভেক্টর:</i> `GET /rest/products/search?q=' OR 1=1 --`<br/>"
        "• <i>সিন্ক (Sink):</i> `models.sequelize.query()` ইন `routes/search.ts:32`<br/>"
        "• <i>সনাক্তকরণ প্রমাণ:</i> রেসপন্সে অপ্রত্যাশিতভাবে সকল প্রোডাক্টের ডেটা আসা অথবা ডাটাবেজ সিনট্যাক্স এরর (`SQLITE_ERROR`) প্রতিফলিত হওয়া।",
        STYLE_BODY
    ))

    story.append(Paragraph("<b>২. Cross-Site Scripting (XSS — CWE-79):</b><br/>"
        "• <i>আক্রমণ ভেক্টর:</i> `GET /vulnerabilities/xss_r/?name=<script>alert(1)</script>`<br/>"
        "• <i>সিন্ক (Sink):</i> `echo $_GET['name'];` ইন ডিভিডব্লিউএ `vulnerabilities/xss_r/source/low.php`<br/>"
        "• <i>সনাক্তকরণ প্রমাণ:</i> এইচটিটিপি রেসপন্স বডিতে আন-এনকোডেড স্ক্রিপ্ট ট্যাগের উপস্থিতি।",
        STYLE_BODY
    ))

    story.append(Paragraph("<b>৩. Broken Access Control (BAC / IDOR — CWE-862):</b><br/>"
        "• <i>আক্রমণ ভেক্টর:</i> `GET /rest/basket/5` (যেখানে লগইন করা ব্যবহারকারীর বাস্কেট আইডি ১)।<br/>"
        "• <i>সনাক্তকরণ প্রমাণ:</i> সার্ভার `403 Forbidden`-এর বদলে `200 OK` রিটার্ন করে অন্য ইউজারের বাস্কেট আইটেম প্রদর্শন করে।",
        STYLE_BODY
    ))

    story.append(make_checkpoint_box(
        what_learned=[
            "প্রতিটি দুর্বলতার একটি নির্দিষ্ট সোর্স (Source) এবং সিন্ক (Sink) থাকে।",
            "সিস্টেম শুধুমাত্র সার্ভার রেসপন্সের সুনির্দিষ্ট প্রমাণের ওপর ভিত্তি করে সিদ্ধান্ত নেয়।",
            "নেগেটিভ কন্ট্রোলে ডিফেন্সিভ কোডিংয়ের অস্তিত্ব যাচাই করা হয়।"
        ],
        quiz_q="SQL ইনজেকশন প্রতিরোধের সবচেয়ে নির্ভরযোগ্য উপায় কী?",
        quiz_a="প্যারামিটারাইজড কোয়েরি (Parameterized Queries / PreparedStatement)।",
        memory_tip="Source (ইনপুট আসে) ➔ Sanitizer (ফিল্টার করে) ➔ Sink (এক্সিকিউট হয়)।"
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 16
    # ==========================================
    story.append(Paragraph("অধ্যায় ১৬: OWASP Standards & Knowledge Corpus", STYLE_H1))
    story.append(Paragraph(
        "AegisCore AI-এর নলেজ বেসে ১১টি অফিশিয়াল সিকিউরিটি স্ট্যান্ডার্ড ডকুমেন্ট সংরক্ষিত রয়েছে (`knowledge_base/` ডিরেক্টরি)। "
        "এই ডকুমেন্টগুলো হলো সিস্টেমের <b>গ্রাউন্ড ট্রুথ পলিসি রেফারেন্স</b>।",
        STYLE_BODY
    ))
    story.append(Paragraph("• <b>OWASP WSTG v4.2 (Web Security Testing Guide):</b> ওয়েব সিকিউরিটি পরীক্ষার আন্তর্জাতিক স্ট্যান্ডার্ড। ফ্রেমওয়ার্ক, অথরাইজেশন ইনডেক্স ও ইনপুট ভ্যালিডেশন চ্যাপ্টার।<br/>"
        "• <b>OWASP ASVS v5.0 (Application Security Verification Standard):</b> V1 (এনকোডিং ও স্যানিটাইজেশন), V2 (ভ্যালিডেশন), এবং V8 (অথরাইজেশন)।<br/>"
        "• <b>OWASP Cheat Sheet Series:</b> XSS প্রিভেনশন এবং SQL ইনজেকশন প্রিভেনশন চিট শিট।<br/>"
        "• <b>MITRE CWE (Common Weakness Enumeration):</b> CWE-79, CWE-89, এবং CWE-862 এর অফিশিয়াল ডেফিনিশন ও মিটিগেশন গাইডলাইন।",
        STYLE_BODY
    ))

    story.append(make_callout(
        "<b>স্বচ্ছতা ও ইনভ্যারিয়েন্ট অডিট:</b><br/>"
        "docs/KNOWLEDGE_CORPUS.md অনুযায়ী, এই ১১টি ডকুমেন্ট বর্তমানে candidate স্ট্যাটাসে রয়েছে। "
        "কোনো ডকুমেন্ট এখনও সুপারভাইজার কর্তৃক ফরমাল APPROVED স্ট্যাম্প পায়নি। "
        "AegisCore-এর ফেইল-ক্লোজড নীতি অনুযায়ী, অ্যাপ্রুভাল না পাওয়া পর্যন্ত এগুলো রিট্রিভাল থেকে বাদ থাকে।",
        title="CORPUS GOVERNANCE INVARIANT"
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "নলেজ বেসে ১১টি বিশ্বমানের সিকিউরিটি স্ট্যান্ডার্ড সংরক্ষিত আছে।",
            "সব ডকুমেন্টকে নরমালাইজ করে কোড এক্সিকিউশন উদাহরণ বাদ দেওয়া হয়েছে।",
            "সুপারভাইজার অনুমোদন ছাড়া কোনো নথি এজেন্টের প্রম্পটে ঢুকতে পারে না।"
        ],
        quiz_q="ASVS এবং WSTG-এর মধ্যে পার্থক্য কী?",
        quiz_a="ASVS হলো ডেভেলপারদের জন্য সিকিউরিটি স্ট্যান্ডার্ড; WSTG হলো টেস্টারদের জন্য টেস্টিং গাইড।",
        memory_tip="OWASP = ওপেন গ্লোবাল স্ট্যান্ডার্ড; MITRE = ট্যাক্সোনমি ও ক্যাটালগ।"
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 17
    # ==========================================
    story.append(Paragraph("অধ্যায় ১৭: Security Analysis of AegisCore Platform (Self-Audit)", STYLE_H1))
    story.append(Paragraph(
        "একটি সিকিউরিটি টেস্টিং প্ল্যাটফর্মের নিজের নিরাপত্তা কেমন? থিসিস ডিফেন্সে এই বিষয়ে প্রশ্ন ওঠা অত্যন্ত স্বাভাবিক। "
        "আমরা আমাদের প্ল্যাটফর্মের চারটি সত্যানুসন্ধানী পর্যবেক্ষণ (Findings) তালিকাভুক্ত করেছি:",
        STYLE_BODY
    ))

    sec_audit = [
        [Paragraph("<b>আইডি</b>", STYLE_BODY_BOLD), Paragraph("<b>ফাইন্ডিং ও তীব্রতা</b>", STYLE_BODY_BOLD), Paragraph("<b>বাস্তব প্রমাণ ও প্রভাব</b>", STYLE_BODY_BOLD), Paragraph("<b>সুপারিশ ও বর্তমান অবস্থা</b>", STYLE_BODY_BOLD)],
        [Paragraph("SEC-01", STYLE_BODY), Paragraph("Missing Network Transport (HIGH)", STYLE_BODY), Paragraph("guarded_execution.py-তে কেবল ফেক ট্রান্সপোর্ট আছে; লাইভ প্যাকেট যায় না।", STYLE_BODY), Paragraph("ভবিষ্যতে আইসোলেটেড HTTP ট্রান্সপোর্ট যোগ করা। (DOCUMENTED GAP)", STYLE_BODY)],
        [Paragraph("SEC-02", STYLE_BODY), Paragraph("Unauthenticated Manifest (MED)", STYLE_BODY), Paragraph("সোর্স রিভিউয়ার নাম সাধারণ টেক্সট স্ট্রিং, ডিজিটাল সাইন নেই।", STYLE_BODY), Paragraph("GPG কি বা সেশন আইডি দিয়ে ম্যানিফেস্ট সাইন করা। (NEEDS IMPROVEMENT)", STYLE_BODY)],
        [Paragraph("SEC-03", STYLE_BODY), Paragraph("In-Memory Auth Tokens (LOW)", STYLE_BODY), Paragraph("সার্ভার রিস্টার্ট দিলে অপারেটরের অ্যাক্টিভ লগইন সেশন নষ্ট হয়ে যায়।", STYLE_BODY), Paragraph("টোকেন ডাটাবেজে এনক্রিপ্ট করে রাখা। (ACCEPTABLE FOR PROTOTYPE)", STYLE_BODY)],
        [Paragraph("SEC-04", STYLE_BODY), Paragraph("Loopback Only Boundary (INFO)", STYLE_BODY), Paragraph("শুধুমাত্র 127.0.0.1 থেকে এক্সেস করা যায়; দূরবর্তী আইপি ব্লকড।", STYLE_BODY), Paragraph("ডিজাইন অনুযায়ী নিরাপদ; বহিরাগত আক্রমণ অসম্ভব। (INTENDED DESIGN)", STYLE_BODY)],
    ]
    t_sec = Table(sec_audit, colWidths=[60, 140, 150, 154])
    t_sec.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_sec)
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "AegisCore নিজের সীমাবদ্ধতা সততার সাথে স্বীকার করে।",
            "সিস্টেমে লাইভ ট্রান্সপোর্ট বাদ রাখা হয়েছে অনিয়ন্ত্রিত আক্রমণ ঠেকাতে।",
            "লুপব্যাক মিডলওয়্যার বহিরাগত নেটওয়ার্ক আক্রমণ থেকে প্ল্যাটফর্মকে রক্ষা করে।"
        ],
        quiz_q="কেন প্ল্যাটফর্মে লাইভ নেটওয়ার্ক ট্রান্সপোর্ট ডিফল্টভাবে নিষ্ক্রিয়?",
        quiz_a="অনিচ্ছাকৃত বা অননুমোদিত লক্ষ্যবস্তুতে ট্র্যাফিক প্রেরণ রোধ করতে (সেফটি ফার্স্ট নীতি)।",
        memory_tip="Honest Audit = Admit gaps openly before examiners point them out."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 18
    # ==========================================
    story.append(Paragraph("অধ্যায় ১৮: Source Code Deep-Dive (Key Modules & Logic)", STYLE_H1))
    story.append(Paragraph(
        "AegisCore AI-এর ব্যাকএন্ডে মোট ২০টি মডিউল এবং ১৪,২৪৩ লাইন কোড রয়েছে। প্রধান মডিউলগুলোর কার্যকারিতা নিচে তুলে ধরা হলো:",
        STYLE_BODY
    ))
    story.append(Paragraph("• <b>aegiscore/safety.py (১,৩৭৭ লাইন):</b> PolicyEngine ক্লাস। `authorize()` মেথড ইনকামিং রিকোয়েস্টের origin, path এবং budget চেক করে ক্রিপ্টোগ্রাফিক পারমিট ইস্যু করে।", STYLE_BODY))
    story.append(Paragraph("• <b>aegiscore/claim_validation.py (৫৯৮ লাইন):</b> `validate_citation_excerpt()` ফাংশন। এটি দেখে এলএলএম-এর উদ্ধৃত টেক্সট আসল এভিডেন্স চাংকের সাবস্ট্রিং কি না। কমা বা স্পেসের অমিল হলেও রিজেক্ট করে।", STYLE_BODY))
    story.append(Paragraph("• <b>aegiscore/uncertainty_engine.py (৬৩২ লাইন):</b> `UncertaintyAggregationEngine` ক্লাস। বিভিন্ন ডিসঅর্ডিনেন্স সিগন্যাল যোগ করে `evidence_sufficiency_score` হিসাব করে এবং থ্রেশহোল্ডের নিচে নামলে অ্যাবস্টেইন করে।", STYLE_BODY))
    story.append(Paragraph("• <b>aegiscore/evaluation.py (১,৪৫৮ লাইন):</b> `compute_wilson_score_interval()` এবং `calculate_evaluation_scores()` ফাংশন। কনফিউশন ম্যাট্রিক্স এবং ৯৫% কনফিডেন্স ইন্টারভাল গণনা করে।", STYLE_BODY))

    story.append(make_checkpoint_box(
        what_learned=[
            "কোডবেস সম্পূর্ণ টাইপড এবং মডুলার।",
            "প্রতিটি ক্রিটিক্যাল লজিক একাধিক ইউনিট টেস্ট দ্বারা সুরক্ষিত।",
            "কোডে কোনো ডামি স্লিপ বা ব্যাকডোর রাখা হয়নি।"
        ],
        quiz_q="claim_validation.py ফাইলে কী ধরনের চেক করা হয়?",
        quiz_a="উদ্ধৃত সাইটেশন হুবহু র-এভিডেন্স টেক্সটের সাবস্ট্রিং কি না তা অক্ষর মিলিয়ে চেক করা হয়।",
        memory_tip="Safety controls dispatch, ClaimValidator controls truth, Uncertainty controls doubt."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 19
    # ==========================================
    story.append(Paragraph("অধ্যায় ১৯: End-to-End Data Flow (User Click to Result)", STYLE_H1))
    story.append(Paragraph(
        "একজন ব্যবহারকারী ফ্লাটার ফ্রন্টএন্ডে একটি ফাইন্ডিংসে ক্লিক করা থেকে শুরু করে স্ক্রিনে ফলাফল দেখা পর্যন্ত সম্পূর্ণ ডেটা ফ্লো নিচে বর্ণনা করা হলো:",
        STYLE_BODY
    ))
    flow_steps = [
        "১. ব্যবহারকারী ফ্লাটার স্ক্রিনে 'FIND-JS-01' বাটনে ক্লিক করেন।",
        "২. findings_screen.dart থেকে apiAegisCoreRepository-এর getStoredFindingById() মেথড কল হয়।",
        "৩. ব্যাকএন্ডে HTTP GET http://127.0.0.1:8000/findings/FIND-JS-01 রিকোয়েস্ট যায় Authorization: Bearer হেডারে।",
        "৪. FastAPI-এর enforce_loopback_access মিডলওয়্যার ক্লায়েন্ট আইপি 127.0.0.1 নিশ্চিত করে।",
        "৫. auth.py মডিউল মেমরিতে থাকা টোকেন স্টোরের সাথে মিলিয়ে ইউজার সেশন ভ্যালিডেট করে।",
        "৬. routes.py লোকাল SQLite স্টোরে কোয়েরি চালায়: SELECT data FROM findings WHERE finding_id = 'FIND-JS-01'।",
        "৭. SQLite থেকে ডাটা এনে Pydantic মডেলে রূপান্তর করে HTTP 200 OK রেসপন্স পাঠায়।",
        "৮. ফ্লাটার অ্যাপ JSON পার্স করে FindingModel তৈরি করে এবং স্ক্রিনে লাল ব্যাজসহ ডিটেইলস প্রদর্শন করে।"
    ]
    for s in flow_steps:
        story.append(Paragraph(s, STYLE_BODY))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "ডেটা ফ্লো ইউআই থেকে শুরু হয়ে এপিআই, অথেনটিকেশন এবং লোকাল স্টোরেজ ঘুরে আবার ইউআই-তে ফেরত আসে।",
            "প্রতিটি পদক্ষেপে এরর হ্যান্ডলিং ও টাইপ ভ্যালিডেশন সক্রিয় থাকে।",
            "কোনো অবস্থাতেই ব্যাকএন্ড ব্লক হয়ে ইউজার ইন্টারফেস ফ্রিজ হয় না।"
        ],
        quiz_q="ডেটা ফ্লোতে enforce_loopback_access মিডলওয়্যার কী ভূমিকা পালন করে?",
        quiz_a="যেকোনো বহিরাগত নেটওয়ার্ক রিকোয়েস্টকে এপিআই রাউটে পৌঁছানোর আগেই রিজেক্ট করে।",
        memory_tip="Click ➔ Riverpod ➔ HTTP ➔ Loopback Check ➔ Auth ➔ SQLite ➔ Screen."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 20
    # ==========================================
    story.append(Paragraph("অধ্যায় ২০: Testing Framework & 646 Passing Tests", STYLE_H1))
    story.append(Paragraph(
        "AegisCore AI-এর নির্ভরযোগ্যতার সবচেয়ে বড় প্রমাণ হলো এর বিশাল অটোমেটেড টেস্ট স্যুট। "
        "ব্যাকএন্ডে মোট <b>৩১টি টেস্ট ফাইলে ৬৪৬টি টেস্ট কেস</b> রয়েছে, যা শতভাগ সফলভাবে পাস করে (`646 passed in 22.92s`)।",
        STYLE_BODY
    ))

    test_summary = [
        [Paragraph("<b>টেস্ট ফাইল ক্যাটাগরি</b>", STYLE_BODY_BOLD), Paragraph("<b>টেস্ট সংখ্যা</b>", STYLE_BODY_BOLD), Paragraph("<b>কী ভেরিফাই করে</b>", STYLE_BODY_BOLD)],
        [Paragraph("Safety Policy & Permit Tests", STYLE_BODY), Paragraph("৮৪টি", STYLE_BODY), Paragraph("স্কোপ রেস্ট্রিকশন, পাবলিক আইপি রিজেকশন, বাজেট কাউন্টার ও পারমিট ল্যাচ।", STYLE_BODY)],
        [Paragraph("Claim Validation & Generation", STYLE_BODY), Paragraph("৪৫টি", STYLE_BODY), Paragraph("উদ্ধৃতি মিল, হ্যালুসিনেশন টোকেন চ্যালেঞ্জ এবং ফ্যাক্ট/হাইপোথিসিস ফিল্টারিং।", STYLE_BODY)],
        [Paragraph("Multi-Specialist & Consensus", STYLE_BODY), Paragraph("৭৪টি", STYLE_BODY), Paragraph("প্রাইমারি স্পেশালিস্ট ও অ্যাডভারসারিয়াল রিভিউয়ারের মতবিরোধ ও ঐক্যমত।", STYLE_BODY)],
        [Paragraph("Uncertainty Engine & Abstention", STYLE_BODY), Paragraph("৫০টি", STYLE_BODY), Paragraph("গাণিতিক স্কোরিং, পেনাল্টি ওয়েট এবং ফেইল-ক্লোজড অ্যাবস্টেনশন গেট।", STYLE_BODY)],
        [Paragraph("Evaluation Metrics & Scoring", STYLE_BODY), Paragraph("৭৯টি", STYLE_BODY), Paragraph("উইলসন কনফিডেন্স ইন্টারভাল, কনফিউশন ম্যাট্রিক্স ও জিরো-ডিনমিনেটর হ্যান্ডলিং।", STYLE_BODY)],
        [Paragraph("API & Persistence Tests", STYLE_BODY), Paragraph("৮৬টি", STYLE_BODY), Paragraph("লুপব্যাক ব্লক, আর্গন-২ লগইন, টোকেন মেয়াদ এবং এসকিউলাইট স্টোরেজ রিড।", STYLE_BODY)],
        [Paragraph("Catalog & Readiness Audits", STYLE_BODY), Paragraph("৬২টি", STYLE_BODY), Paragraph("৩৬টি টেস্ট কেসের ইন্টিগ্রিটি এবং সুপারভাইজার ডিসিশন গেট চেক।", STYLE_BODY)],
    ]
    t_test = Table(test_summary, colWidths=[150, 60, 294])
    t_test.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_test)
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "৬৪৬টি টেস্ট ২২ সেকেন্ডে সম্পূর্ণ অফলাইনে পাস করে।",
            "টেস্টে কোনো মক ডেটাবেজ বা ইন্টারনেট কানেকশনের প্রয়োজন হয় না।",
            "টেস্টগুলো প্রমাণ করে সফটওয়্যার কন্ট্রাক্ট এবং স্টেট মেশিন শতভাগ ত্রুটিমুক্ত।"
        ],
        quiz_q="৬৪৬টি টেস্ট কী প্রমাণ করে আর কী প্রমাণ করে না?",
        quiz_a="সফটওয়্যার কন্ট্রাক্ট এবং ম্যাথমেটিক্যাল স্কোরিং যে সঠিক তা প্রমাণ করে; কিন্তু লাইভ টার্গেটে ডিটেকশন রেট প্রমাণ করে না।",
        memory_tip="646 Passed Tests = Absolute Architectural & Contract Determinism."
    ))
    story.append(PageBreak())

    return story
