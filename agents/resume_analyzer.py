from core.llm import get_llm
from models.schemas import ResumeAnalysis, PanelStrategy, parse_json_safely
import time

def _call_with_retry(prompt: str, model, max_retries=4):
    llm = get_llm()
    last_error = None
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            text = response.content if hasattr(response, 'content') else str(response)
            if text and text.strip():
                return parse_json_safely(response, model).model_dump()
            print(f"Empty response attempt {attempt+1}")
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt+1} failed: {type(e).__name__}: {e}")
            if "rate" in str(e).lower() or "429" in str(e):
                wait = 20 * (attempt + 1)   # 20s, 40s, 60s
                print(f"Rate limit — waiting {wait}s...")
                time.sleep(wait)
            else:
                time.sleep(3)
    print(f"All attempts failed: {last_error}")
    return {}


def analyze_resume(resume_context: str, role: str, jd_context: str = "") -> dict:
    jd_section = f"\nJOB DESCRIPTION:\n{jd_context}" if jd_context else ""

    prompt = f"""You are an expert talent analyst preparing an interview panel.

RESUME:
{resume_context}

TARGET ROLE: {role}
{jd_section}

Analyze this resume and output ONLY this JSON, nothing else:
{{
  "skills": ["skill1", "skill2"],
  "projects": ["project1 — one line description"],
  "experience": ["exp1", "exp2"],
  "strengths": ["strength1", "strength2", "strength3"],
  "weak_areas": ["area1 — reason why"],
  "suspicious_claims": ["claim1 — why suspicious"],
  "suggested_deep_dives": ["topic1", "topic2", "topic3"]
}}"""

    return _call_with_retry(prompt, ResumeAnalysis)


def build_panel_strategy(resume_analysis: dict, role: str) -> dict:
    prompt = f"""You are coordinating a 3-person interview panel for a {role} candidate.

RESUME ANALYSIS:
Skills: {resume_analysis.get('skills', [])}
Projects: {resume_analysis.get('projects', [])}
Strengths: {resume_analysis.get('strengths', [])}
Weak Areas: {resume_analysis.get('weak_areas', [])}
Suspicious Claims: {resume_analysis.get('suspicious_claims', [])}
Suggested Deep Dives: {resume_analysis.get('suggested_deep_dives', [])}

Create a coordinated interview strategy. Output ONLY this JSON:
{{
  "alex_focus": "specific technical areas to drill",
  "sara_focus": "specific behavioral themes to explore",
  "raj_targets": ["specific claim 1 to challenge", "specific claim 2"],
  "opening_theme": "warm opening topic for Sara"
}}"""

    return _call_with_retry(prompt, PanelStrategy)