"""
Scrapes MyCareersFuture, Indeed SG, LinkedIn, and JobStreet
for jobs matching the given roles in Singapore.
"""

import re
import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright

ua = UserAgent()
MAX_PER_PORTAL = 15


def scrape_all(roles: list[str]) -> list[dict]:
    jobs = []
    for role in roles:
        jobs += _mycareersfuture(role)
        jobs += _indeed(role)
        jobs += _linkedin(role)
        jobs += _jobstreet(role)

    # Deduplicate by (title, company)
    seen, unique = set(), []
    for j in jobs:
        key = (j["title"].lower().strip(), j["company"].lower().strip())
        if key not in seen and j["title"]:
            seen.add(key)
            unique.append(j)

    return unique


def _mycareersfuture(role: str) -> list[dict]:
    jobs = []
    try:
        url = (
            "https://api.mycareersfuture.gov.sg/v2/jobs/search"
            f"?search={role.replace(' ', '%20')}"
            f"&limit={MAX_PER_PORTAL}&sortBy=new_posting_date"
        )
        r = httpx.get(url, headers={"User-Agent": ua.random}, timeout=15)
        for item in r.json().get("results", []):
            sal    = item.get("salary", {})
            s_min  = sal.get("minimum", 0)
            s_max  = sal.get("maximum", 0)
            salary = f"SGD {s_min:,} – {s_max:,}/mo" if s_min and s_max else "Not disclosed"
            skills = [s.get("skill", "") for s in item.get("skills", [])]
            jobs.append({
                "id":          None,
                "title":       item.get("title", ""),
                "company":     item.get("postedCompany", {}).get("name", ""),
                "portal":      "MyCareersFuture",
                "url":         f"https://www.mycareersfuture.gov.sg/job/{item.get('uuid','')}",
                "salary":      salary,
                "description": re.sub(r"<[^>]+>", " ", item.get("description", ""))[:400],
                "posted_date": item.get("originalPostingDate", "")[:10],
                "skills":      skills,
            })
    except Exception as e:
        print(f"[MCF error] {e}")
    print(f"[MCF] {len(jobs)} jobs found for '{role}'")
    return jobs


def _indeed(role: str) -> list[dict]:
    jobs = []
    try:
        url = f"https://sg.indeed.com/jobs?q={role.replace(' ', '+')}&l=Singapore&sort=date"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page(user_agent=ua.random)
            page.goto(url, timeout=30000)
            page.wait_for_timeout(2500)
            for card in page.query_selector_all("div.job_seen_beacon")[:MAX_PER_PORTAL]:
                try:
                    title   = _text(card, "h2.jobTitle span")
                    company = _text(card, "span.companyName")
                    salary  = _text(card, "div.salary-snippet") or "Not disclosed"
                    snippet = _text(card, "div.job-snippet")
                    date    = _text(card, "span.date")
                    link_el = card.query_selector("h2.jobTitle a")
                    path    = link_el.get_attribute("href") if link_el else ""
                    if title:
                        jobs.append({
                            "title":       title,
                            "company":     company,
                            "portal":      "Indeed",
                            "url":         f"https://sg.indeed.com{path}",
                            "salary":      salary,
                            "description": snippet[:400],
                            "posted_date": date,
                            "skills":      [],
                        })
                except Exception:
                    pass
            browser.close()
    except Exception as e:
        print(f"[Indeed error] {e}")
    print(f"[Indeed] {len(jobs)} jobs found for '{role}'")
    return jobs


def _linkedin(role: str) -> list[dict]:
    jobs = []
    try:
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={role.replace(' ', '%20')}&location=Singapore&sortBy=DD"
        )
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page(user_agent=ua.random)
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)
            for card in page.query_selector_all("div.base-card")[:MAX_PER_PORTAL]:
                try:
                    title   = _text(card, "h3.base-search-card__title")
                    company = _text(card, "h4.base-search-card__subtitle")
                    date_el = card.query_selector("time")
                    date    = date_el.get_attribute("datetime") if date_el else ""
                    link_el = card.query_selector("a.base-card__full-link")
                    link    = link_el.get_attribute("href") if link_el else ""
                    if title:
                        jobs.append({
                            "title":       title,
                            "company":     company,
                            "portal":      "LinkedIn",
                            "url":         link,
                            "salary":      "Not disclosed",
                            "description": "",
                            "posted_date": date,
                            "skills":      [],
                        })
                except Exception:
                    pass
            browser.close()
    except Exception as e:
        print(f"[LinkedIn error] {e}")
    print(f"[LinkedIn] {len(jobs)} jobs found for '{role}'")
    return jobs


def _jobstreet(role: str) -> list[dict]:
    jobs = []
    try:
        slug = role.lower().replace(" ", "-")
        url  = f"https://www.jobstreet.com.sg/jobs/{slug}-jobs-in-singapore"
        r    = httpx.get(
            url,
            headers={"User-Agent": ua.random, "Accept-Language": "en-SG,en;q=0.9"},
            timeout=15,
            follow_redirects=True,
        )
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("article[data-job-id]")[:MAX_PER_PORTAL]:
            title_el   = card.select_one("h1,h2,h3")
            company_el = card.select_one("[data-automation='advertiser-name']")
            salary_el  = card.select_one("[data-automation='job-salary']")
            snippet_el = card.select_one("[data-automation='jobShortDescription']")
            link_el    = card.select_one("a[href]")
            title = title_el.get_text(strip=True) if title_el else ""
            if title:
                jobs.append({
                    "title":       title,
                    "company":     company_el.get_text(strip=True) if company_el else "",
                    "portal":      "JobStreet",
                    "url":         f"https://www.jobstreet.com.sg{link_el['href']}" if link_el else "",
                    "salary":      salary_el.get_text(strip=True) if salary_el else "Not disclosed",
                    "description": snippet_el.get_text(strip=True)[:400] if snippet_el else "",
                    "posted_date": "",
                    "skills":      [],
                })
    except Exception as e:
        print(f"[JobStreet error] {e}")
    print(f"[JobStreet] {len(jobs)} jobs found for '{role}'")
    return jobs


def _text(el, selector: str) -> str:
    try:
        return el.query_selector(selector).inner_text().strip()
    except Exception:
        return ""
