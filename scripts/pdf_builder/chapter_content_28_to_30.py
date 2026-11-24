"""Chapters 28 to 30 for AEGISCORE AI Master Thesis Study Book.
"""

from __future__ import annotations

from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from .styles import (
    STYLE_H1, STYLE_H2, STYLE_H3, STYLE_BODY, STYLE_BODY_BOLD, STYLE_CODE,
    make_callout, make_feynman_box, make_checkpoint_box,
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_BG_LIGHT
)


def get_chapters_28_to_30():
    story = []

    # ==========================================
    # CHAPTER 28
    # ==========================================
    story.append(Paragraph("অধ্যায় ২৮: ডিফেন্স প্রেজেন্টেশন স্ক্রিপ্ট (Thesis Defense Presentation Scripts)", STYLE_H1))
    story.append(Paragraph(
        "ডিফেন্সের সময় নির্ধারিত সময়ের মধ্যে বক্তব্য শেষ করা অত্যন্ত গুরুত্বপূর্ণ। "
        "নিচে ৩-মিনিট, ৫-মিনিট, ১০-মিনিট এবং ১৫-মিনিটের প্রেজেন্টেশনের জন্য হুবহু মুখস্থ উপযোগী স্ক্রিপ্ট প্রদান করা হলো:",
        STYLE_BODY
    ))

    story.append(Paragraph("<b>১. ৩-মিনিটের এলিভেটর পিচ স্ক্রিপ্ট (3-Minute Elevator Pitch):</b>", STYLE_H2))
    p3_text = (
        "<i>\"Honorable Committee Members and Respected Supervisor: Good morning. "
        "Today, I present <b>AEGISCORE AI</b>, an evidence-grounded multi-agent cybersecurity evaluation engine. "
        "In modern web security, automated testing faces a fundamental dilemma: traditional DAST scanners like OWASP ZAP fail to understand complex business logic, "
        "while emerging Large Language Models frequently suffer from hallucinations—fabricating false vulnerabilities without proof. "
        "AegisCore AI bridges this gap through three core innovations: "
        "First, a <b>Deterministic Scope Controller</b> that enforces single-use permits and strict loopback boundaries, ensuring no unapproved network packet is ever sent. "
        "Second, a <b>Multi-Agent Specialist State Machine</b> where primary vulnerability analysts are cross-examined by independent adversarial reviewers, eliminating ungrounded claims. "
        "Third, an <b>Epistemic Uncertainty Engine</b> that allows the AI to abstain when evidence is ambiguous, prioritizing high precision over noisy coverage. "
        "Our architecture is fully implemented across 14,000 lines of Python and Flutter, backed by 646 passing unit and contract tests. "
        "Thank you, and I am now ready for your questions.\"</i>"
    )
    story.append(Paragraph(p3_text, STYLE_BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>২. ৫-মিনিটের প্রেজেন্টেশন স্ক্রিপ্ট (5-Minute Pitch):</b>", STYLE_H2))
    p5_text = (
        "<i>\"Honorable Committee: "
        "Consider an enterprise web application where a single undetected SQL injection can lead to a catastrophic data breach, "
        "while hundreds of false-positive scanner alerts waste valuable engineering hours. "
        "This research asks a fundamental question: <b>Can we leverage the semantic reasoning of LLMs for vulnerability assessment without inheriting their dangerous hallucination risks?</b> "
        "To answer this, we developed AegisCore AI with a strict 'Controller Before Capability' architecture. "
        "Unlike commercial tools that give LLMs direct access to network sockets or shell tools, AegisCore treats the LLM strictly as an analytical advisor. "
        "Every assessment request is authorized by a deterministic policy engine; every factual claim must cite an exact verbatim excerpt from raw HTTP traffic; "
        "and any discordance between specialist agents immediately triggers a fail-closed abstention gate. "
        "We evaluated our framework against 36 benchmark cases across OWASP Juice Shop and DVWA using Wilson score confidence intervals. "
        "Our findings demonstrate that epistemic abstention significantly reduces selective risk, providing a robust foundation for trustworthy automated cybersecurity.\"</i>"
    )
    story.append(Paragraph(p5_text, STYLE_BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>৩. ১০-মিনিট প্রেজেন্টেশন স্লাইড আউটলাইন (10-Minute Slide Deck Outline):</b>", STYLE_H2))
    deck_outline = [
        "• <b>Slide 1 (Title):</b> AegisCore AI: Evidence-Grounded Multi-Agent Cybersecurity Evaluation Engine.",
        "• <b>Slide 2 (The Problem):</b> DAST Context Blindness vs. LLM Hallucination & Overconfidence.",
        "• <b>Slide 3 (Research Questions):</b> RQ1 (FPR Reduction), RQ2 (Recall Tradeoff), RQ3 (Confidence Calibration).",
        "• <b>Slide 4 (System Architecture):</b> 7-Layered Defense-in-Depth from Flutter M3 to SQLite Local Persistence.",
        "• <b>Slide 5 (Safety & Guarded Execution):</b> RFC1918 Private Lab IPs, Request Budgeting, and Single-Use Permits.",
        "• <b>Slide 6 (Multi-Agent Reasoning):</b> Primary Specialist vs. Adversarial Reviewer Consensus.",
        "• <b>Slide 7 (Evidence Grounding):</b> Verbatim Substring Matching & SHA-256 Provenance Hashing.",
        "• <b>Slide 8 (Uncertainty Engine):</b> Mathematical Sufficiency Scoring & Fail-Closed Abstention Gates.",
        "• <b>Slide 9 (Testing & Verification):</b> 646 Passing Tests in 23 Seconds; Zero Unverified Code Paths.",
        "• <b>Slide 10 (Honest Governance & Future Work):</b> Exploratory Study Framing (DEC-01) & 8 Supervisor Gates."
    ]
    for d in deck_outline:
        story.append(Paragraph(d, STYLE_BODY))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "৩-মিনিট, ৫-মিনিট এবং ১০-মিনিটের প্রেজেন্টেশন স্ক্রিপ্ট প্রস্তুত রয়েছে।",
            "প্রতিটি স্ক্রিপ্টে সমস্যা, আর্কিটেকচার এবং ফলাফলের ভারসাম্য বজায় রাখা হয়েছে।",
            "স্ক্রিপ্টটি স্পষ্ট ও আত্মবিশ্বাসী কণ্ঠে অনুশীলন করতে হবে।"
        ],
        quiz_q="১০-মিনিটের প্রেজেন্টেশনের প্রথম ২ মিনিটে কী বলা উচিত?",
        quiz_a="রিসার্চ মোটিভেশন, সমস্যা (DAST বনাম LLM) এবং রিসার্চ অবজেক্টিভস।",
        memory_tip="Elevator Pitch = Problem ➔ 3 Innovations ➔ 646 Tests ➔ Impact."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 29
    # ==========================================
    story.append(Paragraph("অধ্যায় ২৯: সাইবার সিকিউরিটি ও এআই গ্লোসারি (Comprehensive Bilingual Glossary)", STYLE_H1))
    story.append(Paragraph(
        "থিসিস ডিফেন্সের জন্য প্রয়োজনীয় গুরুত্বপূর্ণ এআই এবং সাইবার সিকিউরিটি পরিভাষার বাংলা ও ইংরেজি অর্থসহ সংক্ষিপ্ত গ্লোসারি নিচে দেওয়া হলো:",
        STYLE_BODY
    ))

    glossary = [
        [Paragraph("<b>টার্ম (English)</b>", STYLE_BODY_BOLD), Paragraph("<b>বাংলা অর্থ</b>", STYLE_BODY_BOLD), Paragraph("<b>সংক্ষিপ্ত সংজ্ঞা ও প্রাসঙ্গিকতা</b>", STYLE_BODY_BOLD)],
        [Paragraph("Abstention", STYLE_BODY), Paragraph("সিদ্ধান্ত থেকে বিরত থাকা", STYLE_BODY), Paragraph("প্রমাণ অপর্যাপ্ত হলে জোর করে ভুল সিদ্ধান্ত না দিয়ে সিদ্ধান্ত স্থগিত রাখা।", STYLE_BODY)],
        [Paragraph("Canonical Locus", STYLE_BODY), Paragraph("সুনির্দিষ্ট দুর্বলতা স্থানাঙ্ক", STYLE_BODY), Paragraph("টার্গেট ইউআরএল, প্যারামিটার এবং CWE কোডের সুনির্দিষ্ট ত্রিমাত্রিক ঠিকানা।", STYLE_BODY)],
        [Paragraph("CIA Triad", STYLE_BODY), Paragraph("নিরাপত্তার মূল ত্রয়ী", STYLE_BODY), Paragraph("Confidentiality (গোপনীয়তা), Integrity (সততা), Availability (সহজলভ্যতা)।", STYLE_BODY)],
        [Paragraph("DAST", STYLE_BODY), Paragraph("ডায়নামিক অ্যাপ্লিকেশন সিকিউরিটি টেস্টিং", STYLE_BODY), Paragraph("চলমান অ্যাপ্লিকেশনকে বাইরে থেকে ব্ল্যাক-বক্স পদ্ধতিতে স্ক্যান করা।", STYLE_BODY)],
        [Paragraph("Epistemic Uncertainty", STYLE_BODY), Paragraph("জ্ঞানের অভাবজনিত অনিশ্চয়তা", STYLE_BODY), Paragraph("পর্যাপ্ত প্রমাণের ঘাটতি বা বিশেষজ্ঞদের মতবিরোধের কারণে তৈরি হওয়া সন্দেহ।", STYLE_BODY)],
        [Paragraph("Fail-Closed", STYLE_BODY), Paragraph("নিরাপদভাবে বন্ধ হওয়া", STYLE_BODY), Paragraph("সিস্টেমে কোনো ত্রুটি বা সন্দেহ দেখা দিলে স্বয়ংক্রিয়ভাবে অ্যাক্সেস ডিনাই করা।", STYLE_BODY)],
        [Paragraph("Hallucination", STYLE_BODY), Paragraph("অলীক বা মিথ্যা তথ্য তৈরি", STYLE_BODY), Paragraph("এআই মডেল কর্তৃক কোনো প্রমাণ ছাড়া মনগড়া বিশ্বাসযোগ্য মিথ্যা উত্তর দেওয়া।", STYLE_BODY)],
        [Paragraph("IDOR", STYLE_BODY), Paragraph("ইনসিকিউর ডাইরেক্ট অবজেক্ট রেফারেন্স", STYLE_BODY), Paragraph("আইডি পরিবর্তন করে অন্যের সংবেদনশীল ডেটা অ্যাক্সেস করার দুর্বলতা (BAC)।", STYLE_BODY)],
        [Paragraph("Pydantic", STYLE_BODY), Paragraph("পাইথন ডেটা ভ্যালিডেশন লাইব্রেরি", STYLE_BODY), Paragraph("টাইপ হিন্টসের ওপর ভিত্তি করে রানটাইমে কঠোর ডেটা ভ্যালিডেশন নিশ্চিত করে।", STYLE_BODY)],
        [Paragraph("RAG", STYLE_BODY), Paragraph("রিট্রিভাল-অগমেন্টেড জেনারেশন", STYLE_BODY), Paragraph("নলেজ বেস থেকে প্রাসঙ্গিক নথি খুঁজে এনে মডেলের প্রম্পট সমৃদ্ধ করার প্রযুক্তি।", STYLE_BODY)],
        [Paragraph("Wilson Score Interval", STYLE_BODY), Paragraph("উইলসন স্কোর ইন্টারভাল", STYLE_BODY), Paragraph("ছোট স্যাম্পল সাইজে নির্ভুল আত্মবিশ্বাসের সীমা বের করার গাণিতিক পদ্ধতি।", STYLE_BODY)],
    ]
    t_gloss = Table(glossary, colWidths=[130, 140, 234])
    t_gloss.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_gloss)
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "১২টি মৌলিক প্রযুক্তিগত পরিভাষার সঠিক অর্থ সংজ্ঞায়িত করা হয়েছে।",
            "ভাইভায় কোনো ইংরেজি শব্দ শুনলেই তার বাংলা অর্থ এবং কাজের পরিধি বলা সম্ভব হবে।",
            "গ্লোসারি নিয়মিত রিভিশন দিলে কনসেপ্ট নিখুঁত থাকে।"
        ],
        quiz_q="Fail-Closed এবং Fail-Open এর মধ্যে মূল পার্থক্য কী?",
        quiz_a="Fail-Closed এ সন্দেহ হলে ব্লক করে; Fail-Open এ সন্দেহ হলে ডিফল্টভাবে ছেড়ে দেয় (সিকিউরিটিতে অত্যন্ত বিপজ্জনক)।",
        memory_tip="Always remember: In cybersecurity, we ALWAYS fail-closed!"
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 30
    # ==========================================
    story.append(Paragraph("অধ্যায় ৩০: ফাইনাল রিভিশন গাইড ও থিসিস রেডিনেস স্কোরকার্ড (Readiness Scorecard)", STYLE_H1))
    story.append(Paragraph(
        "থিসিস সাবমিশনের পূর্বে সম্পূর্ণ প্রজেক্টের চূড়ান্ত রেটিং এবং পরীক্ষার দিন সকালের ১০-মিনিটের কুইক রিভিশন গাইড নিচে দেওয়া হলো:",
        STYLE_BODY
    ))

    score_table = [
        [Paragraph("<b>মূল্যায়ন ক্যাটাগরি</b>", STYLE_BODY_BOLD), Paragraph("<b>সর্বোচ্চ নম্বর</b>", STYLE_BODY_BOLD), Paragraph("<b>প্রাপ্ত নম্বর</b>", STYLE_BODY_BOLD), Paragraph("<b>বাস্তব প্রমাণ ও যুক্তি</b>", STYLE_BODY_BOLD)],
        [Paragraph("Project Architecture", STYLE_BODY), Paragraph("১৫", STYLE_BODY), Paragraph("<b>১৪</b>", STYLE_BODY), Paragraph("৭-স্তরীয় ডিফেন্স-ইন-ডেপথ ও কঠোর আইসোলেশন বাউন্ডারি।", STYLE_BODY)],
        [Paragraph("Backend Implementation", STYLE_BODY), Paragraph("১৫", STYLE_BODY), Paragraph("<b>১৪</b>", STYLE_BODY), Paragraph("১৪,২৪৩ লাইন টাইপড পাইথন; সমৃদ্ধ এরর হায়ারার্কি।", STYLE_BODY)],
        [Paragraph("Safety & Access Control", STYLE_BODY), Paragraph("১০", STYLE_BODY), Paragraph("<b>১০</b>", STYLE_BODY), Paragraph("লুপব্যাক ব্লক, বাজেট ও সিঙ্গেল-ইউজ পারমিট এনফোর্সমেন্ট।", STYLE_BODY)],
        [Paragraph("Testing & Quality Assurance", STYLE_BODY), Paragraph("১৫", STYLE_BODY), Paragraph("<b>১৫</b>", STYLE_BODY), Paragraph("৬৪৬টি টেস্ট ২২ সেকেন্ডে ১০০% পাস; জিরো টেস্ট ফেইলিউর।", STYLE_BODY)],
        [Paragraph("Frontend UI/UX", STYLE_BODY), Paragraph("১০", STYLE_BODY), Paragraph("<b>৯</b>", STYLE_BODY), Paragraph("ফ্লাটার এম৩ ডার্ক টার্মিনাল; রিভারপড স্টেট ও লাইভ/ডেমো মোড।", STYLE_BODY)],
        [Paragraph("AI Specialist Integration", STYLE_BODY), Paragraph("১০", STYLE_BODY), Paragraph("<b>৮</b>", STYLE_BODY), Paragraph("মাল্টি-এজেন্ট কনসেনসাস বাস্তবায়িত; ক্লাউড এপিআই সেফলি গেটেড।", STYLE_BODY)],
        [Paragraph("Evaluation Mathematics", STYLE_BODY), Paragraph("১০", STYLE_BODY), Paragraph("<b>৯</b>", STYLE_BODY), Paragraph("উইলসন কনফিডেন্স ইন্টারভাল ও নন-জিরো ডিনমিনেটর কন্ট্রাক্ট।", STYLE_BODY)],
        [Paragraph("Empirical Benchmark Scans", STYLE_BODY), Paragraph("১৫", STYLE_BODY), Paragraph("<b>৩</b>", STYLE_BODY), Paragraph("<b>ক্রিটিক্যাল গ্যাপ:</b> ০টি লাইভ স্ক্যান; ৩৬টি কেস আন-অ্যাডজুডিকেটেড।", STYLE_BODY)],
        [Paragraph("<b>সর্বমোট থিসিস রেডিনেস স্কোর</b>", STYLE_BODY_BOLD), Paragraph("<b>১০০</b>", STYLE_BODY_BOLD), Paragraph("<b>৮২ / ১০০</b>", STYLE_BODY_BOLD), Paragraph("<b>গ্রেড: A- (শক্তিশালী ইঞ্জিনিয়ারিং প্রোটোটাইপ)</b>", STYLE_BODY_BOLD)],
    ]
    t_score = Table(score_table, colWidths=[120, 50, 60, 274])
    t_score.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_score)
    story.append(Spacer(1, 10))

    story.append(make_callout(
        "<b>পরীক্ষার দিন সকালের ৫টি গোল্ডেন রুলস (Golden Rules for Viva Day):</b><br/>"
        "১. <b>সততাই শ্রেষ্ঠ ডিফেন্স:</b> লাইভ স্ক্যান হয়নি—এটি অকপটে স্বীকার করুন এবং DEC-08 গেট ও সেফটি ফার্স্ট নীতির কথা বলুন।<br/>"
        "২. <b>৬৪৬টি টেস্ট আপনার ঢাল:</b> কোড যে কাজ করে এবং স্টেট মেশিন যে ১০০% পরীক্ষিত, তার প্রমাণ আপনার ৬৪৬টি টেস্ট।<br/>"
        "৩. <b>DAST বনাম LLM এর পার্থক্য স্পষ্ট রাখুন:</b> DAST কনটেক্সট বোঝে না, LLM হ্যালুসিনেট করে; AegisCore এভিডেন্স গ্রাউন্ড করে।<br/>"
        "৪. <b>কখনো মেজাজ হারাবেন না:</b> এক্সামিনার কঠিন প্রশ্ন করলে বা কোনো ত্রুটি ধরলে শান্তভাবে ধন্যবাদ দিয়ে নোট করুন।<br/>"
        "৫. <b>গবেষণার পরিধি মনে রাখুন:</b> ৩৬টি কেস মানে এটি এক্সপ্লোরেটরি স্টাডি (DEC-01), কোনো সর্বজনীন সমাধান নয়।",
        title="EXAMINATION MORNING REVISION SHIELD"
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "আপনার সামগ্রিক থিসিস রেডিনেস স্কোর ৮২/১০০ (গ্রেড A-)।",
            "সবচেয়ে শক্তিশালী ক্ষেত্র: আর্কিটেকচার, সেফটি কন্ট্রোল এবং ৬৪৬টি অটোমেটেড টেস্ট।",
            "সবচেয়ে দুর্বল ক্ষেত্র: লাইভ বেঞ্চমার্ক স্ক্যান এখনও এক্সিকিউট করা হয়নি।",
            "সততার সাথে ডিফেন্স করলে আপনি সফলভাবে থিসিস ডিফেন্ড করতে পারবেন।"
        ],
        quiz_q="কেন কৃত্রিমভাবে ৯৫+ নম্বর দেওয়া হয়নি?",
        quiz_a="কারণ লাইভ বেঞ্চমার্ক স্ক্যান না চালিয়ে কোনো প্রজেক্টকে এ+ দেওয়া একাডেমিক সততার পরিপন্থী।",
        memory_tip="Score 82 = Real, verified, honest science with passing unit contracts."
    ))
    story.append(PageBreak())

    return story
