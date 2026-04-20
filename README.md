# 🇸🇬 Singapore Job Assistant

A complete local web application that helps you find matching jobs in Singapore, select interested roles, and generate customised resumes and cover letters powered by Google Gemini AI.

---

## Features

- **Multi-portal job search** — scrapes MyCareersFuture, Indeed SG, LinkedIn, and JobStreet simultaneously
- **Resume-based matching** — scores and ranks every job against your uploaded resume
- **AI document generation** — generates a tailored, ATS-optimised resume and cover letter for each job via Google Gemini API
- **4-step wizard UI** — clean, responsive, single-page web app with no external JS/CSS dependencies
- **Fully local** — runs on your machine; only external calls are to job portals and the Gemini API

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn (Python) |
| Frontend | Vanilla HTML/CSS/JS (Jinja2 template, no build step) |
| AI | Google Gemini API (`gemini-2.0-flash`) |
| Scraping | Playwright (headless Chromium) + httpx + BeautifulSoup |
| Resume parsing | PyMuPDF (PDF) + python-docx (DOCX) |

---

## Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/saravanaspace/my-job-assistant.git
cd my-job-assistant
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure your Gemini API key

```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder with your key:

```
GEMINI_API_KEY=AIzaSy_your_actual_key_here
GEMINI_MODEL=gemini-2.0-flash
```

Get a free key at <https://aistudio.google.com/app/apikey>.

### 3. Run the app

```bash
python app.py
```

Open your browser at **<http://localhost:8000>**.

---

## How It Works

| Step | What happens |
|------|-------------|
| **1 – Setup** | Upload your PDF/DOCX resume, fill in your name, email, target job titles, and salary preferences. |
| **2 – Search** | The app scrapes all four portals in parallel and scores each job against your resume keywords. |
| **3 – Browse & Select** | Browse the ranked job cards, filter by portal or keyword, and tick the ones you want. |
| **4 – Generate** | Click **Generate** on any selected job to have Gemini produce a tailored resume and cover letter in Markdown. Preview and download them. |

---

## Job Portals

| Portal | Method | Notes |
|--------|--------|-------|
| MyCareersFuture | JSON API | Official Singapore government jobs portal |
| Indeed SG | Playwright (headless browser) | |
| LinkedIn | Playwright (headless browser) | Public job listings only |
| JobStreet | httpx + BeautifulSoup | |

---

## Gemini Free Tier Notes

- **gemini-2.0-flash** (default) — 15 requests/minute, 1,500 requests/day
- **gemini-1.5-flash** — also free tier, similar limits
- **gemini-1.5-pro** — higher quality, lower free quota

Each "Generate Documents" click makes **2 API calls** (resume + cover letter).  
Change the model in `.env` by setting `GEMINI_MODEL=gemini-1.5-pro` etc.

---

## Project Structure

```
my-job-assistant/
├── app.py              # FastAPI backend + all API routes
├── scraper.py          # Multi-portal job scraper
├── ai_generator.py     # Gemini resume & cover letter generator
├── resume_parser.py    # PDF/DOCX resume parser
├── requirements.txt
├── .env.example        # Copy to .env and add your API key
└── templates/
    └── index.html      # Complete single-page frontend
```

---

## Notes

- The app uses an **in-memory session** (no database). Restarting the server resets all data.
- Playwright scraping may occasionally be blocked by portals. MyCareersFuture (official API) is the most reliable source.
- Generated documents are in **Markdown** format. You can copy-paste into Google Docs or convert with Pandoc.
- The `.env` file is gitignored — never commit your API key.