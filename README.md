# AI Resume Analyzer

A web app that reads a resume PDF, scores it out of 100, shows what is missing, and compares it against a job description.

Built with Python and Streamlit.

## What it does

Upload a resume as a PDF and the app gives you:

- **An overall score out of 100**, with a breakdown across 6 checks
- **A prioritized list of fixes** (high, medium, low) and a list of what is already good
- **Section check:** finds Summary, Education, Experience, Projects, Skills, Certifications and Achievements
- **Contact check:** email, phone, LinkedIn and GitHub or portfolio
- **Skill detection:** 87 skills across 7 categories
- **Bullet point analysis:** how many bullets start with an action verb and contain a measurable result, with the weak ones listed
- **Job description match:** paste a job posting to get a match percentage, the skills you have, and the skills you are missing
- **Optional AI feedback:** Claude reviews the full resume and suggests fixes and bullet rewrites (needs an Anthropic API key)
- **A downloadable report** and a view of the extracted text

## How it works

1. `pdfplumber` extracts the text from the PDF.
2. The app reads the text line by line to find section headings, and uses regular expressions to find the email and phone number.
3. It compares the text against a list of known skills and a list of action verbs.
4. Each check earns points, and the points add up to a score out of 100.
5. Streamlit displays the results in tabs.

## Scoring

| Check | Points | What is measured |
|---|---|---|
| Contact info | 15 | Email, phone, LinkedIn, GitHub or portfolio |
| Sections | 25 | Education, Skills, Projects, Experience (20 points) and Summary (5 points) |
| Skills | 15 | Number of recognized skills, 1 point each |
| Action verbs | 15 | Share of bullets that start with an action verb (full marks at 70%) |
| Measurable results | 15 | Share of bullets that contain a number (full marks at 40%) |
| Length | 15 | 350 to 800 words scores highest |

Resumes under 200 words are capped at a score of 55.

## Tech stack

- Python 3
- Streamlit (web interface)
- pdfplumber (PDF text extraction)
- Regular expressions (pattern matching)
- Anthropic API (optional AI feedback)

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/DevelopMehr/ai-resume-analyzer.git
cd ai-resume-analyzer
```

**2. Create and activate a virtual environment**

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\activate
```

macOS or Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install the dependencies**

```bash
pip install -r requirements.txt
```

**4. Run the app**

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## How to use it

1. Upload your resume as a text-based PDF.
2. Read your score and the fixes on the **Overview** tab.
3. Check the **Skills** and **Bullet Points** tabs for details.
4. To compare with a job, paste the full job posting into the **Job Match** tab and press `Ctrl + Enter`.
5. For AI feedback, paste an Anthropic API key into the sidebar and open the **AI Feedback** tab. The key is used only during your session and is never saved.

## Project structure

```
ai-resume-analyzer/
├── app.py              # analysis logic and Streamlit interface
├── requirements.txt    # Python dependencies
├── screenshots/        # images of the app
├── .gitignore
└── README.md
```

## Limitations

- The score comes from fixed rules and keyword lists, not a trained model. It measures structure and wording, not the quality of your projects.
- Sections are detected only when they use standard headings such as EDUCATION or SKILLS.
- Only skills and action verbs in the built-in lists are recognized.
- The job match compares specific skills such as Python or SQL. A job title or field on its own, such as "Artificial Intelligence", gives no result.
- Scanned or photographed resumes cannot be read. Use a text-based PDF.
- Multi-column layouts can scramble the extracted text.
- English resumes only.
- Resumes are processed in memory and are not stored. If you use the AI feedback tab, the resume text is sent to the Anthropic API.

## Future improvements

- DOCX resume support
- OCR for scanned PDFs
- Semantic matching between a resume and a job description
- A larger, configurable skills database
- Role-specific scoring, for example AI engineer versus web developer

## Author

**Mehr Hussain**, Artificial Intelligence student at the University of Sindh

[GitHub](https://github.com/DevelopMehr) · [LinkedIn](https://www.linkedin.com/in/mehr-hussain-ai/) · [Portfolio](https://mehr-portfolio.netlify.app/)
