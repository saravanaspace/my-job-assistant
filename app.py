"""
Singapore Job Assistant - Local Web App
Run:  python app.py
Open: http://localhost:8000
"""

import re
import asyncio
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel

from resume_parser import parse_resume
from scraper       import scrape_all
from ai_generator  import generate_resume, generate_cover_letter

SESSION: dict = {
    "profile":     None,
    "resume_text": None,
    "jobs":        [],
    "generated":   {},
}

app       = FastAPI(title="Singapore Job Assistant")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/setup")
async def setup(
    resume:               UploadFile = File(...),
    name:                 str        = Form(...),
    email:                str        = Form(...),
    phone:                str        = Form(""),
    target_roles:         str        = Form(...),
    preferred_industries: str        = Form(""),
    min_salary:           int        = Form(0),
    employment_type:      str        = Form("full-time"),
):
    if not resume.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(400, "Only PDF or DOCX resumes are accepted.")

    file_bytes = await resume.read()

    try:
        resume_text = parse_resume(file_bytes, resume.filename)
    except Exception as e:
        raise HTTPException(400, f"Could not parse resume: {e}")

    if not resume_text.strip():
        raise HTTPException(400, "Resume appears to be empty or unreadable.")

    roles      = [r.strip() for r in target_roles.split(",")        if r.strip()]
    industries = [i.strip() for i in preferred_industries.split(",") if i.strip()]

    SESSION["resume_text"] = resume_text
    SESSION["profile"] = {
        "name":                 name,
        "email":                email,
        "phone":                phone,
        "target_roles":         roles,
        "preferred_industries": industries,
        "min_salary":           min_salary,
        "employment_type":      employment_type,
    }

    return {"ok": True, "resume_chars": len(resume_text), "roles": roles}


@app.post("/api/search")
async def search():
    if not SESSION["profile"]:
        raise HTTPException(400, "Complete setup first.")

    roles = SESSION["profile"]["target_roles"]

    loop = asyncio.get_event_loop()
    jobs = await loop.run_in_executor(None, scrape_all, roles)

    resume_words = set(_tokens(SESSION["resume_text"]))
    for i, job in enumerate(jobs):
        job["id"] = i + 1
        job_words   = set(_tokens(f"{job['title']} {job['description']} {' '.join(job['skills'])}"))
        overlap     = len(resume_words & job_words)
        title_boost = 20 if any(
            r.lower() in job["title"].lower()
            for r in SESSION["profile"]["target_roles"]
        ) else 0
        job["match_score"] = min(round((overlap / max(len(job_words), 1)) * 120 + title_boost, 1), 99)
        job["selected"]    = False

    min_sal = SESSION["profile"].get("min_salary", 0)
    if min_sal > 0:
        jobs = [j for j in jobs if _max_salary(j["salary"]) >= min_sal or j["salary"] == "Not disclosed"]

    jobs.sort(key=lambda x: x["match_score"], reverse=True)
    SESSION["jobs"] = jobs

    return {"total": len(jobs), "jobs": jobs}


@app.get("/api/jobs")
async def get_jobs():
    return {"jobs": SESSION["jobs"], "total": len(SESSION["jobs"])}


class SelectionPayload(BaseModel):
    selected_ids: list[int]


@app.post("/api/select")
async def select_jobs(payload: SelectionPayload):
    ids = set(payload.selected_ids)
    for job in SESSION["jobs"]:
        job["selected"] = job["id"] in ids
    return {"selected_count": len(ids)}


class GeneratePayload(BaseModel):
    job_id: int


@app.post("/api/generate")
async def generate(payload: GeneratePayload):
    job = next((j for j in SESSION["jobs"] if j["id"] == payload.job_id), None)
    if not job:
        raise HTTPException(404, "Job not found.")
    if not SESSION["resume_text"]:
        raise HTTPException(400, "Resume not uploaded.")
    if not SESSION["profile"]:
        raise HTTPException(400, "Profile not set up.")

    loop = asyncio.get_event_loop()
    resume_md, cover_md = await asyncio.gather(
        loop.run_in_executor(None, generate_resume,       SESSION["resume_text"], job, SESSION["profile"]),
        loop.run_in_executor(None, generate_cover_letter, SESSION["resume_text"], job, SESSION["profile"]),
    )

    SESSION["generated"][payload.job_id] = {
        "resume_md":       resume_md,
        "cover_letter_md": cover_md,
    }

    return {
        "job_id":          payload.job_id,
        "resume_md":       resume_md,
        "cover_letter_md": cover_md,
    }


@app.get("/api/generated/{job_id}")
async def get_generated(job_id: int):
    docs = SESSION["generated"].get(job_id)
    if not docs:
        raise HTTPException(404, "Not generated yet.")
    return docs


def _tokens(text: str) -> list[str]:
    return re.findall(r"\b[a-z]{3,}\b", (text or "").lower())


def _max_salary(salary_str: str) -> int:
    nums = re.findall(r"\d[\d,]*", salary_str.replace(",", ""))
    return max((int(n) for n in nums if n.isdigit()), default=0)


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
