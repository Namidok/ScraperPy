
import os
import json
import requests
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = BASE_DIR
PROFILE_PATH = os.path.join(PROJECT_ROOT, "config", "profile.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "resumes", "generated")

# Ollama config
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1"  # change if needed


def load_profile():
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def call_ollama(prompt: str) -> str:
    """
    Call local Ollama model and return the generated text (non-streaming).
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")


def detect_language(text: str) -> str:
    """
    Very simple heuristic language detection between English and German.
    Returns "English" or "German".
    """
    t = (text or "").lower()

    # Common German function words / patterns
    german_markers = [
        "und", "der", "die", "das", "mit", "für", "bei", "nicht",
        "entwickeln", "bewerben", "kenntnisse", "erfahrung",
        "arbeitgeber", "bereich", "teamfähig", "studium",
        "werkstudent", "praktikum"
    ]

    english_markers = [
        "and", "the", "with", "for", "software", "engineer",
        "responsibilities", "requirements", "experience",
        "working student", "internship"
    ]

    german_score = sum(1 for w in german_markers if w in t)
    english_score = sum(1 for w in english_markers if w in t)

    if german_score > english_score:
        return "German"
    else:
        return "English"


def build_resume_prompt(profile: dict, job: dict, target_language: str) -> str:
    """
    Create a prompt that tells the model to generate a tailored resume in Markdown
    in the requested language (English or German).
    """
    profile_text = json.dumps(profile, indent=2)
    job_text = json.dumps(job, indent=2)

    language_instruction = (
        "Write the entire resume in fluent, professional English."
        if target_language.lower().startswith("en")
        else "Write the entire resume in fluent, professional German. Use clear, simple sentences suitable for a working student CV."
    )

    prompt = f"""
You are an expert resume writer for software and AI roles.

Task:
Using the CANDIDATE_PROFILE and JOB_DESCRIPTION below, create a tailored, one-to-two-page resume in clean Markdown format.

Language:
- {language_instruction}

Requirements:
- Focus on working student / junior software, data, or AI roles.
- Start with a short professional summary tailored to the job.
- Emphasize the most relevant skills for this specific job (hard skills first).
- Reorder and selectively include experience and projects that best match the job description.
- Use concise bullet points with strong action verbs and measurable impact where possible.
- Use a neutral, professional tone.
- Do NOT invent fake companies or degrees.
- You may slightly rephrase tasks to better match the job wording, but keep them truthful.
- Output ONLY the resume in Markdown (no explanation, no preamble).

CANDIDATE_PROFILE (JSON):
{profile_text}

JOB_DESCRIPTION (JSON):
{job_text}
"""
    return prompt


def sanitize_filename(text: str) -> str:
    keep = "-_.() "
    return "".join(c for c in text if c.isalnum() or c in keep).strip().replace(" ", "_")


def generate_tailored_resume(job: dict) -> str:
    """
    Main function:
    - job: dict with at least: title, company, location, description, url, platform, posted_date

    Returns full path to generated Markdown file.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    profile = load_profile()
    jd_text = job.get("description", "") or ""
    target_language = detect_language(jd_text)
    print(f"🌐 Detected job description language: {target_language}")

    prompt = build_resume_prompt(profile, job, target_language)
    print(f"🧠 Calling Ollama model '{OLLAMA_MODEL}' to generate {target_language} resume...")
    md_text = call_ollama(prompt)

    company = job.get("company", "Company")
    title = job.get("title", "Role")
    date_str = datetime.now().strftime("%Y%m%d")

    filename = f"resume_{sanitize_filename(company)}_{sanitize_filename(title)}_{date_str}.md"
    out_path = os.path.join(OUTPUT_DIR, filename)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    print(f"✅ Tailored resume saved to: {out_path}")
    return out_path


# Example usage for testing
if __name__ == "__main__":
    # Example English job
    example_job = {
        "title": "AI Engineer",
        "company": "ExampleTech GmbH",
        "location": "Berlin, Germany",
        "description": (
            "We are looking for a working student to support our engineering team. "
            "Responsibilities include building backend services in Python, working with REST APIs, "
            "writing clean and testable code, and collaborating in an Agile environment. "
            "Experience with Django or Flask, PostgreSQL, and cloud services (AWS) is a plus."
        ),
        "url": "https://example.com/job/123",
        "posted_date": "2025-12-03",
        "platform": "StepStone"
    }

    # Example German job (uncomment to test German)
    # example_job = {
    #     "title": "Werkstudent Softwareentwicklung (m/w/d)",
    #     "company": "Beispiel AG",
    #     "location": "Berlin, Deutschland",
    #     "description": (
    #         "Als Werkstudent (m/w/d) unterstützen Sie unser Entwicklungsteam bei der Umsetzung von "
    #         "Backend-Services in Python. Zu Ihren Aufgaben gehören die Entwicklung und Wartung von REST-APIs, "
    #         "die Implementierung automatisierter Tests sowie die Mitarbeit in einem agilen Scrum-Team. "
    #         "Idealerweise bringen Sie erste Erfahrungen mit Django oder Flask, PostgreSQL und AWS mit."
    #     ),
    #     "url": "https://example.com/job/456",
    #     "posted_date": "2025-12-03",
    #     "platform": "StepStone"
    # }

    generate_tailored_resume(example_job)
