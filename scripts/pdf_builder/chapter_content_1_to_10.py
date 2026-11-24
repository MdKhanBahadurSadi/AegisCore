"""Chapters 1 to 10 for AEGISCORE AI Master Thesis Study Book.
"""

from __future__ import annotations

from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from .styles import (
    STYLE_H1, STYLE_H2, STYLE_H3, STYLE_BODY, STYLE_BODY_BOLD, STYLE_CODE,
    make_callout, make_feynman_box, make_checkpoint_box,
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_BG_LIGHT, COLOR_BORDER
)


def get_chapters_1_to_10():
    story = []

    # ==========================================
    # CHAPTER 1
    # ==========================================
    story.append(Paragraph("অধ্যায় ১: AEGISCORE AI পরিচিতি (Introduction & Core Mission)", STYLE_H1))
    story.append(Paragraph(
        "<b>AEGISCORE AI</b> হলো একটি কৃত্রিম বুদ্ধিমত্তা (AI) চালিত, প্রমাণ-ভিত্তিক (Evidence-Grounded) ওয়েব অ্যাপ্লিকেশন ভালনারেবিলিটি অ্যাসেসমেন্ট ইঞ্জিন। "
        "বর্তমান সাইবার সিকিউরিটি জগতে চিরাচরিত অটোমেটেড স্ক্যানারগুলো (যেমন OWASP ZAP, Nikto) রিজিড সিগনেচার দিয়ে কাজ করে, যা আধুনিক জটিল ওয়েব অ্যাপ্লিকেশনের কনটেক্সট এবং বিজনেস লজিক বুঝতে পারে না। "
        "অন্যদিকে, নতুন লার্জ ল্যাঙ্গুয়েজ মডেল (LLM) ভিত্তিক চ্যাটবটগুলো দারুণ যুক্তি দিতে পারলেও প্রায়শই মিথ্যা বা কাল্পনিক দুর্বলতা তৈরি করে (Hallucination)। "
        "AEGISCORE AI এই দুই প্রান্তিক সমস্যার একটি গাণিতিক ও সফটওয়্যার ইঞ্জিনিয়ারিং সমাধান।",
        STYLE_BODY
    ))

    story.append(make_feynman_box(
        concept_name="AEGISCORE AI প্ল্যাটফর্ম",
        simple_bangla="এটি এমন একটি বুদ্ধিমান সিকিউরিটি গার্ড সিস্টেম, যা সফটওয়্যারের কোনো দুর্বলতা খুঁজে পেলে নিজে আন্দাজে রিপোর্ট না করে শতভাগ চাক্ষুষ প্রমাণ (Evidence) মিলিয়ে তবেই রিপোর্ট করে।",
        analogy="একটি হাসপাতালের ফরেনসিক ল্যাবরেটরি। ডাক্তার রোগীর কথা শুনে আন্দাজে অপারেশন করেন না; রক্তের টেস্ট রিপোর্ট ও এক্স-রে প্লেটে রোগ নিশ্চিত না হওয়া পর্যন্ত তিনি কোনো চূড়ান্ত সিদ্ধান্ত নেন না।",
        tech_reality="সিস্টেমটি পাইথন ৩.১৩ ব্যাকএন্ড, ফাস্ট-এপিআই (FastAPI), এবং ফ্লাটার (Flutter M3) ইউজার ইন্টারফেসের সমন্বয়ে গঠিত। এটি ডিটারমিনিস্টিক সেফটি পলিসি, মাল্টি-এজেন্ট স্টেট মেশিন এবং আনসার্টেইনটি গেট ব্যবহার করে কাজ করে।",
        aegis_impl="aegiscore/safety.py, aegiscore/orchestration.py, এবং aegiscore/claim_validation.py-এর মাধ্যমে জিরো-হ্যালুসিনেশন আর্কিটেকচার নিশ্চিত করা হয়েছে।",
        viva_answer="AegisCore AI is an evidence-grounded multi-agent cybersecurity evaluation engine that combines deterministic safety controllers, specialist agent consensus, and calibrated uncertainty gating to eliminate false positives in automated web vulnerability assessment."
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "AegisCore AI কোনো সাধারণ চ্যাটবট নয়, এটি একটি প্রমাণ-ভিত্তিক মূল্যায়ন প্ল্যাটফর্ম।",
            "চিরাচরিত DAST টুলের দুর্বলতা এবং LLM-এর হ্যালুসিনেশন ঝুঁকি দূর করাই এর মূল লক্ষ্য।",
            "সিস্টেমে কন্ট্রোলার ছাড়া কোনো এআই এজেন্ট সরাসরি নেটওয়ার্ক কল করতে পারে না।"
        ],
        quiz_q="AegisCore AI-এর মূল স্বাতন্ত্র্য (Unique Selling Point) কী?",
        quiz_a="ডিটারমিনিস্টিক এভিডেন্স গ্রাউন্ডিং এবং এপিস্টেমিক আনসার্টেইনটি অ্যাবস্টেনশন গেট।",
        memory_tip="Aegis মানে ঢাল (Shield) + Core মানে মূল ভিত্তি = প্রমাণভিত্তিক সিকিউরিটির মূল ঢাল।"
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 2
    # ==========================================
    story.append(Paragraph("অধ্যায় ২: আমার Thesis-এর মূল সমস্যা (Problem Statement & Motivation)", STYLE_H1))
    story.append(Paragraph(
        "আধুনিক সফটওয়্যার সিস্টেমে প্রতি বছর হাজার হাজার নতুন সিকিউরিটি দুর্বলতা (CVE) যুক্ত হচ্ছে। এই দুর্বলতাগুলো সময়মতো শনাক্ত না করলে ডেটা লঙ্ঘন (Data Breach) ঘটে। "
        "বর্তমানে বাজারে থাকা সমাধানগুলোর প্রধান দুটি সীমাবদ্ধতা রয়েছে:",
        STYLE_BODY
    ))
    story.append(Paragraph("<b>১. DAST টুলের অন্ধত্ব (Rigidity of DAST):</b> ZAP বা Burp Suite কেবল প্রি-ডিফাইন্ড পেলোড পাঠিয়ে রেসপন্স ম্যাচ করে। তারা মাল্টি-স্টেপ ওয়ার্কফ্লো বা অ্যাক্সেস কন্ট্রোলের জটিলতা অনুধাবন করতে পারে না।", STYLE_BODY))
    story.append(Paragraph("<b>২. জেনারেটিভ এআই-এর অলীক আত্মবিশ্বাস (LLM Overconfidence & Hallucination):</b> জিপিটি বা জেমিনি-র মতো মডেলগুলোকে সিকিউরিটি লগ দিলে তারা প্রায়ই সার্ভার এরর দেখে আন্দাজে বলে দেয় যে সেখানে আরসিই বা এসকিউএলআই আছে, যার কোনো প্রমাণ নেই।", STYLE_BODY))

    story.append(make_callout(
        "<b>গবেষণার তিনটি মূল প্রশ্ন (Research Questions):</b><br/>"
        "• <b>RQ1:</b> RAG এবং এভিডেন্স-ভেরিফিকেশন কি প্রচলিত পদ্ধতির তুলনায় ফলস পজিটিভ রেট (FPR) উল্লেখযোগ্যভাবে কমাতে পারে?<br/>"
        "• <b>RQ2:</b> আনসার্টেইনটি গেট প্রয়োগ করলে সিস্টেমের সামগ্রিক রিকল (Recall) বা কভারেজে কী ধরনের প্রভাব পড়ে?<br/>"
        "• <b>RQ3:</b> সিস্টেম কি তার অনিশ্চয়তা সঠিকভাবে পরিমাপ করতে সক্ষম (Confidence Calibration)?",
        title="RESEARCH QUESTIONS & HYPOTHESES"
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "থিসিসের মূল সমস্যা হলো সিকিউরিটি অ্যাসেসমেন্টে ফলস পজিটিভ এবং হ্যালুসিনেশন।",
            "আমরা তিনটি সুস্পষ্ট রিসার্চ কোয়েশ্চেন (RQ1, RQ2, RQ3) নির্ধারণ করেছি।",
            "অ্যাবস্টেনশন পলিসি সিস্টেমকে অনির্ভরযোগ্য অনুমান করা থেকে বিরত রাখে।"
        ],
        quiz_q="RQ1-এর মূল প্রতিপাদ্য কী?",
        quiz_a="এভিডেন্স ভেরিফিকেশন সিস্টেম ফলস পজিটিভ ভালনারেবিলিটি রিপোর্ট কমাতে পারে কি না তা যাচাই করা।",
        memory_tip="Problem = DAST is blind + LLM hallucinates ➔ AegisCore brings evidence."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 3
    # ==========================================
    story.append(Paragraph("অধ্যায় ৩: Cybersecurity একদম শুরু থেকে (Cybersecurity 101 to Advanced)", STYLE_H1))
    story.append(Paragraph(
        "সাইবার সিকিউরিটি বোঝার মূল চাবিকাঠি হলো <b>CIA Triad</b>: Confidentiality (গোপনীয়তা), Integrity (অবিকৃত অবস্থা), এবং Availability (সহজলভ্যতা)। "
        "একটি সিস্টেম তখনই নিরাপদ যখন এই তিনটি শর্ত সুরক্ষিত থাকে।",
        STYLE_BODY
    ))

    # Vulnerability comparison table
    vuln_data = [
        [Paragraph("<b>দুর্বলতার শ্রেণি</b>", STYLE_BODY_BOLD), Paragraph("<b>CWE কোড</b>", STYLE_BODY_BOLD), Paragraph("<b>বাস্তব জীবনের উদাহরণ</b>", STYLE_BODY_BOLD), Paragraph("<b>প্রতিরোধের উপায়</b>", STYLE_BODY_BOLD)],
        [Paragraph("SQL Injection (SQLi)", STYLE_BODY), Paragraph("CWE-89", STYLE_BODY), Paragraph("ব্যাংক স্লিপে চেকে অ্যাকাউন্টের পাশে 'OR 1=1' লিখে সব টাকা দাবি করা।", STYLE_BODY), Paragraph("Parameterized Queries / Prepared Statements", STYLE_BODY)],
        [Paragraph("Cross-Site Scripting (XSS)", STYLE_BODY), Paragraph("CWE-79", STYLE_BODY), Paragraph("নোটিশ বোর্ডে বিষাক্ত আঠা মাখিয়ে রাখা যা দর্শনার্থীদের হাত নষ্ট করে।", STYLE_BODY), Paragraph("Context-aware Output Encoding & CSP", STYLE_BODY)],
        [Paragraph("Broken Access Control", STYLE_BODY), Paragraph("CWE-862", STYLE_BODY), Paragraph("হোটেলে রুম ১০১-এর চাবি দিয়ে রুম ১০২-এর দরজা খুলে ঢুকে পড়া (IDOR)।", STYLE_BODY), Paragraph("Server-side Session & Role Verification", STYLE_BODY)],
    ]
    t_vuln = Table(vuln_data, colWidths=[110, 60, 180, 154])
    t_vuln.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_vuln)
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "CIA Triad সাইবার নিরাপত্তার মৌলিক ভিত্তিস্তম্ভ।",
            "SQLi ডাটাবেজ আক্রমণ করে, XSS ব্যবহারকারীর ব্রাউজার আক্রমণ করে, BAC অনুমোদন নীতি লঙ্ঘন করে।",
            "AegisCore এই তিনটি উচ্চ-ঝুঁকিপূর্ণ দুর্বলতা ক্লাসের ওপর কাজ করে।"
        ],
        quiz_q="IDOR কোন ক্যাটাগরির দুর্বলতা?",
        quiz_a="Broken Access Control (CWE-862 / OWASP Top 10 A01)।",
        memory_tip="CIA = Confidentiality (গোপন রাখা), Integrity (অটুট রাখা), Availability (পাওয়া যাওয়া)।"
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 4
    # ==========================================
    story.append(Paragraph("অধ্যায় ৪: AI, ML, Deep Learning ও LLM (AI Evolution)", STYLE_H1))
    story.append(Paragraph(
        "কৃত্রিম বুদ্ধিমত্তার ক্রমবিকাশ বোঝার জন্য স্তরগুলো নিচে তুলে ধরা হলো:<br/>"
        "<b>১. Artificial Intelligence (AI):</b> মেশিনের মাধ্যমে মানুষের মতো সিদ্ধান্ত নেওয়ার সাধারণ বিজ্ঞান।<br/>"
        "<b>২. Machine Learning (ML):</b> ডেটা থেকে প্যাটার্ন ও ফাংশন শিখে ভবিষ্যদ্বাণী করার অ্যালগরিদম (যেমন Decision Trees, SVM)।<br/>"
        "<b>৩. Deep Learning (DL):</b> বহুস্তরীয় নিউরাল নেটওয়ার্ক (Deep Neural Networks) ব্যবহার করে স্বয়ংক্রিয় ফিচার নিষ্কাশন।<br/>"
        "<b>৪. Large Language Models (LLM):</b> ট্রান্সফরমার (Transformer) আর্কিটেকচার এবং সেলফ-অ্যাটেনশন (Self-Attention) মেকানিজম ভিত্তিক বিশাল মডেল (বিলিয়ন প্যারামিটার), যা ভাষার সম্ভাব্য পরবর্তী শব্দ অনুমান করে।",
        STYLE_BODY
    ))

    story.append(make_feynman_box(
        concept_name="Large Language Model (LLM)",
        simple_bangla="একটি অতি-উন্নত স্বয়ংক্রিয় টাইপিং অ্যাসিস্ট্যান্ট, যা লাখ লাখ বই ও ইন্টারনেট পড়ে শিখেছে একটি শব্দের পর সবচেয়ে যুক্তিযুক্ত পরবর্তী শব্দ কী হতে পারে।",
        analogy="একজন লাইব্রেরিয়ান যিনি পৃথিবীর সব বই পড়েছেন। আপনি যদি তাকে কোনো গল্পের প্রথম লাইন বলেন, তিনি তার স্মৃতির ওপর ভিত্তি করে পরবর্তী পৃষ্ঠাগুলো বলে দিতে পারেন।",
        tech_reality="ট্রান্সফরমার আর্কিটেকচারের সেলফ-অ্যাটেনশন ম্যাট্রিক্স $Attention(Q,K,V) = softmax(\\frac{QK^T}{\\sqrt{d_k}})V$ ব্যবহার করে কনটেক্সচুয়াল রিলেশনশিপ গণনা করে।",
        aegis_impl="AegisCore-এ মডেল অ্যাডাপ্টার ইন্টারফেস (aegiscore/model_adapter.py) রাখা হয়েছে যাতে লোকাল বা ক্লাউড যেকোনো এলএলএম যুক্ত করা যায়।",
        viva_answer="An LLM is a probabilistic autoregressive model based on the Transformer architecture trained on massive text corpora to predict next-token distributions, functioning as the semantic reasoning engine in AegisCore."
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "AI ➔ ML ➔ Deep Learning ➔ LLM হলো ধারাবাহিক উপসেট।",
            "এলএলএম মূলত স্ট্যাটিস্টিক্যাল নেক্সট-টোকেন প্রিডিক্টর, স্বয়ংক্রিয় সত্য-মিথ্যা যাচাইকারী নয়।",
            "AegisCore মডেলের সম্ভাবনা-ভিত্তিক উত্তরকে ডিটারমিনিস্টিক চেক দিয়ে যাচাই করে।"
        ],
        quiz_q="LLM-এর সেলফ-অ্যাটেনশন মেকানিজম কী কাজ করে?",
        quiz_a="বাক্যের প্রতিটি শব্দের সাথে অন্য শব্দের প্রাসঙ্গিক সম্পর্ক ও গুরুত্ব গাণিতিকভাবে নির্ধারণ করে।",
        memory_tip="AI (বড় ছাতা) ➔ ML (লার্নিং) ➔ DL (নিউরাল নেট) ➔ LLM (ভাষা মডেল)।"
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 5
    # ==========================================
    story.append(Paragraph("অধ্যায় ৫: AI Agent কী এবং কীভাবে কাজ করে (Agentic AI vs Chatbots)", STYLE_H1))
    story.append(Paragraph(
        "সাধারণ চ্যাটবট এবং এআই এজেন্টের মধ্যে পার্থক্য আকাশ-পাতাল। চ্যাটবট শুধু প্যাসিভ উত্তর দেয়, কিন্তু এআই এজেন্ট <b>লক্ষ্য-নির্দিষ্ট (Goal-Oriented)</b> কাজ সম্পাদন করে। "
        "একটি এআই এজেন্ট মূলত চারটি উপাদানের সমন্বয়ে কাজ করে:<br/>"
        "• <b>Perception (উপলব্ধি):</b> পরিবেশ বা ইনপুট থেকে তথ্য গ্রহণ (যেমন HTTP Response দেখা)।<br/>"
        "• <b>Planning (পরিকল্পনা):</b> লক্ষ্য অর্জনের জন্য ধাপে ধাপে পদক্ষেপ তৈরি করা।<br/>"
        "• <b>Tool Calling / Action (টুল ব্যবহার):</b> স্বয়ংক্রিয়ভাবে ক্যালকুলেটর, সার্চ বা কাস্টম পার্সার চালানো।<br/>"
        "• <b>Memory & State (স্মৃতি ও অবস্থা):</b> পূর্বের ধাপের ফলাফল ট্র্যাকিং করা।",
        STYLE_BODY
    ))

    story.append(make_callout(
        "<b>AegisCore সেফটি ইনভেরিয়েন্ট:</b><br/>"
        "কোনো এআই এজেন্টকে সরাসরি শেল বা নেটওয়ার্ক অ্যাক্সেস দেওয়া হয়নি। এজেন্ট কেবল টাইপড সাজেশন (Typed Hypothesis) দিতে পারে। নেটওয়ার্ক প্যাকেট পাঠানোর একমাত্র অধিকার রয়েছে গার্ডেড এক্সিকিউটরের, তাও কন্ট্রোলারের পারমিট সাপেক্ষে।",
        title="ZERO-CAPABILITY AGENT POLICY"
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "এজেন্ট = এলএলএম ব্রেন + প্ল্যানিং + মেমরি + টুল এক্সেকিউশন।",
            "AegisCore-এ এজেন্টের ক্ষমতা ইচ্ছাকৃতভাবে সীমাবদ্ধ রাখা হয়েছে নিরাপত্তার স্বার্থে।",
            "টুল কলিংয়ের মাধ্যমে এজেন্ট কাঠামোগত JSON আউটপুট তৈরি করে।"
        ],
        quiz_q="চ্যাটবট এবং এজেন্টের প্রধান পার্থক্য কী?",
        quiz_a="এজেন্ট লক্ষ্য অর্জনের জন্য পরিবেশের সাথে ইন্টারঅ্যাক্ট করে এবং মাল্টি-স্টেপ টুল এক্সেকিউট করতে পারে।",
        memory_tip="Chatbot talks; Agent plans, uses tools, and acts."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 6
    # ==========================================
    story.append(Paragraph("অধ্যায় ৬: LangGraph ও Custom State Machine Architecture", STYLE_H1))
    story.append(Paragraph(
        "থিসিসের প্রাথমিক প্রপোজালে এবং আর্কিটেকচার নথিতে ল্যাংগ্রাফ (LangGraph)-এর উল্লেখ ছিল। কিন্তু বাস্তব কোডবেস অডিটে দেখা যায়, "
        "এক্সটার্নাল প্যাকেজের অতিরিক্ত ডিপেন্ডেন্সি এবং আন-ডিটারমিনিস্টিক আচরণ এড়াতে AegisCore AI সম্পূর্ণ পাইথনে নিজস্ব <b>Deterministic Typed State Machine</b> তৈরি করেছে (`aegiscore/orchestration.py`)।",
        STYLE_BODY
    ))

    # ASCII State diagram
    state_ascii = """
    [*] --> Requested
    Requested --> PolicyDenied (Invalid Scope/IP)
    Requested --> Mapping (Initial Allow)
    Mapping --> Planning
    Planning --> Executing (Permit Issued)
    Executing --> Analyzing (Observation Captured)
    Analyzing --> HumanReview (Conflict / Uncertainty)
    Analyzing --> Reporting (Checklist Passed)
    Analyzing --> Abstained (Insufficient Evidence)
    """
    story.append(Paragraph("<b>স্টেট ট্রানজিশন ফ্লো (ASCII State Machine):</b>", STYLE_H3))
    story.append(Paragraph(f"<pre>{state_ascii}</pre>", STYLE_CODE))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "ল্যাংগ্রাফ ড্রাফটে থাকলেও বাস্তবে কাস্টম পাইথন স্টেট মেশিন তৈরি করা হয়েছে।",
            "প্রতিটি স্টেট ট্রানজিশন কঠোরভাবে টাইপড এবং ফেইল-ক্লোজড (Fail-Closed)।",
            "যেকোনো পলিসি লঙ্ঘন বা অস্পষ্টতা সরাসরি টার্মিনাল ডিনাই বা অ্যাবস্টেনশনে যায়।"
        ],
        quiz_q="কেন ল্যাংগ্রাফ লাইব্রেরির বদলে কাস্টম স্টেট মেশিন ব্যবহার করা হলো?",
        quiz_a="ডিটারমিনিস্টিক স্টেট অডিট, জিরো এক্সটার্নাল ডিপেন্ডেন্সি এবং শতভাগ অফলাইন টেস্টেবিলিটির জন্য।",
        memory_tip="State Machine = কঠোর নিয়ম মেনে ধাপে ধাপে চলা ট্রাফিক সিগন্যাল।"
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 7
    # ==========================================
    story.append(Paragraph("অধ্যায় ৭: Multi-Agent Workflow & Specialist Roles", STYLE_H1))
    story.append(Paragraph(
        "AegisCore AI-এর কেন্দ্রবিন্দু হলো এর <b>Multi-Specialist Consensus Architecture</b>। একটি একক মডেলের ওপর নির্ভর না করে দায়িত্ব ভাগ করে দেওয়া হয়েছে:",
        STYLE_BODY
    ))
    story.append(Paragraph("• <b>Primary Specialist (SQLi, XSS, BAC Analyst):</b> টার্গেট রেসপন্স বিশ্লেষণ করে প্রাথমিক অনুমান এবং প্রমাণপত্রসহ ক্লেইম তৈরি করে।", STYLE_BODY))
    story.append(Paragraph("• <b>Adversarial Evidence Reviewer:</b> স্বাধীন বিরোধী পক্ষের ভূমিকা পালন করে। সে স্পেশালিস্টের যুক্তির ফাঁকফোকর খোঁজে এবং হ্যালুসিনেটেড টোকেন পেলে `REJECT` বা `CHALLENGE` ফ্ল্যাগ দেয়।", STYLE_BODY))
    story.append(Paragraph("• <b>Consensus Gate:</b> যদি উভয় বিশেষজ্ঞ একমত হয়, তবেই পরবর্তী ধাপে যায়। কোনো বিরোধ তৈরি হলে কনসেনসাস স্ট্যাটাস হয় `disagreement` এবং সিস্টেম `ABSTAIN` করে।", STYLE_BODY))

    story.append(make_feynman_box(
        concept_name="অ্যাডভারসারিয়াল রিভিউয়ার (Adversarial Reviewer)",
        simple_bangla="একজন খুঁতখুঁতে সমালোচক যিনি যেকোনো দাবির ভুল ধরার জন্য বসে থাকেন, যাতে কোনো ভুয়া রিপোর্ট বাইরে যেতে না পারে।",
        analogy="আদালতের বিপরীত পক্ষের উকিল। পুলিশ বা প্রসিকিউটর কোনো প্রমাণ দেখালে বিরোধী উকিল প্রতিটি প্রমাণের সত্যতা ও আইনি বৈধতা চ্যালেঞ্জ করেন।",
        tech_reality="specialist_roles.py-তে DeterministicEvidenceReviewerFake প্রতিটি সাইটেশন খণ্ডের অস্তিত্ব এবং ক্লায়েন্ট বনাম সার্ভার-সাইড স্যানিটাইজেশন অডিট করে।",
        aegis_impl="aegiscore/specialist_roles.py L45-120 এবং tests/test_multi_specialist_consensus.py-এর মাধ্যমে ৩৫টি টেস্টে ভেরিফায়েড।",
        viva_answer="The adversarial reviewer acts as a secondary verification agent that cross-examines proposed candidate findings, checking for quotation fidelity and conflicting hypotheses before consensus is reached."
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "মাল্টি-এজেন্ট সিস্টেমে প্রাইমারি অ্যানালিস্ট এবং অ্যাডভারসারিয়াল রিভিউয়ার থাকে।",
            "তাদের মধ্যে মতবিরোধ হলে সিস্টেম নিজে সিদ্ধান্ত না চাপিয়ে অ্যাবস্টেইন করে।",
            "এর ফলে ফলস পজিটিভ প্রায় শূন্যের কোঠায় নেমে আসে।"
        ],
        quiz_q="স্পেশালিস্টদের মধ্যে মতবিরোধ হলে AegisCore কী করে?",
        quiz_a="SPECIALIST_DISAGREEMENT রিজন কোড দিয়ে ABSTAIN বা FLAG_FOR_REVIEW স্টেটে যায়।",
        memory_tip="Specialist proposes, Reviewer challenges, Consensus decides."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 8
    # ==========================================
    story.append(Paragraph("অধ্যায় ৮: Full Project Architecture & Layered Design", STYLE_H1))
    story.append(Paragraph(
        "AegisCore AI একটি কঠোর ৭-স্তরীয় ডিফেন্স-ইন-ডেপথ (Defense-in-Depth) আর্কিটেকচার মেনে চলে। প্রতিটি লেয়ার সম্পূর্ণ আইসোলেটেড:",
        STYLE_BODY
    ))

    arch_layers = [
        [Paragraph("<b>লেয়ার নম্বর ও নাম</b>", STYLE_BODY_BOLD), Paragraph("<b>বাস্তবায়িত মডিউল</b>", STYLE_BODY_BOLD), Paragraph("<b>মূল দায়িত্ব ও সিকিউরিটি ইনভেরিয়েন্ট</b>", STYLE_BODY_BOLD)],
        [Paragraph("Layer 1: Presentation", STYLE_BODY), Paragraph("frontend/lib/ (Flutter)", STYLE_BODY), Paragraph("অপারেটর ড্যাশবোর্ড, ফাইন্ডিংস ও এভিডেন্স এক্সপ্লোরার; ডেমো/লাইভ মোড।", STYLE_BODY)],
        [Paragraph("Layer 2: API Gateway", STYLE_BODY), Paragraph("aegiscore/api/app.py", STYLE_BODY), Paragraph("লুপব্যাক (127.0.0.1) এনফোর্সমেন্ট; আর্গন-২ অথেনটিকেশন; রিড-অনলি গেটওয়ে।", STYLE_BODY)],
        [Paragraph("Layer 3: Safety Controller", STYLE_BODY), Paragraph("aegiscore/safety.py", STYLE_BODY), Paragraph("স্কোপ ফিল্টারিং, রিকোয়েস্ট বাজেট (Max 50), সিঙ্গেল-ইউজ ক্রিপ্টোগ্রাফিক পারমিট।", STYLE_BODY)],
        [Paragraph("Layer 4: Guarded Executor", STYLE_BODY), Paragraph("aegiscore/guarded_execution.py", STYLE_BODY), Paragraph("অনুমোদিত পারমিট ভক্ষণ ও সেফ লোকাল ল্যাব ডিসপ্যাচ (রেকর্ডিং ফেক)।", STYLE_BODY)],
        [Paragraph("Layer 5: RAG Runtime", STYLE_BODY), Paragraph("aegiscore/rag_runtime.py", STYLE_BODY), Paragraph("অনুমোদিত সিকিউরিটি কর্পাস (OWASP/MITRE) থেকে লেক্সিকাল রিট্রিভাল।", STYLE_BODY)],
        [Paragraph("Layer 6: Multi-Agent Engine", STYLE_BODY), Paragraph("aegiscore/orchestration.py", STYLE_BODY), Paragraph("স্পেশালিস্ট কনসেনসাস স্টেট মেশিন এবং আনসার্টেইনটি গেটিং।", STYLE_BODY)],
        [Paragraph("Layer 7: Persistence & Eval", STYLE_BODY), Paragraph("aegiscore/evaluation.py", STYLE_BODY), Paragraph("এসকিউলাইট স্টোর এবং উইলসন স্কোর কনফিডেন্স ইন্টারভাল গণনা।", STYLE_BODY)],
    ]
    t_arch = Table(arch_layers, colWidths=[120, 140, 244])
    t_arch.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "৭টি পৃথক লেয়ারের মাধ্যমে দায়িত্ব সম্পূর্ণ আলাদা রাখা হয়েছে।",
            "কোনো লেয়ার সরাসরি অন্য লেয়ারের অভ্যন্তরীণ স্টেট বাইপাস করতে পারে না।",
            "বাইরে থেকে সরাসরি ব্যাকএন্ড ডেটাবেজে প্রবেশের কোনো পথ নেই।"
        ],
        quiz_q="কেন আর্কিটেকচারে ডিফেন্স-ইন-ডেপথ নীতি অনুসরণ করা হয়েছে?",
        quiz_a="একটি লেয়ারে ত্রুটি হলেও যাতে অন্য লেয়ার সেফটি ধরে রাখতে পারে এবং সিস্টেম ফেইল-ক্লোজড থাকে।",
        memory_tip="7 Layers = UI ➔ API ➔ Safety ➔ Executor ➔ RAG ➔ Agent ➔ Storage."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 9
    # ==========================================
    story.append(Paragraph("অধ্যায় ৯: Frontend Architecture (Flutter M3 & Riverpod)", STYLE_H1))
    story.append(Paragraph(
        "ফ্রন্টএন্ডটি ডার্ট (Dart) এবং ফ্লাটার (Flutter Web/Desktop) দিয়ে নির্মিত, যার সাইজ ৮,৩৮৪ লাইন। "
        "এটি সাইবার সিকিউরিটি থিমযুক্ত ডার্ক স্লেট (`#0B0F19`) ইন্টারফেস প্রদান করে।",
        STYLE_BODY
    ))
    story.append(Paragraph("<b>মূল বৈশিষ্ট্যসমূহ:</b><br/>"
        "• <b>Riverpod v3 স্টেট ম্যানেজমেন্ট:</b> কম্পাইল-টাইম সেফটি নিশ্চিত করে এবং মেমরি লিক প্রতিরোধে অটো-ডিসপোজ ব্যবহার করে।<br/>"
        "• <b>GoRouter ন্যাভিগেশন:</b> ডিক্লোরেটিভ রাউটিং যার মাধ্যমে ড্যাশবোর্ড, ফাইন্ডিংস, এভিডেন্স এবং রিপোর্ট স্ক্রিনে যাওয়া যায়।<br/>"
        "• <b>Live vs Demo Mode টগল:</b> ব্যাকএন্ড সক্রিয় থাকলে লাইভ এপিআই থেকে ডেটা টানে; ব্যাকএন্ড বন্ধ থাকলে মক ডেমো ডেটা (`MockDemoData`) দিয়ে নিরাপদ প্রদর্শন করে।",
        STYLE_BODY
    ))

    story.append(make_callout(
        "<b>Frontend Safety Boundary:</b><br/>"
        "frontend/lib/services/api_aegiscore_repository.dart-এর লাইন ৪০-এ স্পষ্ট বলা আছে: supportsAssessmentSubmission => false। "
        "অর্থাৎ ফ্রন্টএন্ড থেকে ইচ্ছাকৃতভাবে লাইভ স্ক্যান ডিসপ্যাচ ব্লক রাখা হয়েছে যাতে কোনো অননুমোদিত ইউজার হঠাৎ করে আক্রমণ শুরু করতে না পারে।",
        title="FRONTEND SAFETY INVARIANT"
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "ফ্লাটার ফ্রন্টএন্ড Riverpod এবং GoRouter ব্যবহার করে কাঠামোগতভাবে তৈরি।",
            "লাইভ এবং ডেমো মোডের মধ্যে স্পষ্ট বিভাজন রয়েছে।",
            "ইউজার ইন্টারফেস থেকে কোনো স্বয়ংক্রিয় আক্রমণ কমান্ড পাঠানো যায় না।"
        ],
        quiz_q="লাইভ মোড এবং ডেমো মোডের মধ্যে পার্থক্য কী?",
        quiz_a="লাইভ মোড লোকাল ফাস্ট-এপিআই থেকে ডেটা আনে; ডেমো মোড সিন্থেটিক মক ডেটা দিয়ে ইউআই দেখায়।",
        memory_tip="Flutter = Riverpod State + Dark Slate UI + Safe Read-Only View."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 10
    # ==========================================
    story.append(Paragraph("অধ্যায় ১০: Backend Architecture (FastAPI & Python 3.13)", STYLE_H1))
    story.append(Paragraph(
        "ব্যাকএন্ডটি পাইথন ৩.১৩ এবং ফাস্ট-এপিআই (FastAPI) দিয়ে নির্মিত (`aegiscore/api/app.py` ও `routes.py`)। "
        "এর প্রধান দায়িত্ব হলো লোকাল স্টোরেজ থেকে ফলাফল রিড করা এবং নিরাপদ অথেনটিকেশন প্রদান করা।",
        STYLE_BODY
    ))
    story.append(Paragraph("<b>মূল সিকিউরিটি বৈশিষ্ট্য:</b><br/>"
        "• <b>লুপব্যাক রেস্ট্রিকশন মিডলওয়্যার:</b> `enforce_loopback_access` মিডলওয়্যার প্রতিটি ইনকামিং রিকোয়েস্টের ক্লায়েন্ট আইপি চেক করে। আইপি যদি `127.0.0.1` বা `::1` না হয়, সাথে সাথে HTTP 403 Forbidden ফিরিয়ে দেয়।<br/>"
        "• <b>আর্গন২আইডি (Argon2id) পাসওয়ার্ড হ্যাশিং:</b> মেমরি-হার্ড ক্রিপ্টোগ্রাফিক অ্যালগরিদম যা ব্রুট-ফোর্স আক্রমণ অসম্ভব করে তোলে।<br/>"
        "• <b>Pydantic v2 ইনপুট ভ্যালিডেশন:</b> প্রতিটি ডেটা টাইপ কড়াভাবে যাচাই করা হয়, যা এসকিউএলআই বা বাফার ওভারফ্লোর পথ বন্ধ করে।",
        STYLE_BODY
    ))

    story.append(make_checkpoint_box(
        what_learned=[
            "ব্যাকএন্ড শুধুমাত্র লোকালহোস্টে বাইন্ড করা (Loopback Only)।",
            "পাসওয়ার্ড সংরক্ষণে Argon2id ব্যবহার করা হয়েছে।",
            "ইনপুট ভ্যালিডেশনের দায়িত্বে রয়েছে Pydantic v2।"
        ],
        quiz_q="কেন ব্যাকএন্ডকে লুপব্যাকে সীমাবদ্ধ রাখা হয়েছে?",
        quiz_a="যাতে লোকাল নেটওয়ার্ক বা ইন্টারনেটের কোনো বহিরাগত ব্যক্তি প্ল্যাটফর্মের অ্যাক্সেস না পায়।",
        memory_tip="FastAPI = Pydantic Validation + Loopback Only + Argon2id Auth."
    ))
    story.append(PageBreak())

    return story
