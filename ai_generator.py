"""
Calls Google Gemini API to generate tailored resume
and cover letter in Markdown.

Free tier:  gemini-2.0-flash  -> 15 req/min, 1,500 req/day
Docs:       https://ai.google.dev/gemini-api/docs
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
model      = genai.GenerativeModel(MODEL_NAME)


def _chat(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
    config = genai.types.GenerationConfig(
        temperature=temperature,
        max_output_tokens=3000,
    )
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    response    = model.generate_content(full_prompt, generation_config=config)
    return response.text


def generate_resume(resume_text: str, job: dict, profile: dict) -> str:
    system = (
        "You are an expert Singapore career coach and ATS-optimised resume writer. "
        "Tailor the candidate's resume specifically for the given job. "
        "Rewrite the professional summary to directly address the role, "
        "reorder and rewrite experience bullet points to match job requirements, "
        "and add a Key Skills section using keywords from the job description. "
        "Keep it truthful — do NOT fabricate or invent any experience. "
        "Output clean Markdown only, suitable for a max 2-page resume."
    )
    user = f"""## Candidate Resume
{resume_text}

## Target Job
Title:       {job['title']}
Company:     {job['company']}
Portal:      {job['portal']}
Salary:      {job['salary']}
Description: {job.get('description', 'N/A')}
Skills:      {', '.join(job.get('skills', []))}

## Candidate Details
Name:  {profile.get('name', '')}
Email: {profile.get('email', '')}

Produce the tailored resume in Markdown now."""

    return _chat(system, user, temperature=0.4)


def generate_cover_letter(resume_text: str, job: dict, profile: dict) -> str:
    from datetime import date

    system = (
        "You are a professional cover letter writer specialising in Singapore's job market. "
        "Write a compelling, personalised cover letter with exactly 3-4 paragraphs: "
        "1) A strong opening hook specific to the company and role. "
        "2) Connect the candidate's top 3 achievements directly to the role requirements. "
        "3) Show cultural fit, enthusiasm for the company, and knowledge of Singapore's industry. "
        "4) A confident, polite call to action. "
        "Tone: formal but warm. Use Singapore English. Output clean Markdown only."
    )
    user = f"""## Candidate
Name:    {profile.get('name', '')}
Email:   {profile.get('email', '')}
Date:    {date.today().strftime('%d %B %Y')}
Resume:  {resume_text[:2500]}

## Job
Title:       {job['title']}
Company:     {job['company']}
Description: {job.get('description', '')}

Write the cover letter addressed to the Hiring Manager at {job['company']}."""

    return _chat(system, user, temperature=0.6)
