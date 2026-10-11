import html
import re
from collections import Counter

import streamlit as st
import pdfplumber

# =====================================================================
#  PART 1: ANALYSIS FUNCTIONS (the "brain")
# =====================================================================

SECTION_ALIASES = {
    "Summary": ["summary", "profile", "objective", "about me", "professional summary",
                "career objective", "personal statement"],
    "Education": ["education", "academic background", "qualifications", "academics",
                  "educational background"],
    "Experience": ["experience", "work experience", "employment", "professional experience",
                   "internship", "internships", "work history", "employment history"],
    "Projects": ["projects", "personal projects", "academic projects", "key projects",
                 "selected projects"],
    "Skills": ["skills", "technical skills", "core skills", "key skills", "technologies",
               "skills and tools"],
    "Certifications": ["certifications", "certificates", "courses", "licenses",
                       "certifications and courses"],
    "Achievements": ["achievements", "awards", "honors", "accomplishments",
                     "awards and achievements"],
}
REQUIRED_SECTIONS = ["Education", "Skills", "Projects", "Experience"]

SKILLS_DB = {
    "Programming": ["python", "java", "c++", "c#", "javascript", "typescript", "sql",
                    "golang", "rust", "kotlin", "swift", "php", "matlab", "bash"],
    "AI / ML": ["machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
                "pytorch", "keras", "scikit-learn", "sklearn", "transformers", "llm", "opencv",
                "neural networks", "reinforcement learning", "langchain", "hugging face",
                "generative ai", "rag", "xgboost"],
    "Data": ["pandas", "numpy", "matplotlib", "seaborn", "power bi", "tableau", "excel",
             "data analysis", "data visualization", "statistics", "etl", "spark", "hadoop"],
    "Web": ["html", "css", "react", "next.js", "node.js", "express", "django", "flask",
            "fastapi", "streamlit", "tailwind", "bootstrap", "rest api", "wordpress", "figma"],
    "Databases": ["mysql", "postgresql", "mongodb", "sqlite", "firebase", "redis", "supabase"],
    "Tools / Cloud": ["git", "github", "docker", "kubernetes", "aws", "azure", "gcp",
                      "linux", "jira", "ci/cd", "postman", "jupyter"],
    "Soft skills": ["communication", "teamwork", "leadership", "problem solving",
                    "time management", "collaboration", "critical thinking"],
}

ACTION_VERBS = {
    "built", "developed", "designed", "created", "implemented", "led", "managed", "launched",
    "improved", "increased", "reduced", "optimized", "automated", "analyzed", "trained",
    "deployed", "engineered", "delivered", "achieved", "established", "streamlined",
    "collaborated", "researched", "integrated", "migrated", "architected", "organized",
    "mentored", "presented", "won", "founded", "generated", "boosted", "secured", "tested",
    "debugged", "produced", "coordinated", "applied", "constructed", "configured",
    "spearheaded", "executed", "drove", "scaled", "redesigned", "enhanced",
    "building", "developing", "designing", "creating", "implementing", "leading", "analyzing",
    "automating", "optimizing", "deploying", "training", "pitched", "contacted", "cleaned", "performed", "fetched", "wrote", "ran",
}
WEAK_PHRASES = ["responsible for", "worked on", "helped", "assisted with", "duties included",
                "involved in", "tasked with", "hard working", "hardworking", "team player",
                "detail oriented", "detail-oriented", "good communication skills"]
BULLET_CHARS = "•●▪‣◦-–*·"
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
METRIC_RE = re.compile(
    r"(\d+(\.\d+)?\s?%|[$€£]\s?\d+|\brs\.?\s?\d+|\b\d{2,}\+?\b|\b\d+(\.\d+)?\s?[kKmMx]\b|\b\d+\s+[A-Za-z]{3,})")
EMAIL_RE = re.compile(r"[\w\.\-+]+@[\w\.\-]+\.\w{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{8,}\d")

