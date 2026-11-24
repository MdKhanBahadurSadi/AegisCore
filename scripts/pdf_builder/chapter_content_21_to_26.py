"""Chapters 21 to 26 for AEGISCORE AI Master Thesis Study Book.
"""

from __future__ import annotations

from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from .styles import (
    STYLE_H1, STYLE_H2, STYLE_H3, STYLE_BODY, STYLE_BODY_BOLD, STYLE_CODE,
    make_callout, make_feynman_box, make_checkpoint_box,
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_BG_LIGHT
)


def get_chapters_21_to_26():
    story = []

    # ==========================================
    # CHAPTER 21
    # ==========================================
    story.append(Paragraph("অধ্যায় ২১: Research Methodology & Hypotheses (RQ1, RQ2, RQ3)", STYLE_H1))
    story.append(Paragraph(
        "একটি অ্যাকাডেমিক থিসিসের মেরুদণ্ড হলো এর <b>রিসার্চ মেথডোলজি (Research Methodology)</b>। "
        "আমাদের গবেষণার ফ্রেমওয়ার্কটি একটি <b>এক্সপ্লোরেটরি ফিজিবিলিটি স্টাডি (Exploratory Feasibility Study)</b> হিসেবে ডিজাইন করা হয়েছে।",
        STYLE_BODY
    ))

    story.append(Paragraph("<b>গবেষণার তিনটি হাইপোথিসিস (Hypotheses):</b><br/>"
        "• <b>Hypothesis 1 (H1 — FPR Reduction):</b> প্রমাণ-ভিত্তিক সাইটেশন ভ্যালিডেশন এবং অ্যাডভারসারিয়াল রিভিউয়ার যুক্ত করার ফলে ফলস পজিটিভ রেট বেইজলাইন মাল্টি-এজেন্ট সিস্টেমের তুলনায় অন্তত ৫০% হ্রাস পাবে ($FPR_{\\text{Aegis}} < 0.50 \\times FPR_{\\text{Baseline}}$)।<br/>"
        "• <b>Hypothesis 2 (H2 — Selective Risk vs Coverage):</b> অনিশ্চয়তা ইঞ্জিন যখন অস্পষ্ট ক্ষেত্রে বিরত থাকে (Abstention), তখন কভারেজ কিছুটা কমলেও ($Coverage \\ge 75\\%$), ডিসাইডেড স্যাম্পলের নির্ভুলতা বা সিলেক্টিভ রিস্ক উল্লেখযোগ্যভাবে উন্নত হয়।<br/>"
        "• <b>Hypothesis 3 (H3 — Calibration):</b> মডেলের স্ব-ঘোষিত কনফিডেন্স স্কোরের চেয়ে গাণিতিক এভিডেন্স সাফিশিয়েন্সি স্কোর বাস্তব নির্ভুলতার সাথে অধিক সংগতিপূর্ণ (Lower Brier Score / ECE)।",
        STYLE_BODY
    ))

    story.append(make_checkpoint_box(
        what_learned=[
            "গবেষণাটি ৩টি সুনির্দিষ্ট হাইপোথিসিসের ওপর প্রতিষ্ঠিত।",
            "নমুনা সাইজ ৩৬টি হওয়ায় এটিকে এক্সপ্লোরেটরি স্টাডি হিসেবে ফ্রেম করা হয়েছে।",
            "পরিসংখ্যানগত তুলনার জন্য ম্যাকনেমার টেস্ট (McNemar's test) ব্যবহৃত হবে।"
        ],
        quiz_q="কেন গবেষণাটিকে এক্সপ্লোরেটরি স্টাডি হিসেবে ফ্রেম করা হয়েছে?",
        quiz_a="কারণ ৩৬টি কেস সামগ্রিক পপুলেশন দাবি করার জন্য ছোট; সততার সাথে এক্সপ্লোরেটরি বলাই বৈজ্ঞানিক রীতি।",
        memory_tip="Methodology = Formulate Hypotheses ➔ Pre-register Metrics ➔ Test Honestly."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 22
    # ==========================================
    story.append(Paragraph("অধ্যায় ২২: Experimentation, Benchmarking & Evaluation Protocol", STYLE_H1))
    story.append(Paragraph(
        "আমাদের ইভ্যালুয়েশন প্রোটোকলে দুটি স্ট্যান্ডার্ড গ্রাউন্ড-ট্রুথ টার্গেট রাখা হয়েছে: <b>OWASP Juice Shop v15.0.0</b> (Node.js/Angular) এবং <b>DVWA 1.10</b> (PHP/MySQL)। "
        "মোট ৩৬টি কেস স্লট প্রস্তাব করা হয়েছে (২৪টি জুস শপ, ১২টি ডিভিডব্লিউএ)।",
        STYLE_BODY
    ))

    # Confusion matrix breakdown table
    cm_data = [
        [Paragraph("<b>আউটকাম শ্রেণি</b>", STYLE_BODY_BOLD), Paragraph("<b>বাস্তব অবস্থা (Ground Truth)</b>", STYLE_BODY_BOLD), Paragraph("<b>AegisCore সিদ্ধান্ত</b>", STYLE_BODY_BOLD), Paragraph("<b>স্কোরিং প্রভাব</b>", STYLE_BODY_BOLD)],
        [Paragraph("True Positive (TP)", STYLE_BODY), Paragraph("ভালনারেবল (Vulnerable)", STYLE_BODY), Paragraph("রিপোর্ট করেছে (VERIFIED)", STYLE_BODY), Paragraph("সফল ডিটেকশন; রিকল বৃদ্ধি পায়।", STYLE_BODY)],
        [Paragraph("False Positive (FP)", STYLE_BODY), Paragraph("নিরাপদ (Non-Vulnerable)", STYLE_BODY), Paragraph("ভুল করে রিপোর্ট করেছে", STYLE_BODY), Paragraph("ভুল অ্যালার্ম; স্পেসিফিসিটি কমে যায়।", STYLE_BODY)],
        [Paragraph("True Negative (TN)", STYLE_BODY), Paragraph("নিরাপদ (Non-Vulnerable)", STYLE_BODY), Paragraph("রিজেক্ট করেছে (NON_VULN)", STYLE_BODY), Paragraph("সফল প্রতিরোধ; স্পেসিফিসিটি বৃদ্ধি পায়।", STYLE_BODY)],
        [Paragraph("False Negative (FN)", STYLE_BODY), Paragraph("ভালনারেবল (Vulnerable)", STYLE_BODY), Paragraph("মিস করেছে বা বিরত থেকেছে (ABSTAIN)", STYLE_BODY), Paragraph("ফেইল-ক্লোজড নীতি অনুযায়ী অ্যাবস্টেইনকে FN ধরা হয়।", STYLE_BODY)],
    ]
    t_cm = Table(cm_data, colWidths=[120, 120, 134, 130])
    t_cm.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_cm)
    story.append(Spacer(1, 10))

    story.append(make_callout(
        "<b>কঠোর বৈজ্ঞানিক ইনভেরিয়েন্ট:</b><br/>"
        "ভালনারেবল এন্ডপয়েন্টে সিস্টেম যদি এভিডেন্সের অভাবে বিরত থাকে (ABSTAIN), তবে সিস্টেমে ফাঁকি না দিয়ে সেটিকে কঠোরভাবে False Negative (FN) হিসেবে গণ্য করা হয়। "
        "একইভাবে, নিরাপদ কন্ট্রোলে বিরত থাকলে তাকে কখনোই True Negative (TN) বলে ক্রেডিট দেওয়া হয় না।",
        title="FAIL-CLOSED SCORING INVARIANT"
    ))
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "টার্গেট বেঞ্চমার্ক হিসেবে জুস শপ এবং ডিভিডব্লিউএ নির্বাচিত।",
            "অ্যাবস্টেনশনকে সুবিধাজনকভাবে সত্য বলে দাবি না করে FN হিসেবে ধরা হয়।",
            "উইলসন স্কোর ইন্টারভাল দিয়ে ছোট নমুনার ত্রুটি দূর করা হয়েছে।"
        ],
        quiz_q="কেন অ্যাবস্টেনশনকে ভালনারেবল কেসে FN ধরা হয়?",
        quiz_a="কারণ সিস্টেম দুর্বলতাটি সনাক্ত করতে ব্যর্থ হয়েছে; সিকিউরিটিতে মিসিং ভালনারেবিলিটি সবসময় নেগেটিভ আউটকাম।",
        memory_tip="TP = Caught Flaw, FP = False Alarm, TN = Caught Benign, FN = Missed Flaw."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 23
    # ==========================================
    story.append(Paragraph("অধ্যায় ২৩: Thesis Writing & Chapter-by-Chapter Guide", STYLE_H1))
    story.append(Paragraph(
        "থিসিস পেপার লেখার সময় প্রতিটি চ্যাপ্টারে কী থাকা উচিত এবং কী ভুল এড়ানো উচিত, তার একটি কমপ্লিট নির্দেশিকা নিচে দেওয়া হলো:",
        STYLE_BODY
    ))

    ch_guide = [
        [Paragraph("<b>চ্যাপ্টার</b>", STYLE_BODY_BOLD), Paragraph("<b>মূল বিষয়বস্তু (What to Write)</b>", STYLE_BODY_BOLD), Paragraph("<b>যে ভুলটি কখনোই করবেন না (Mistakes to Avoid)</b>", STYLE_BODY_BOLD)],
        [Paragraph("Chapter 1: Intro", STYLE_BODY), Paragraph("পটভূমি, সমস্যা, রিসার্চ মোটিভেশন এবং অবজেক্টিভস।", STYLE_BODY), Paragraph("খুব সাধারণ গল্প দিয়ে শুরু করা বা উদ্দেশ্য অস্পষ্ট রাখা।", STYLE_BODY)],
        [Paragraph("Chapter 2: Lit Review", STYLE_BODY), Paragraph("DAST স্ক্যানার, এলএলএম সিকিউরিটি, RAG এবং মাল্টি-এজেন্ট গবেষণার তুলনামূলক পর্যালোচনা।", STYLE_BODY), Paragraph("শুধু পেপারের সারসংক্ষেপ লেখা; রিসার্চ গ্যাপ চিহ্নিত না করা।", STYLE_BODY)],
        [Paragraph("Chapter 3: Methodology", STYLE_BODY), Paragraph("সিস্টেম ডিজাইন, পলিসি ইঞ্জিন, মাল্টি-এজেন্ট স্টেট মেশিন এবং আনসার্টেইনটি মডেল।", STYLE_BODY), Paragraph("কোড লজিক বাদ দিয়ে শুধু তাত্ত্বিক কথা লেখা।", STYLE_BODY)],
        [Paragraph("Chapter 4: Implementation", STYLE_BODY), Paragraph("FastAPI, Flutter, SQLite, Pydantic এবং ৬৪৬টি টেস্টের আর্কিটেকচার।", STYLE_BODY), Paragraph("লাইব্রেরির বিবরণ দেওয়া কিন্তু নিজের লেখা কোডের কথা না বলা।", STYLE_BODY)],
        [Paragraph("Chapter 5: Evaluation", STYLE_BODY), Paragraph("উইলসন কনফিডেন্স ইন্টারভাল, কনফিউশন ম্যাট্রিক্স, বেঞ্চমার্ক কেস ও রেজাল্ট।", STYLE_BODY), Paragraph("কাল্পনিক বা ভুয়া রেজাল্ট তৈরি করা (Fabrication)।", STYLE_BODY)],
        [Paragraph("Chapter 6: Conclusion", STYLE_BODY), Paragraph("প্রধান ফলাফল, গবেষণার সীমাবদ্ধতা এবং ভবিষ্যতের কাজ।", STYLE_BODY), Paragraph("সীমাবদ্ধতা গোপন করা বা দাবি অতিরঞ্জিত করা।", STYLE_BODY)],
    ]
    t_guide = Table(ch_guide, colWidths=[100, 210, 194])
    t_guide.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_guide)
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "থিসিসের ৬টি মূল চ্যাপ্টারের সুস্পষ্ট ভূমিকা রয়েছে।",
            "লিটারেচার রিভিউতে রিসার্চ গ্যাপ স্পষ্টভাবে তুলে ধরতে হবে।",
            "ইভ্যালুয়েশন চ্যাপ্টারে কোনো ভুয়া রেজাল্ট যুক্ত করা যাবে না।"
        ],
        quiz_q="লিটারেচার রিভিউয়ের মূল উদ্দেশ্য কী?",
        quiz_a="পূর্ববর্তী গবেষণার সীমাবদ্ধতা চিহ্নিত করে নিজের কাজের যৌক্তিকতা (Research Gap) প্রতিষ্ঠা করা।",
        memory_tip="Thesis Flow = Context ➔ Gap ➔ Method ➔ Code ➔ Proof ➔ Honesty."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 24
    # ==========================================
    story.append(Paragraph("অধ্যায় ২৪: Research Limitations & Supervisor Decision Register", STYLE_H1))
    story.append(Paragraph(
        "গবেষণার সীমাবদ্ধতা সততার সাথে স্বীকার করা একজন গবেষকের সবচেয়ে বড় শক্তি। "
        "AegisCore AI-এর `docs/SUPERVISOR_DECISION_REGISTER.md` ফাইলে ৮টি আনুষ্ঠানিক সিদ্ধান্ত গেট (Decision Gates) নথিভুক্ত করা আছে, যা বর্তমানে **PENDING** অবস্থায় রয়েছে:",
        STYLE_BODY
    ))

    gates_data = [
        [Paragraph("<b>গেট আইডি</b>", STYLE_BODY_BOLD), Paragraph("<b>সিদ্ধান্তের বিষয়বস্তু</b>", STYLE_BODY_BOLD), Paragraph("<b>বর্তমান স্ট্যাটাস ও প্রভাব</b>", STYLE_BODY_BOLD)],
        [Paragraph("DEC-01", STYLE_BODY), Paragraph("Exploratory Statistical Framing", STYLE_BODY), Paragraph("PENDING — ৩৬টি কেসকে এক্সপ্লোরেটরি স্টাডি হিসেবে ফ্রেম করা।", STYLE_BODY)],
        [Paragraph("DEC-02", STYLE_BODY), Paragraph("Proposed Evaluation Scope (N=36)", STYLE_BODY), Paragraph("PENDING — ২০টি অপূর্ণ স্লট প্রুন করা বা অনুমোদন দেওয়া।", STYLE_BODY)],
        [Paragraph("DEC-03", STYLE_BODY), Paragraph("Ground-Truth Adjudication Procedure", STYLE_BODY), Paragraph("PENDING — গ্রাউন্ড ট্রুথ অনুমোদনের ৩-ধাপের ভেরিফিকেশন।", STYLE_BODY)],
        [Paragraph("DEC-04", STYLE_BODY), Paragraph("Negative-Control Resolution", STYLE_BODY), Paragraph("PENDING — জুস শপের ত্রুটিপূর্ণ কন্ট্রোল বাদ দেওয়া।", STYLE_BODY)],
        [Paragraph("DEC-05", STYLE_BODY), Paragraph("Validation / Test Partition Policy", STYLE_BODY), Paragraph("PENDING — ৪০% ভ্যালিডেশন / ৬০% টেস্ট পার্টিশন অনুমোদন।", STYLE_BODY)],
        [Paragraph("DEC-06", STYLE_BODY), Paragraph("Benchmark Version & Digest Policy", STYLE_BODY), Paragraph("PENDING — ডিভিডব্লিউএ ও জুস শপ ডকার ইমেজ হ্যাশ পিন করা।", STYLE_BODY)],
        [Paragraph("DEC-07", STYLE_BODY), Paragraph("Model-Provider Architecture Selection", STYLE_BODY), Paragraph("PENDING — ক্লাউড জেমিনি এপিআই বনাম লোকাল ওলামা/ভিএলএলএম।", STYLE_BODY)],
        [Paragraph("DEC-08", STYLE_BODY), Paragraph("Authorization for Container Startup", STYLE_BODY), Paragraph("PENDING (HOLD) — লাইভ কনটেইনার স্ক্যান চালু করার অনুমোদন।", STYLE_BODY)],
    ]
    t_gates = Table(gates_data, colWidths=[70, 180, 254])
    t_gates.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_gates)
    story.append(Spacer(1, 10))

    story.append(make_checkpoint_box(
        what_learned=[
            "৮টি ডিসিশন গেট পুরো গবেষণার গভর্নেন্স সীমানা নির্ধারণ করে।",
            "সুপারভাইজারের স্বাক্ষর ছাড়া লাইভ কনটেইনার চালানো নিষিদ্ধ রাখা হয়েছে (DEC-08)।",
            "এটি প্রমাণ করে শিক্ষার্থী দায়িত্বশীল ও সেফটি-সচেতন গবেষক।"
        ],
        quiz_q="DEC-08 গেটটি কেন PENDING রাখা হয়েছে?",
        quiz_a="গ্রাউন্ড ট্রুথ এবং লিগ্যাল বাউন্ডারি সুপারভাইজার কর্তৃক অনুমোদিত হওয়ার আগে যাতে কোনো লাইভ স্ক্যান না চালানো হয়।",
        memory_tip="8 Decision Gates = Supervisor sign-off checkpoints for ethical science."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 25
    # ==========================================
    story.append(Paragraph("অধ্যায় ২৫: Future Improvements Roadmap (P0, P1, P2)", STYLE_H1))
    story.append(Paragraph(
        "থিসিস ডিফেন্সের পর এবং পেপার পাবলিকেশনের আগে সিস্টেমটিকে আরও সমৃদ্ধ করার জন্য অগ্রাধিকারভিত্তিক রোডম্যাপ নির্ধারণ করা হলো:",
        STYLE_BODY
    ))
    story.append(Paragraph("<b>P0 — জরুরি অগ্রাধিকার (Must Fix Before Final Submission):</b><br/>"
        "১. সুপারভাইজারের সাথে বসে DEC-01 এবং DEC-03 গেট স্বাক্ষর করিয়ে নেওয়া।<br/>"
        "২. ক্যাটালগের ২০টি খালি স্লট প্রুন করে ১৬টি প্রি-রেজিস্টার্ড কেসে সীমাবদ্ধ করা।<br/>"
        "৩. থিসিস পেপারে স্পষ্টভাবে ঘোষণা করা যে এটি একটি অফলাইন-ভেরিফাইড আর্কিটেকচারাল প্রোটোটাইপ।",
        STYLE_BODY
    ))
    story.append(Paragraph("<b>P1 — গুরুত্বপূর্ণ উন্নতি (Important Improvements):</b><br/>"
        "১. DEC-08 অনুমোদিত হলে লোকাল ডকার কনটেইনারে ১৬টি কেসের লাইভ টেস্ট রান সম্পন্ন করা।<br/>"
        "২. জেডএপি (OWASP ZAP) স্ক্যানার চালিয়ে সরাসরি তুলনামূলক কনফিউশন ম্যাট্রিক্স তৈরি করা।<br/>"
        "৩. সোর্স রিভিউ ম্যানিফেস্টে হিউম্যান সাইন-অফ সম্পন্ন করে রিট্রিভাল সক্রিয় করা।",
        STYLE_BODY
    ))
    story.append(Paragraph("<b>P2 — ঐচ্ছিক বর্ধিতকরণ (Optional Enhancements):</b><br/>"
        "১. ক্লাউড ডিপেন্ডেন্সি পুরোপুরি মুছে লোকাল ওলামা (Ollama Llama-3.1-70B) রানটাইম যুক্ত করা।<br/>"
        "২. ফ্লাটার ইউআই থেকে সরাসরি ওয়ান-ক্লিক পিডিএফ এক্সপোর্ট ফিচার চালু করা।",
        STYLE_BODY
    ))

    story.append(make_checkpoint_box(
        what_learned=[
            "উন্নতিগুলোকে P0, P1 এবং P2 ক্যাটাগরিতে ভাগ করা হয়েছে।",
            "P0 কাজগুলো থিসিস সাবমিশনের পূর্বশর্ত।",
            "ভবিষ্যতের কাজ স্পষ্টভাবে জানা থাকলে এক্সামিনাররা সন্তুষ্ট হন।"
        ],
        quiz_q="P0 রোডম্যাপের প্রধান লক্ষ্য কী?",
        quiz_a="মেথডোলজিক্যাল সততা নিশ্চিত করা এবং সুপারভাইজার ডিসিশন গেট ক্লোজ করা।",
        memory_tip="P0 = Urgent Defense Shield; P1 = Live Run; P2 = Future Features."
    ))
    story.append(PageBreak())

    # ==========================================
    # CHAPTER 26
    # ==========================================
    story.append(Paragraph("অধ্যায় ২৬: Thesis Defense Preparation Strategy (Facing Examiners)", STYLE_H1))
    story.append(Paragraph(
        "থিসিস ডিফেন্স বা ভাইভায় ভালো করার জন্য শুধু কোড জানলেই চলে না; এক্সামিনারের মনস্তত্ত্ব বোঝা এবং সঠিক বডি ল্যাঙ্গুয়েজ বজায় রাখা জরুরি। "
        "নিচে পাঁচটি পরীক্ষিত কৌশল দেওয়া হলো:",
        STYLE_BODY
    ))
    story.append(Paragraph("<b>১. কখনো কোনো ফলাফল বানিয়ে বলবেন না (Never Fabricate):</b> কোনো প্রশ্নের উত্তর জানা না থাকলে বা কোনো ফিচার বাস্তবায়ন না থাকলে সরাসরি বলুন—'স্যার, এই ফিচারটি আমাদের প্রজেক্ট স্কোপের বাইরে রাখা হয়েছিল এবং ডিসিশন রেজিস্টারে এটি ফিউচার ওয়ার্ক হিসেবে নথিভুক্ত আছে।' এটি সততার প্রমাণ দেয়।", STYLE_BODY))
    story.append(Paragraph("<b>২. আত্মরক্ষামূলক না হয়ে কৃতজ্ঞতা প্রকাশ করুন:</b> এক্সামিনার কোনো ভুল ধরলে বলবেন—'Thank you sir, that is a great observation. We noted this in our limitation section and will incorporate it in our next revision.'", STYLE_BODY))
    story.append(Paragraph("<b>৩. স্থাপত্য ও সিদ্ধান্তের কারণ ব্যাখ্যা করুন (Explain the Why):</b> শুধু কী করেছেন তা বলবেন না; কেন এই প্রযুক্তি বেছে নিয়েছেন এবং কেন বিকল্প প্রযুক্তি বাদ দিয়েছেন তা বলুন।", STYLE_BODY))
    story.append(Paragraph("<b>৪. কন্ট্রোল নিজের হাতে রাখুন:</b> কোনো জটিল প্রশ্নের উত্তর দেওয়ার সময় আপনার আর্কিটেকচার ডায়াগ্রাম বা ৬৪৬টি টেস্টের রেফারেন্স টানুন।", STYLE_BODY))

    story.append(make_checkpoint_box(
        what_learned=[
            "ডিফেন্সে সততা ও আত্মবিশ্বাস সবচেয়ে বড় শক্তি।",
            "অজানা প্রশ্নে বানিয়ে না বলে সীমাবদ্ধতা হিসেবে স্বীকার করা ভালো।",
            "প্রতিটি প্রযুক্তিগত সিদ্ধান্তের পেছনে জোরালো যুক্তি থাকতে হবে।"
        ],
        quiz_q="এক্সামিনার যখন সিস্টেমে কোনো সীমাবদ্ধতা খুঁজে পান তখন কী বলা উচিত?",
        quiz_a="সততার সাথে স্বীকার করা, পর্যবেক্ষণের জন্য ধন্যবাদ দেওয়া এবং এটি কীভাবে ফিউচার ওয়ার্কে রাখা হয়েছে তা বলা।",
        memory_tip="Be humble, be honest, anchor answers to architecture and tests."
    ))
    story.append(PageBreak())

    return story
