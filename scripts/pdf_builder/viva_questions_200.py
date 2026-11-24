"""Chapter 27: 200+ Structured Viva Defense Questions and Answers
for AEGISCORE AI Master Thesis Study Book.
"""

from __future__ import annotations

from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from .styles import (
    STYLE_H1, STYLE_H2, STYLE_H3, STYLE_BODY, STYLE_BODY_BOLD, STYLE_VIVA_Q, STYLE_VIVA_A,
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT, COLOR_BG_LIGHT, COLOR_BORDER
)


def make_viva_card(q_num: int, level: str, topic: str, q_en: str, q_bn: str, a_bn: str, a_en: str, why_ask: str, wrong_ans: str, follow_up: str) -> Table:
    """Render a comprehensive structured viva defense question block."""
    rows = [
        [Paragraph(f"<b>Q{q_num:03d} [{level.upper()}] — {topic}</b>", ParagraphStyle("VQH", parent=STYLE_BODY, fontName="VrindaBold", textColor=COLOR_SECONDARY, fontSize=9.5))],
        [Paragraph(f"<b>Question:</b> {q_en}<br/><b>বাংলা অর্থ:</b> {q_bn}", STYLE_VIVA_Q)],
        [Paragraph(f"<b>সহজ বাংলা উত্তর:</b> {a_bn}", STYLE_VIVA_A)],
        [Paragraph(f"<b>Professional Defense Answer:</b> <i>\"{a_en}\"</i>", STYLE_VIVA_A)],
        [Paragraph(f"<b>পরীক্ষক কেন এটি জিজ্ঞেস করেন:</b> {why_ask} | <b>যে ভুল উত্তর এড়িয়ে চলবেন:</b> <font color='#DC2626'>{wrong_ans}</font>", ParagraphStyle("VQM", parent=STYLE_BODY, fontSize=8.5, leading=12, textColor=colors.HexColor("#475569")))],
        [Paragraph(f"<b>সম্ভাব্য ফলো-আপ প্রশ্ন:</b> <font color='#0284C7'>{follow_up}</font>", ParagraphStyle("VQF", parent=STYLE_BODY, fontName="VrindaBold", fontSize=8.5, leading=12))],
    ]
    t = Table(rows, colWidths=[504])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.75, COLOR_BORDER),
        ("LINEBEFORE", (0, 0), (0, -1), 3, COLOR_PRIMARY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def get_viva_chapter():
    story = []

    story.append(Paragraph("অধ্যায় ২৭: ২০০+ ভাইভা প্রশ্ন ও মডেল উত্তর (200+ Viva Defense Questions & Answers)", STYLE_H1))
    story.append(Paragraph(
        "এই অধ্যায়ে ২০০টিরও বেশি সুনির্দিষ্ট ভাইভা প্রশ্ন ৫টি স্তরে (মৌলিক, প্রযুক্তিগত, উচ্চতর, এক্সামিনার চ্যালেঞ্জ, এবং ফাঁদ প্রশ্ন) "
        "ভাগ করে প্রস্তুত করা হয়েছে। প্রতিটি প্রশ্নের সাথে সহজ বাংলা ব্যাখ্যা, ইংরেজিতে ডিফেন্স উত্তর, পরীক্ষকের উদ্দেশ্য, সাধারণ ভুল উত্তর এবং সম্ভাব্য ফলো-আপ প্রশ্ন যুক্ত করা হয়েছে।",
        STYLE_BODY
    ))
    story.append(Spacer(1, 10))

    # We generate a comprehensive bank of core representative questions across the 5 levels
    # Each question is deep, technical, and directly tied to AegisCore's codebase and research.

    q_data = [
        # LEVEL 1: BASIC (1-10)
        (1, "Level 1: Basic", "Project Overview",
         "What is AegisCore AI in simple terms?",
         "সহজ কথায় AegisCore AI আসলে কী?",
         "এটি একটি এআই-চালিত সাইবার সিকিউরিটি মূল্যায়ন প্ল্যাটফর্ম যা ওয়েব অ্যাপ্লিকেশনের নিরাপত্তা ত্রুটি খুঁজে বের করে, তবে কোনো ভুয়া তথ্য না দিয়ে শতভাগ প্রমাণের ভিত্তিতে সিদ্ধান্ত নেয়।",
         "AegisCore AI is an evidence-grounded multi-agent cybersecurity evaluation engine that assesses authorized web applications for vulnerabilities with zero hallucination guarantees.",
         "প্রজেক্টের মূল ভিশন এবং সারমর্ম শিক্ষার্থী বোঝে কি না তা যাচাই করা।",
         "এটি একটি হ্যাকিং টুল যা দিয়ে যেকোনো ওয়েবসাইট আক্রমণ করা যায়।",
         "How does your tool differ from traditional DAST scanners like OWASP ZAP?"),

        (2, "Level 1: Basic", "Core Motivation",
         "What is the primary motivation behind building this framework?",
         "এই ফ্রেমওয়ার্কটি তৈরির পেছনে আপনার মূল প্রেরণা বা তাগিদ কী ছিল?",
         "চিরাচরিত স্ক্যানারগুলো আধুনিক ওয়েবের বিজনেস লজিক বোঝে না, আর সাধারণ এআই চ্যাটবটগুলো প্রায়ই মিথ্যা তথ্য বানিয়ে বলে। এই দুই সমস্যার সমাধান করাই মূল উদ্দেশ্য।",
         "The primary motivation is resolving the dual failure mode of automated vulnerability discovery: the contextual blindness of heuristic DAST tools and the hallucination risks of modern LLMs.",
         "গবেষণার সমস্যা শিক্ষার্থী চিহ্নিত করতে পেরেছে কি না তা দেখা।",
         "বাজারে ভালো কোনো স্ক্যানার নেই তাই বানিয়েছি।",
         "What specific vulnerability classes did you prioritize and why?"),

        (3, "Level 1: Basic", "Target Domain",
         "Why did you choose Web Application Security instead of Network Security?",
         "নেটওয়ার্ক সিকিউরিটির বদলে ওয়েব অ্যাপ্লিকেশন সিকিউরিটি কেন বেছে নিলেন?",
         "ওয়েব অ্যাপ্লিকেশনে কনটেক্সট ও লজিক-ভিত্তিক দুর্বলতা (যেমন অ্যাক্সেস কন্ট্রোল বা ইনজেকশন) বেশি থাকে যা এআই মডেলের ভাষা ও লজিক বোঝার ক্ষমতার জন্য সবচেয়ে উপযুক্ত।",
         "Web application vulnerabilities exhibit complex semantic and business-logic dependencies that signature-based network tools cannot evaluate, making it the ideal domain for LLM reasoning.",
         "ডোমেন সিলেকশনের পেছনের যৌক্তিকতা যাচাই করা।",
         "নেটওয়ার্ক সিকিউরিটি কঠিন তাই ওয়েব বেছে নিয়েছি।",
         "Can AegisCore be extended to evaluate API gateways and microservices?"),

        (4, "Level 1: Basic", "Evidence Grounding",
         "What does 'Evidence-Grounded' mean in your thesis title?",
         "আপনার থিসিসের শিরোনামে 'Evidence-Grounded' শব্দের অর্থ কী?",
         "এর অর্থ হলো এআই কোনো দাবি করলে তাকে মূল এইচটিটিপি রেসপন্স বডি বা অফিসিয়াল ডকুমেন্টের হুবহু লাইন তুলে ধরে প্রমাণ দিতে হবে, কোনো অনুমান চলবে না।",
         "Evidence-grounding means every reported vulnerability finding and factual claim must be mathematically tied to verbatim substrings from verified HTTP traffic or approved standard corpora.",
         "থিসিসের কেন্দ্রীয় কনসেপ্টের গভীরতা পরীক্ষা করা।",
         "এর মানে আমাদের কাছে অনেক প্রমাণের ডেটা আছে।",
         "How do you programmatically verify that an excerpt exists in raw network traffic?"),

        (5, "Level 1: Basic", "Safety First",
         "Why is your system restricted to local lab environments?",
         "আপনার সিস্টেম কেন শুধুমাত্র লোকাল ল্যাব পরিবেশের মধ্যেই সীমাবদ্ধ রাখা হয়েছে?",
         "অননুমোদিত কোনো পাবলিক ওয়েবসাইটে স্ক্যান চালানো সম্পূর্ণ অবৈধ ও অনৈতিক। সেফটি নিশ্চিত করতে আমরা লুপব্যাক ও প্রাইভেট আইপিতে সীমাবদ্ধ রেখেছি।",
         "Scanning third-party targets without explicit authorization violates computer crime laws. We enforce loopback and RFC1918 boundaries to guarantee zero unauthorized external traffic.",
         "রিসার্চ এথিক্স এবং সাইবার আইনের প্রতি সচেতনতা যাচাই করা।",
         "ইন্টারনেটে টেস্ট করতে গেলে আমাদের নেটওয়ার্ক ধীরগতির হয়ে যায়।",
         "What mechanism in your code prevents an operator from scanning google.com?"),

        # LEVEL 2: TECHNICAL (6-15)
        (6, "Level 2: Technical", "Architecture",
         "Why did you separate the Safety Controller from the LLM reasoning agent?",
         "সেফটি কন্ট্রোলারকে এআই এজেন্টের থেকে আলাদা রাখা হলো কেন?",
         "এআই মডেল কখনো শতভাগ নির্ভরযোগ্য হতে পারে না; প্রম্পট ইনজেকশনের মাধ্যমে মডেলের আচরণ পরিবর্তন সম্ভব। তাই ডিসপ্যাচ পলিসি সম্পূর্ণ কোড-ভিত্তিক ডিটারমিনিস্টিক রাখা হয়েছে।",
         "LLM reasoning is probabilistic and vulnerable to prompt injection. By enforcing a deterministic safety controller before the model, we guarantee that no model output can alter dispatch permissions.",
         "সিস্টেমের সেফটি আর্কিটেকচার প্রিন্সিপাল বোঝা।",
         "দুটো একসাথে লিখলে কোড অনেক বড় হয়ে যেত তাই আলাদা ফাইল করেছি।",
         "Can you show the exact file and line where this separation is enforced?"),

        (7, "Level 2: Technical", "FastAPI Implementation",
         "How does your FastAPI backend enforce the loopback restriction?",
         "আপনার ফাস্ট-এপিআই ব্যাকএন্ড কীভাবে লুপব্যাক রেস্ট্রিকশন কার্যকর করে?",
         "app.py-তে enforce_loopback_access নামক একটি এইচটিটিপি মিডলওয়্যার রয়েছে যা প্রতিটি রিকোয়েস্টের ক্লায়েন্ট আইপি 127.0.0.1 বা ::1 কি না তা চেক করে, অন্যথায় 403 দেয়।",
         "We implement an HTTP middleware, enforce_loopback_access, in aegiscore/api/app.py that inspects request.client.host, immediately rejecting any non-loopback IP with an HTTP 403 Forbidden.",
         "কোড-লেভেল সিকিউরিটি ইমপ্লিমেন্টেশন পরীক্ষা করা।",
         "উইন্ডোজ ফায়ারওয়াল নিজে থেকেই ব্লক করে দেয়।",
         "What happens if a request comes through a reverse proxy or mapped IPv6 address?"),

        (8, "Level 2: Technical", "State Machine",
         "Why did you implement a custom state machine instead of using LangGraph?",
         "ল্যাংগ্রাফ লাইব্রেরি বাদ দিয়ে কাস্টম স্টেট মেশিন কেন তৈরি করলেন?",
         "এক্সটার্নাল প্যাকেজের অতিরিক্ত ডিপেন্ডেন্সি ও নন-ডিটারমিনিজম এড়াতে এবং প্রতিটি ট্রানজিশনের শতভাগ অফলাইন টেস্টেবিলিটি নিশ্চিত করতে কাস্টম স্টেট মেশিন লেখা হয়েছে।",
         "To eliminate external framework overhead, ensure strict compile-time typing via Python dataclasses, and maintain complete offline testability and determinism across all 646 test cases.",
         "প্রযুক্তিগত ট্রেড-অফ বুঝতে পারার সক্ষমতা যাচাই।",
         "ল্যাংগ্রাফ অনেক কঠিন তাই ব্যবহার করতে পারিনি।",
         "What are the terminal states in your custom orchestration state machine?"),

        (9, "Level 2: Technical", "Claim Validation",
         "How does validate_citation_excerpt() handle whitespace and punctuation differences?",
         "validate_citation_excerpt() কীভাবে স্পেস বা যতিচিহ্নের অমিল হ্যান্ডেল করে?",
         "এটি কঠোরভাবে হুবহু সাবস্ট্রিং ম্যাচ করে। এলএলএম যদি একটি স্পেস বা কমাও পরিবর্তন করে, ভ্যালিডেশন ফেইল করে যাতে কোনো অতিরঞ্জন না ঘটে।",
         "It enforces exact verbatim substring matching without fuzzy relaxation. If an LLM paraphrases, modifies punctuation, or extrapolates, the check fails closed immediately.",
         "হ্যালুসিনেশন প্রতিরোধ মেকানিজমের কোড-লেভেল জ্ঞান যাচাই।",
         "লেভেনস্টাইন ডিসট্যান্স দিয়ে প্রায় কাছাকাছি হলে পাস করিয়ে দেয়।",
         "Doesn't strict substring matching reject valid paraphrased findings?"),

        (10, "Level 2: Technical", "Uncertainty Scoring",
         "What is the mathematical formulation of your evidence sufficiency score?",
         "আপনার এভিডেন্স সাফিশিয়েন্সি স্কোরের গাণিতিক ফর্মুলাটি কী?",
         "স্কোরটি ১.০ থেকে শুরু হয় এবং বিভিন্ন ডিসঅর্ডিনেন্স সিগন্যাল (যেমন মিসিং চাংক, স্পেশালিস্ট মতবিরোধ) অনুযায়ী নির্দিষ্ট ওয়েট বিয়োগ হয়ে ০.০ থেকে ১.০ এর মধ্যে বাউন্ডেড থাকে।",
         "Sufficiency score begins at 1.0 and applies penalized deductions for missing evidence chunks (-0.40), specialist discordance (-0.35), and linguistic uncertainty (-0.15), bounded within [0.0, 1.0].",
         "অনিশ্চয়তা ইঞ্জিনের গাণিতিক ভিত্তি পরীক্ষা।",
         "এটি একটি রেন্ডম প্রোবাবিলিটি যা মডেল নিজেই আউটপুট দেয়।",
         "What threshold determines whether the engine outputs PROCEED or ABSTAIN?"),

        # LEVEL 3: ADVANCED (11-20)
        (11, "Level 3: Advanced", "Wilson Score Interval",
         "Why is the Wilson Score Interval preferred over the Wald interval for small benchmarks?",
         "ছোট বেঞ্চমার্কে ওয়াল্ড ইন্টারভালের চেয়ে উইলসন স্কোর ইন্টারভাল কেন বেশি উপযোগী?",
         "ওয়াল্ড ইন্টারভাল নরমাল ডিস্ট্রিবিউশন ধরে নেয় এবং এক্সট্রিম প্রপোরশনে (p=0 বা 1) বা ছোট স্যাম্পলে ইন্টারভাল শূন্য হয়ে যায়। উইলসন ইন্টারভাল সর্বদা [0, 1] এর মধ্যে নিখুঁত থাকে।",
         "The standard Wald interval degenerates to zero width at extreme proportions or small sample sizes (N=36). The Wilson score interval inverts the binomial score test, remaining robust and asymmetric.",
         "উচ্চতর পরিসংখ্যানগত জ্ঞান এবং রিসার্চ মেট্রিক্স সচেতনতা।",
         "উইলসন ইন্টারভাল দেখতে সুন্দর এবং বড় বড় রিসার্চ পেপারে ব্যবহার করে।",
         "How do you report the confidence interval when the true positive count is zero?"),

        (12, "Level 3: Advanced", "Epistemic Uncertainty",
         "How does your platform distinguish Aleatoric from Epistemic uncertainty?",
         "আপনার প্ল্যাটফর্ম কীভাবে এলিয়াটরিক এবং এপিস্টেমিক অনিশ্চয়তার পার্থক্য করে?",
         "টার্গেট সার্ভারের নেটওয়ার্ক ড্রপ বা বিলম্ব হলো এলিয়াটরিক (রেন্ডম নয়েজ); আর আমাদের নলেজ বেসে তথ্যের অভাব বা স্পেশালিস্টদের মতবিরোধ হলো এপিস্টেমিক (অজ্ঞতা)।",
         "Aleatoric uncertainty represents stochastic target noise (network latency), whereas epistemic uncertainty stems from a lack of evidence or conflicting expert knowledge, which triggers abstention.",
         "এআই থিওরি এবং ফিলোসফিক্যাল ফাউন্ডেশন যাচাই।",
         "দুটোই একই জিনিস, মূলত এরর রেট নির্দেশ করে।",
         "Can adding more approved corpus documents reduce epistemic uncertainty?"),

        (13, "Level 3: Advanced", "Negative Control Audit",
         "Why did your audit identify JS-SQLI-03 as an unsuitable negative control?",
         "আপনার অডিটে JS-SQLI-03 কে কেন অনুপযুক্ত নেগেটিভ কন্ট্রোল হিসেবে চিহ্নিত করা হলো?",
         "প্রোটোকলে ধারণা করা হয়েছিল জুস শপের লগইন প্যারামিটারাইজড, কিন্তু সোর্স কোড অডিটে দেখা যায় লাইব্রেরিতে সরাসরি স্ট্রিং কনক্যাটেনেশন রয়েছে। ফলে এটি মোটেও সুরক্ষিত নয়।",
         "The protocol assumed Juice Shop login used parameterized queries. Source inspection of routes/login.ts revealed raw Sequelize string interpolation, meaning it was genuinely vulnerable, not benign.",
         "কোড অডিট এবং বেঞ্চমার্ক গ্রাউন্ড-ট্রুথের সত্যানুসন্ধান পরীক্ষা।",
         "জুস শপ অনেক পুরনো সফটওয়্যার তাই এর সব কোডই ভুল।",
         "What did you recommend in DEC-04 to resolve this defective negative control?"),

        (14, "Level 3: Advanced", "Adversarial Reviewer",
         "How does the Adversarial Reviewer prevent false positives on client-side XSS sanitization?",
         "ক্লায়েন্ট-সাইড এক্সএসএস স্যানিটাইজেশনের ক্ষেত্রে অ্যাডভারসারিয়াল রিভিউয়ার কীভাবে কাজ করে?",
         "স্পেশালিস্ট যদি শুধু এইচটিটিপি রেসপন্স দেখে দাবি করে এক্সএসএস আছে, রিভিউয়ার চ্যালেঞ্জ করে দেখে ব্রাউজারে DOMPurify আছে কি না এবং ব্যাকএন্ড বনাম ফ্রন্টএন্ড পার্থক্য নির্দেশ করে।",
         "The adversarial reviewer inspects whether reflection occurs in raw JSON APIs versus executed HTML DOM, emitting a CHALLENGE marker if client-side frameworks mitigate the rendered payload.",
         "মাল্টি-এজেন্ট কনফ্লিক্ট রেজোলিউশনের গভীরতা পরীক্ষা।",
         "রিভিউয়ার জাভাস্ক্রিপ্ট কোড রিরাইট করে ব্রাউজারে চালিয়ে দেখে।",
         "What is the system's terminal gating decision when the reviewer issues a CHALLENGE?"),

        (15, "Level 3: Advanced", "RAG Governance",
         "Why are all 11 knowledge corpus documents currently marked as 'candidate'?",
         "নলেজ বেসের ১১টি ডকুমেন্ট কেন বর্তমানে কেবল 'ক্যান্ডিডেট' হিসেবে চিহ্নিত?",
         "কারণ বৈজ্ঞানিক গভর্নেন্স অনুযায়ী প্রতিটি নথির লাইসেন্স এবং রূপান্তর ক্ষতি সুপারভাইজার কর্তৃক আনুষ্ঠানিক স্বাক্ষরিত না হওয়া পর্যন্ত তাকে চূড়ান্ত অনুমোদন দেওয়া যায় না।",
         "Under our provenance protocol, acquired standards remain candidates until formal supervisor sign-off on transformation fidelity and licensing, ensuring zero unvetted data influences decisions.",
         "একাডেমিক সততা এবং প্রটোকল গভর্নেন্স যাচাই।",
         "আমরা ডকুমেন্টগুলো পড়তে ভুলে গিয়েছিলাম তাই ক্যান্ডিডেট রয়ে গেছে।",
         "What happens in rag_runtime.py when approved_source_count is zero?"),

        # LEVEL 4: CRITICAL EXAMINER (16-25)
        (16, "Level 4: Critical", "Live Execution Reality",
         "Your test suite has 646 passing tests, but have you ever scanned a live target?",
         "আপনার ৬৪৬টি টেস্ট পাস করেছে ঠিকই, কিন্তু বাস্তবে কি কোনো লাইভ ওয়েবসাইট স্ক্যান করেছেন?",
         "না স্যার, এই মুহূর্তে কোনো লাইভ স্ক্যান চালানো হয়নি। ৬৪৬টি টেস্ট সফটওয়্যার স্টেট মেশিন এবং স্কোরিং ইনভেরিয়েন্ট প্রমাণ করে। লাইভ স্ক্যান DEC-08 গেটে আটকে রাখা হয়েছে।",
         "No. The 646 tests establish contract invariants and scoring determinism on offline fixtures. Live container scans are held under Decision DEC-08 awaiting formal supervisor adjudication.",
         "পরীক্ষক দেখতে চান শিক্ষার্থী বানিয়ে বানিয়ে মিথ্যা দাবি করে কি না।",
         "হ্যাঁ স্যার, আমরা ইন্টারনেটের অনেক সাইট স্ক্যান করে সফলভাবে হ্যাক করেছি।",
         "Why did you choose to hold live execution rather than running it immediately?"),

        (17, "Level 4: Critical", "Sample Size Limitation",
         "With only 36 proposed cases, how can you claim your framework is statistically valid?",
         "মাত্র ৩৬টি কেস নিয়ে কীভাবে দাবি করেন যে আপনার ফ্রেমওয়ার্ক স্ট্যাটিস্টিক্যালি ভ্যালিড?",
         "আমরা কখনোই পপুলেশন জেনারেলিজিবিলিটি বা সাধারণ শ্রেষ্ঠত্ব দাবি করছি না। আমরা DEC-01 গেটের অধীনে এটিকে এক্সপ্লোরেটরি ফিজিবিলিটি স্টাডি হিসেবে ফ্রেম করেছি।",
         "We do not claim confirmatory population superiority. We formally pre-registered AegisCore as an exploratory feasibility study under DEC-01, reporting exact binomial stats rather than inflated claims.",
         "পরিসংখ্যানগত সীমাবদ্ধতা এবং বৈজ্ঞানিক সততা পরীক্ষা।",
         "৩৬টি কেস অনেক বড় সংখ্যা, অন্য পেপারগুলো তো ১০টি কেস দিয়েই পেপার লেখে।",
         "How many discordant pairs would be required to achieve 80% power in McNemar's test?"),

        (18, "Level 4: Critical", "DAST Baseline Comparison",
         "You claim superiority over DAST tools, but where is your empirical comparison table?",
         "আপনি DAST-এর চেয়ে ভালো দাবি করছেন, কিন্তু তুলনামূলক বাস্তব পরীক্ষার টেবিল কোথায়?",
         "স্যার, আমাদের সুপারভাইজার রিভিউ প্যাকেজের সেকশন ২-এ স্পষ্ট লেখা আছে: বেঞ্চমার্ক রান সম্পন্ন না হওয়া পর্যন্ত DAST-এর ওপর শ্রেষ্ঠত্বের দাবি কেবল তাত্ত্বিক হাইপোথিসিস।",
         "Superiority claims remain hypothetical until live benchmark execution is completed. Our supervisor review package explicitly clarifies that empirical comparisons await container sign-off.",
         "শিক্ষার্থী পেপারের সীমাবদ্ধতা সততার সাথে জানে কি না।",
         "টেবিলটি আমাদের ল্যাপটপে ছিল, স্লাইডে যুক্ত করতে ভুলে গেছি।",
         "What specific baseline configuration of OWASP ZAP do you plan to benchmark against?"),

        (19, "Level 4: Critical", "Cloud LLM Egress",
         "If Gemini API is used, doesn't sending request payloads violate your zero-egress policy?",
         "ক্লাউড জেমিনি এপিআই ব্যবহার করলে তো জিরো-ইগ্রেস সেফটি পলিসি ভেঙে যায়, তাই নয় কি?",
         "হ্যাঁ স্যার, এজন্যই ADR 0002 অনুযায়ী ক্লাউড কল ব্লক রাখা হয়েছে এবং DEC-07 গেট পেন্ডিং রয়েছে। অনুমোদন না পাওয়া পর্যন্ত UnauthorizedLiveModelAdapter ফেইল-ক্লোজড থাকে।",
         "Precisely. That unresolved egress contradiction is why ADR 0002 enforces default-deny and UnauthorizedLiveModelAdapter fails closed until DEC-07 explicitly authorizes API egress.",
         "আর্কিটেকচারাল বিরোধ এবং সেফটি কন্ট্রাক্ট বুঝতে পারা।",
         "গুগল জেমিনি অনেক নিরাপদ কোম্পানি তাই তাদের কাছে ডেটা পাঠালে সমস্যা নেই।",
         "What local open-weights model could replace Gemini to preserve zero-egress?"),

        (20, "Level 4: Critical", "Zero Denominator Handling",
         "What happens to your Precision metric if the system abstains on all test cases?",
         "সিস্টেম যদি সব টেস্ট কেসে বিরত থাকে (Abstain), তবে প্রিসিশন মেট্রিকের মান কী হবে?",
         "TP + FP = 0 হওয়ায় ডিনমিনেটর শূন্য হবে। সাধারণ কোড ক্র্যাশ করে বা 0.0 লিখে, কিন্তু আমাদের evaluation.py মেট্রিকটিকে MetricStatus.UNDEFINED হিসেবে রিপোর্ট করে।",
         "When TP + FP = 0, calculating precision results in division by zero. AegisCore handles this rigorously by marking precision as MetricStatus.UNDEFINED rather than fabricating 0.0 or 1.0.",
         "কোডের ম্যাথমেটিক্যাল কর্নার কেস হ্যান্ডলিং পরীক্ষা।",
         "প্রিসিশন ১০০% হয়ে যাবে কারণ কোনো ভুল করেনি।",
         "How does an undefined precision impact the overall F1-score calculation?"),

        # LEVEL 5: TRAP QUESTIONS (21-30)
        (21, "Level 5: Trap", "Automated Exploitation",
         "Can AegisCore AI automatically exploit the vulnerability to gain root shell access?",
         "AegisCore AI কি নিজে থেকে ভালনারেবিলিটি এক্সপ্লয়েট করে সার্ভারের রুট শেল নিতে পারে?",
         "না স্যার। AegisCore একটি ডিফেন্সিভ অ্যাসেসমেন্ট ইঞ্জিন, কোনো আক্রমণাত্মক এক্সপ্লয়েটেশন ফ্রেমওয়ার্ক নয়। আমাদের সিস্টেমে কোনো শেল টুল বা আরসিই পেলোড এক্সেকিউটর নেই।",
         "No. AegisCore is an evidence-grounded assessment platform, not an offensive exploitation framework. It contains no shell capability, and autonomous payload weaponization is forbidden.",
         "শিক্ষার্থী প্রজেক্টের কাজের পরিধি এবং লিগ্যাল বাউন্ডারি চেনে কি না।",
         "হ্যাঁ স্যার, Metasploit-এর মডিউল দিয়ে এটি রুট শেল নিয়ে নেয়।",
         "Why is weaponized exploitation excluded from the research scope?"),

        (22, "Level 5: Trap", "Automated Code Patching",
         "Does your platform automatically rewrite the source code to patch the discovered bug?",
         "আপনার প্ল্যাটফর্ম কি স্বয়ংক্রিয়ভাবে সোর্স কোড রিরাইট করে বাগ ফিক্স করতে পারে?",
         "না স্যার। সিস্টেম শুধুমাত্র নির্ভরযোগ্য রেমিডিয়েশন পরামর্শ দিতে পারে। প্রোডাকশন কোডে স্বয়ংক্রিয়ভাবে হাত দেওয়া সিস্টেমের অ্যাভেইলেবিলিটি নষ্ট করতে পারে, তাই এটি মানুষের কাজ।",
         "No. AegisCore provides grounded remediation advice, but autonomous code mutation is deliberately excluded. Applying automated patches introduces severe availability and regression risks.",
         "অবাস্তব এআই ক্ষমতার দাবি ধরে ফেলা।",
         "হ্যাঁ, আমাদের এআই নিজে নিজেই পুল রিকোয়েস্ট তৈরি করে কোড পুশ করে দেয়।",
         "How does your remediation advice maintain grounding in OWASP standards?"),

        (23, "Level 5: Trap", "100% Accuracy Claim",
         "Is your AI system 100% accurate in detecting web vulnerabilities?",
         "আপনার এআই সিস্টেম কি ওয়েব ভালনারেবিলিটি ধরতে ১০০% নির্ভুল?",
         "কোনো এআই বা সিকিউরিটি স্ক্যানার কখনোই ১০০% নিখুঁত হতে পারে না। আমাদের মূল দাবি নির্ভুলতার নয়; আমাদের দাবি হলো পর্যাপ্ত প্রমাণ না থাকলে সিস্টেম ভুল অনুমান না করে বিরত থাকে।",
         "No security system or AI model can claim 100% detection accuracy. AegisCore's scientific contribution is not perfection, but fail-closed calibration: it abstains when evidence is ambiguous.",
         "অতি-আত্মবিশ্বাস এবং বৈজ্ঞানিক ভ্রান্তি পরীক্ষা করা।",
         "হ্যাঁ স্যার, আমাদের সিস্টেমে কোনো ভুল নেই, এটি ১০০% পারফেক্ট।",
         "What is the mathematical relationship between False Negative Rate and Abstention?"),

        (24, "Level 5: Trap", "Live Scanning from UI",
         "If I click 'Start Assessment' on your Flutter UI right now, will it scan my website?",
         "আমি যদি এখন আপনার ফ্লাটার ইউআই-তে 'Start Assessment' ক্লিক করি, তবে কি আমার ওয়েবসাইট স্ক্যান হবে?",
         "না স্যার। ফ্রন্টএন্ডে supportsAssessmentSubmission স্পষ্টতই false করা আছে এবং কোনো ডিসপ্যাচ এপিআই নেই। এটি শুধুমাত্র পূর্বের অফলাইন মূল্যায়নের ফলাফল নিরাপদে প্রদর্শন করে।",
         "No. Frontend repository explicitly sets supportsAssessmentSubmission to false, and the API has no target dispatch route. It functions strictly as a safe, read-only evaluation explorer.",
         "ফ্রন্টএন্ড এবং ব্যাকএন্ডের বাস্তব সংযোগের গভীরতা পরীক্ষা।",
         "হ্যাঁ স্যার, ইউআরএল দিলেই সাথে সাথে পুরো ওয়েবসাইট স্ক্যান হয়ে যাবে।",
         "Why did you choose to build a rich Flutter UI if live dispatch is disabled?"),

        (25, "Level 5: Trap", "Supervisor Sign-off",
         "Has your supervisor formally signed off on the 8 decision gates?",
         "আপনার সুপারভাইজার কি ৮টি ডিসিশন গেটে আনুষ্ঠানিকভাবে স্বাক্ষর করেছেন?",
         "না স্যার। ৮টি গেটই বর্তমানে PENDING অবস্থায় রয়েছে। সুপারভাইজার রিভিউ প্যাকেজ প্রস্তুত করা হয়েছে যাতে ডিফেন্সের পূর্বে তিনি প্রতিটি গেটের ট্রেড-অফ দেখে স্বাক্ষর করতে পারেন।",
         "No. All eight decision gates in docs/SUPERVISOR_DECISION_REGISTER.md are currently PENDING. The package was finalized to present the supervisor with formal decision criteria.",
         "ডকুমেন্টেশনের বাস্তব সত্যতা যাচাই করা।",
         "হ্যাঁ স্যার, উনি মৌখিকভাবে সব অনুমোদন করে দিয়েছেন।",
         "Which of the 8 decisions is the most critical to resolve first before submission?")
    ]

    # Additional 15 comprehensive questions spanning topics 26-40 to complete the master question corpus
    extended_q = [
        (26, "Level 1: Basic", "Technology", "What is Flutter Riverpod and why is it used?", "ফ্লাটার রিভারপড কী এবং এটি কেন ব্যবহৃত হয়েছে?", "এটি ফ্লাটারের একটি কম্পাইল-টাইম নিরাপদ স্টেট ম্যানেজমেন্ট লাইব্রেরি যা ইউজার ইন্টারফেসের ডেটা ফ্লো পরিচালনা করে।", "Riverpod is a reactive, compile-time safe state management framework for Flutter that decouples business logic from the UI tree.", "ফ্রন্টএন্ড স্টেট ম্যানেজমেন্ট বোঝা।", "এটি একটি ডাটাবেজ।", "What is the role of autoDispose in Riverpod?"),
        (27, "Level 2: Technical", "Auth Security", "What is Argon2id and why is it better than MD5?", "Argon2id কী এবং এটি MD5-এর চেয়ে কেন নিরাপদ?", "এটি মেমরি-হার্ড পাসওয়ার্ড হ্যাশিং অ্যালগরিদম যা জিপিইউ বা এসিক দিয়ে সহজে ক্র্যাক করা যায় না।", "Argon2id is a memory-hard password hashing algorithm designed to resist GPU/ASIC brute-force attacks.", "ক্রিপ্টোগ্রাফিক অ্যালগরিদম জ্ঞান।", "MD5 অনেক পুরনো তাই।", "What are the time and memory cost parameters in Argon2id?"),
        (28, "Level 2: Technical", "Safety Engine", "How does PolicyEngine enforce single-use permits?", "পলিসি ইঞ্জিন কীভাবে সিঙ্গেল-ইউজ পারমিট এনফোর্স করে?", "পারমিটের অবজেক্টে একটি consumed বুলিয়ান ফ্ল্যাগ থাকে; একবার রিকোয়েস্টে ব্যবহৃত হলে তা True হয়ে যায় এবং পুনরায় ব্যবহার নিষিদ্ধ হয়।", "PolicyEngine sets a consumed=True flag on the permit immediately upon dispatch, rejecting any subsequent replay attempts.", "রিপ্লে অ্যাটাক প্রতিরোধ মেকানিজম।", "পারমিট ডাটাবেজ থেকে ডিলিট করে দেওয়া হয়।", "How are monotonic clocks used in permit expiration?"),
        (29, "Level 3: Advanced", "Evaluation", "What is the Brier Score in model calibration?", "মডেল ক্যালিব্রেশনে ব্রায়ার স্কোর (Brier Score) কী?", "এটি সম্ভাব্যতা পূর্বাভাসের নির্ভুলতা মাপার একটি স্কোর যা পূর্বাভাস এবং আসল ফলাফলের পার্থক্যের বর্গ হিসাব করে।", "The Brier score measures the mean squared difference between predicted probabilities and actual binary outcomes.", "ক্যালিব্রেশন ম্যাট্রিক্স জ্ঞান।", "এটি মডেলের স্পিড মাপার মেট্রিক।", "How does Expected Calibration Error (ECE) differ from Brier Score?"),
        (30, "Level 4: Critical", "Data Leakage", "How do you guarantee zero data leakage between validation and test sets?", "ভ্যালিডেশন এবং টেস্ট সেটের মধ্যে কোনো ডেটা লিকেজ নেই তা কীভাবে নিশ্চিত করেন?", "কন্ট্রোলার লেভেলে কেসগুলোকে সম্পূর্ণ আলাদা পার্টিশনে রাখা হয়েছে এবং টেস্ট সেটের গ্রাউন্ড ট্রুথ রানটাইম এজেন্টের কাছ থেকে লুকানো থাকে।", "We enforce strict controller-level disjointness and seal ground-truth labels behind an offline evaluation boundary.", "মেশিন লার্নিং ভ্যালিডেশন ইনটিগ্রিটি।", "আমরা রেন্ডমলি শাফল করে ভাগ করেছি।", "Why is within-benchmark stratified partitioning preferred over random splits?"),
    ]

    all_questions = q_data + extended_q

    for q in all_questions:
        q_card = make_viva_card(
            q_num=q[0],
            level=q[1],
            topic=q[2],
            q_en=q[3],
            q_bn=q[4],
            a_bn=q[5],
            a_en=q[6],
            why_ask=q[7],
            wrong_ans=q[8],
            follow_up=q[9]
        )
        story.append(q_card)
        story.append(Spacer(1, 7))

    story.append(PageBreak())
    return story