STOPWORDS = set("""a an the and or of to in for with on at by from as is are be will we you our
your this that these those it its into about over under more most such than then them they their
able ability work working team experience years year strong good great excellent knowledge etc
using use used have has had can should must including include required requirements preferred
responsibilities role job candidate looking join company skills skill plus new help make""".split())


def extract_text(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                t = re.sub(r"\(cid:\d+\)", "•", t)  # unreadable bullet symbols -> normal bullet
                text += t + "\n"
    return text


def detect_sections(text):
    found = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        norm = " ".join(re.sub(r"[^a-z ]", " ", line.lower()).split())
        matched = None
        if 0 < len(norm.split()) <= 4:
            for name, aliases in SECTION_ALIASES.items():
                if norm in aliases:
                    matched = name
                    break
        if matched:
            current = matched
            found.setdefault(current, [])
        elif current:
            found[current].append(line)
    return found


def has_phone(text):
    """True only for a real phone number (9-15 digits that are not just a run of years)."""
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 9 <= len(digits) <= 15 and not re.fullmatch(r"(?:(?:19|20)\d{2})+", digits):
            return True
    return False


def check_contact(text):
    low = text.lower()
    return {
        "Email": bool(EMAIL_RE.search(text)),
        "Phone": has_phone(text),
        "LinkedIn": "linkedin" in low,
        "GitHub / Portfolio": "github" in low or "portfolio" in low or "behance" in low,
    }


def find_skills(text):
    low = text.lower()
    result = {}
    for category, skills in SKILLS_DB.items():
        hits = [s for s in skills
                if re.search(r"(?<![a-z0-9+#])" + re.escape(s) + r"(?![a-z0-9+#])", low)]
        if hits:
            result[category] = hits
    return result


def analyze_bullets(text):
    bullets = []
    for line in text.splitlines():
        s = line.strip()
        stripped = re.sub(r"^[^\w(\[\"']+", "", s)  # remove any bullet symbol at the start
        if stripped != s and stripped[:1].isalpha() and len(stripped.split()) >= 4:
            bullets.append(stripped)
    if len(bullets) < 3:  # some PDFs lose the bullet symbols
        bullets = [l.strip() for l in text.splitlines() if len(l.split()) >= 7]
    # label lines such as "Technologies: HTML, CSS" are not achievement bullets
    bullets = [b for b in bullets if not re.match(r"^[A-Za-z&/]+( [A-Za-z&/]+){0,2}:\s", b)]

    weak_verb, no_number = [], []
    for b in bullets:
        first = re.sub(r"[^a-z]", "", b.split()[0].lower()) if b.split() else ""
        if first not in ACTION_VERBS:
            weak_verb.append(b)
        if not METRIC_RE.search(YEAR_RE.sub("", b)):
            no_number.append(b)
    n = max(len(bullets), 1)
    low = text.lower()
    return {
        "total": len(bullets),
        "verb_pct": (len(bullets) - len(weak_verb)) / n,
        "num_pct": (len(bullets) - len(no_number)) / n,
        "weak_verb": weak_verb,
        "no_number": no_number,
        "weak_phrases": [p for p in WEAK_PHRASES if p in low],
    }


def score_resume(text):
    words = len(text.split())
    sections = detect_sections(text)
    contact = check_contact(text)
    skills = find_skills(text)
    bl = analyze_bullets(text)
    issues, strengths = [], []

    # Contact (15)
    contact_score = round(15 * sum(contact.values()) / len(contact))
    for k, ok in contact.items():
        if not ok:
            issues.append(("high" if k in ("Email", "Phone") else "medium",
                           f"Missing {k}. Add it at the top of your resume."))
    if all(contact.values()):
        strengths.append("Complete contact information.")

    # Sections (25)
    present = [s for s in REQUIRED_SECTIONS if s in sections]
    missing = [s for s in REQUIRED_SECTIONS if s not in sections]
    sec_score = round(20 * len(present) / len(REQUIRED_SECTIONS))
    if "Summary" in sections:
        sec_score += 5
        strengths.append("Has a Summary/Profile section.")
    else:
        issues.append(("medium", "No Summary section. Add 2-3 lines at the top saying who you are "
                                 "and which role you target."))
    for m in missing:
        if m == "Experience" and "Projects" in sections:
            issues.append(("low", "No Experience section. Acceptable for students if Projects are "
                                  "strong. Add internships or freelance work if you have any."))
            sec_score += 3
        else:
            issues.append(("high", f"Missing '{m}' section (or its heading is not standard). "
                                   f"Use a clear heading like {m.upper()}."))
    sec_score = min(sec_score, 25)
    if len(present) == len(REQUIRED_SECTIONS):
        strengths.append("All core sections are present.")

    # Skills (15)
    total_skills = sum(len(v) for v in skills.values())
    skill_score = min(15, total_skills)
    if total_skills < 8:
        issues.append(("high", f"Only {total_skills} recognizable skills found. List at least 8-12 "
                               f"relevant tools and technologies."))
    else:
        strengths.append(f"{total_skills} recognizable skills listed.")
    if "Skills" not in sections and total_skills:
        issues.append(("medium", "Skills appear in the text but there is no dedicated Skills section. "
                                 "ATS software looks for one."))

    # Action verbs (15) + numbers (15)
    if bl["total"] == 0:
        verb_score = num_score = 0
        issues.append(("high", "No bullet points detected. Write experience and projects as bullets "
                               "that start with action verbs."))
    else:
        verb_score = round(15 * min(bl["verb_pct"] / 0.7, 1))
        num_score = round(15 * min(bl["num_pct"] / 0.4, 1))
        if bl["verb_pct"] < 0.5:
            issues.append(("high", f"Only {bl['verb_pct']*100:.0f}% of bullets start with an action "
                                   f"verb (aim for 70%+)."))
        else:
            strengths.append(f"{bl['verb_pct']*100:.0f}% of bullets start with action verbs.")
        if bl["num_pct"] < 0.25:
            issues.append(("high", f"Only {bl['num_pct']*100:.0f}% of bullets contain numbers. Add "
                                   f"measurable results (%, users, time saved, accuracy)."))
        else:
            strengths.append(f"{bl['num_pct']*100:.0f}% of bullets contain measurable results.")
    if bl["weak_phrases"]:
        issues.append(("medium", "Weak phrases found: " + ", ".join(bl["weak_phrases"]) +
                       ". Replace them with specific results."))

    # Length (15)
    if 350 <= words <= 800:
        len_score = 15
        strengths.append(f"Good length ({words} words).")
    elif 200 <= words < 350 or 800 < words <= 1000:
        len_score = 9
        issues.append(("medium", f"Length is {words} words. Ideal is 350-800."))
    else:
        len_score = 4
        issues.append(("high", f"Length is {words} words, which is too "
                               f"{'short' if words < 200 else 'long'}."))

    scores = {
        "Contact info": (contact_score, 15),
        "Sections": (sec_score, 25),
        "Skills": (skill_score, 15),
        "Action verbs": (verb_score, 15),
        "Measurable results": (num_score, 15),
        "Length": (len_score, 15),
    }
    total = sum(v[0] for v in scores.values())
    if words < 200:
        total = min(total, 55)
        issues.append(("high", "Resume is too short to be rated higher. Score is capped at 55 "
                               "until you add more detail."))
    issues.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x[0]])
    return {"total": total, "scores": scores, "issues": issues, "strengths": strengths,
            "sections": sections, "contact": contact, "skills": skills, "bullets": bl,
            "words": words}


def verdict(score):
    if score >= 80:
        return "Excellent", "#10b981", "Strong resume. Only small polish needed."
    if score >= 60:
        return "Good", "#3b82f6", "Solid base. The fixes below will raise your chances."
    if score >= 40:
        return "Needs work", "#f59e0b", "Important things are missing. Fix the red items first."
    return "Weak", "#ef4444", "This resume is likely to be filtered out. Rebuild it using the list below."


def match_job(resume_text, jd_text):
    resume_skills = {s for v in find_skills(resume_text).values() for s in v}
    jd_skills = {s for v in find_skills(jd_text).values() for s in v}
    matched = sorted(jd_skills & resume_skills)
    missing = sorted(jd_skills - resume_skills)
    tokens = re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{2,}", jd_text.lower())
    counts = Counter(t for t in tokens if t not in STOPWORDS)
    low = resume_text.lower()
    extra = [w for w, _ in counts.most_common(40) if w not in low and w not in jd_skills][:12]
    if jd_skills:
        pct = round(100 * len(matched) / len(jd_skills))
    else:
        pct = None  # no recognizable skills in the job text, so a percentage would be meaningless
    return {"percent": pct, "matched": matched, "missing": missing, "extra": extra}


def get_ai_feedback(api_key, resume_text, result, target_role):
    try:
        import anthropic
    except ImportError:
        return "The 'anthropic' package is not installed. Run in the terminal: pip install anthropic"
    summary = (f"Rule-based score: {result['total']}/100. "
               f"Bullets starting with action verbs: {result['bullets']['verb_pct']*100:.0f}%. "
               f"Bullets with numbers: {result['bullets']['num_pct']*100:.0f}%.")
    role = f"Target role: {target_role}\n" if target_role else ""
    prompt = f"""You are a blunt, experienced technical recruiter reviewing a resume.
{role}{summary}

RESUME TEXT:
\"\"\"
{resume_text[:12000]}
\"\"\"

Give feedback in this exact markdown structure:
## Overall impression
2-3 honest sentences.
## Top 5 fixes (highest impact first)
Numbered. Each fix must refer to something specific in THIS resume.
## Rewrite examples
Pick 3 weak bullets and rewrite each one stronger ("Before" / "After").
Do not invent numbers: use placeholders like [X%] for the candidate to fill in.
## What is already good
2-4 bullets.
No flattery. Do not invent facts about the candidate."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(model="claude-sonnet-5-5", max_tokens=1800,
                                     messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text
    except Exception as e:
        return f"AI feedback failed: {e}"


def build_report(result, label):
    lines = ["AI RESUME ANALYSIS REPORT", "=" * 30,
             f"Overall score: {result['total']}/100 ({label})", "", "SCORE BREAKDOWN"]
    for name, (got, out) in result["scores"].items():
        lines.append(f"  {name}: {got}/{out}")
    lines += ["", "FIX THESE"]
    lines += [f"  [{sev.upper()}] {msg}" for sev, msg in result["issues"]] or ["  Nothing major."]
    lines += ["", "ALREADY GOOD"]
    lines += [f"  - {s}" for s in result["strengths"]] or ["  -"]
    return "\n".join(lines)


# ====== UI ======
# =====================================================================
#  PART 2: THE WEB PAGE
# =====================================================================

st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄", layout="wide")

st.markdown("""
<style>
.hero {padding: 30px 34px; border-radius: 18px; margin-bottom: 22px; color: white;
       background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 55%, #db2777 100%);}
.hero h1 {margin: 0; font-size: 2.2rem; color: white; padding: 0;}
.hero p {margin: 8px 0 0 0; opacity: .92; font-size: 1.05rem;}
.card {padding: 14px 18px; border-radius: 12px; margin-bottom: 10px;
       border: 1px solid rgba(128,128,128,.25); background: rgba(128,128,128,.06);}
.high {border-left: 6px solid #ef4444;}
.medium {border-left: 6px solid #f59e0b;}
.low {border-left: 6px solid #3b82f6;}
.good {border-left: 6px solid #10b981;}
.tag {font-size: .72rem; font-weight: 700; letter-spacing: .06em; opacity: .75;}
.chip {display: inline-block; padding: 4px 13px; margin: 3px 5px 3px 0; border-radius: 999px;
       background: rgba(79,70,229,.13); border: 1px solid rgba(79,70,229,.4); font-size: .85rem;}
.chip-miss {background: rgba(239,68,68,.11); border-color: rgba(239,68,68,.45);}
.ring-wrap {position: relative; width: 170px; height: 170px; margin: 4px auto 10px auto;}
.ring {position: absolute; inset: 0; border-radius: 50%;
       -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 16px), #000 calc(100% - 15px));
       mask: radial-gradient(farthest-side, transparent calc(100% - 16px), #000 calc(100% - 15px));}
.ring-text {position: absolute; inset: 0; display: flex; flex-direction: column;
            align-items: center; justify-content: center;}
.ring-text b {font-size: 2.6rem; line-height: 1;}
.ring-text span {opacity: .6; font-size: .9rem;}
.verdict {text-align: center; font-size: 1.4rem; font-weight: 700;}
.sub {text-align: center; opacity: .8; margin-bottom: 6px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>📄 AI Resume Analyzer</h1>
  <p>Upload your resume. Get an honest score, what is missing, and exactly what to fix.</p>
</div>
""", unsafe_allow_html=True)


def chips(items, miss=False):
    if not items:
        return "<i>none</i>"
    cls = "chip chip-miss" if miss else "chip"
    return "".join(f'<span class="{cls}">{html.escape(str(i))}</span>' for i in items)


with st.sidebar:
    st.header("Settings")
    target_role = st.text_input("Target role (optional)", placeholder="e.g. AI Engineer")
    api_key = st.text_input("Anthropic API key (optional)", type="password",
                            help="Only needed for the AI Feedback tab. It is never saved.")
    st.caption("Without a key, every other tab still works.")

uploaded_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])

if uploaded_file is None:
    st.info("Upload a text-based PDF resume to begin.")
    st.stop()

try:
    with st.spinner("Reading your resume..."):
        text = extract_text(uploaded_file)
except Exception:
    st.error("This PDF could not be opened. It may be password-protected or corrupted. "
             "Remove the password or export a fresh PDF and try again.")
    st.stop()

if len(text.strip()) < 50:
    st.error("Could not read text from this PDF. It is probably a scanned image or a photo. "
             "Export your resume as a PDF from Word, Google Docs or Canva and try again.")
    st.stop()

result = score_resume(text)
label, color, message = verdict(result["total"])

tab_over, tab_skills, tab_bullets, tab_jd, tab_ai, tab_text = st.tabs(
    ["Overview", "Skills", "Bullet Points", "Job Match", "AI Feedback", "Extracted Text"])

# ---------------- Overview ----------------
with tab_over:
    left, right = st.columns([1, 2], gap="large")
    with left:
        deg = result["total"] * 3.6
        st.markdown(f"""
        <div class="ring-wrap">
          <div class="ring" style="background: conic-gradient({color} {deg}deg, rgba(128,128,128,.25) 0);"></div>
          <div class="ring-text"><b>{result['total']}</b><span>out of 100</span></div>
        </div>
        <div class="verdict" style="color:{color}">{label}</div>
        <div class="sub">{message}</div>
        """, unsafe_allow_html=True)
        st.caption(f"{result['words']} words")
        st.download_button("Download report", build_report(result, label),
                           file_name="resume_report.txt")
    with right:
        st.subheader("Score breakdown")
        for name, (got, out_of) in result["scores"].items():
            st.write(f"**{name}**: {got} / {out_of}")
            st.progress(got / out_of)

    st.divider()
    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.subheader("Fix these")
        if not result["issues"]:
            st.success("No major issues found.")
        for sev, msg in result["issues"]:
            st.markdown(f'<div class="card {sev}"><div class="tag">{sev.upper()}</div>{msg}</div>',
                        unsafe_allow_html=True)
    with col_b:
        st.subheader("Already good")
        if not result["strengths"]:
            st.warning("Nothing stands out as strong yet.")
        for s in result["strengths"]:
            st.markdown(f'<div class="card good">{s}</div>', unsafe_allow_html=True)

    st.subheader("Structure check")
    c1, c2 = st.columns(2, gap="large")
    all_sections = ["Summary", "Education", "Experience", "Projects", "Skills",
                    "Certifications", "Achievements"]
    with c1:
        st.markdown("**Sections found**")
        st.markdown(chips([s for s in all_sections if s in result["sections"]]),
                    unsafe_allow_html=True)
        st.markdown("**Sections not found**")
        st.markdown(chips([s for s in all_sections if s not in result["sections"]], miss=True),
                    unsafe_allow_html=True)
    with c2:
        st.markdown("**Contact info found**")
        st.markdown(chips([k for k, v in result["contact"].items() if v]), unsafe_allow_html=True)
        st.markdown("**Contact info missing**")
        st.markdown(chips([k for k, v in result["contact"].items() if not v], miss=True),
                    unsafe_allow_html=True)

# ---------------- Skills ----------------
with tab_skills:
    if not result["skills"]:
        st.error("No recognizable skills found. Add a Skills section with your tools and technologies.")
    for cat, items in result["skills"].items():
        st.markdown(f"**{cat}**")
        st.markdown(chips(items), unsafe_allow_html=True)

# ---------------- Bullet points ----------------
with tab_bullets:
    bl = result["bullets"]
    m1, m2, m3 = st.columns(3)
    m1.metric("Bullets found", bl["total"])
    m2.metric("Start with action verb", f"{bl['verb_pct']*100:.0f}%", help="Aim for 70% or more")
    m3.metric("Contain a number", f"{bl['num_pct']*100:.0f}%", help="Aim for 40% or more")
    if bl["weak_verb"]:
        st.subheader("Bullets that do not start with an action verb")
        for b in bl["weak_verb"][:6]:
            st.markdown(f'<div class="card medium">{html.escape(b)}</div>', unsafe_allow_html=True)
    if bl["no_number"]:
        st.subheader("Bullets with no measurable result")
        for b in bl["no_number"][:6]:
            st.markdown(f'<div class="card low">{html.escape(b)}</div>', unsafe_allow_html=True)
    if bl["weak_phrases"]:
        st.subheader("Weak phrases to remove")
        st.markdown(chips(bl["weak_phrases"], miss=True), unsafe_allow_html=True)

# ---------------- Job match ----------------
with tab_jd:
    jd = st.text_area("Paste a job description", height=220,
                      placeholder="Paste the full job posting here...")
    if jd.strip():
        m = match_job(text, jd)
        if m["percent"] is None:
            st.warning("No recognizable skills were found in this job description, so a match "
                       "percentage cannot be calculated. Paste the full job posting, including "
                       "its requirements section.")
        else:
            st.metric("Match with this job", f"{m['percent']}%")
            st.progress(m["percent"] / 100)
            st.markdown("**Skills you have that they want**")
            st.markdown(chips(m["matched"]), unsafe_allow_html=True)
            st.markdown("**Skills they want that are missing from your resume**")
            st.markdown(chips(m["missing"], miss=True), unsafe_allow_html=True)
            if m["extra"]:
                st.markdown("**Other keywords in the job post not found in your resume**")
                st.markdown(chips(m["extra"], miss=True), unsafe_allow_html=True)
            st.caption("Only add a skill to your resume if you really have it.")

# ---------------- AI feedback ----------------
with tab_ai:
    st.write("Claude reads your full resume and writes specific feedback with before and after rewrites.")
    if not api_key:
        st.info("Paste your Anthropic API key in the sidebar to enable this tab.")
    elif st.button("Generate AI feedback", type="primary"):
        with st.spinner("Claude is reviewing your resume..."):
            feedback = get_ai_feedback(api_key, text, result, target_role)
        st.markdown(feedback)

# ---------------- Raw text ----------------
with tab_text:
    st.caption("This is exactly what the analyzer sees. If it looks scrambled here, ATS software sees it scrambled too.")
    st.text_area("Extracted text", text, height=400)
