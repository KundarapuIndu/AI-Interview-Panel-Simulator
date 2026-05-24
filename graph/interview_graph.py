import time
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from core.llm import get_llm
from models.state import InterviewState
from models.schemas import AgentScore, JudgeVerdict, parse_json_safely
from agents.resume_analyzer import analyze_resume, build_panel_strategy
from agents.personas import (
    sara_intro_prompt, sara_behavioral_prompt, sara_behavioral_2_prompt,
    sara_score_prompt,
    alex_technical_prompt, alex_followup_prompt, alex_sysdesign_prompt,
    alex_score_prompt,
    raj_skeptic_prompt, raj_crossquestion_prompt, raj_conditional_prompt,
    raj_score_prompt, should_raj_ask_third,
    debate_prompt, JUDGE_PROMPT
)

# ── Retry helper ──────────────────────────────────────────────────────────────
def call_llm(messages, max_retries=3):
    llm = get_llm()
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]

    last_error = None
    for attempt in range(max_retries):
        try:
            response = llm.invoke(messages)
            text = response.content if hasattr(response, 'content') else str(response)
            if text and text.strip():
                return response
            print(f"Attempt {attempt+1}: Empty response, retrying...")
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt+1} error: {type(e).__name__}: {e}")
            if "rate" in str(e).lower() or "429" in str(e):
                print("Rate limit — waiting 15s...")
                time.sleep(15)
            elif "connection" in str(e).lower() or "timeout" in str(e).lower():
                time.sleep(5)
            else:
                time.sleep(2)

    raise ValueError(f"LLM failed after {max_retries} attempts. Last: {last_error}")


def get_text(response) -> str:
    return response.content.strip() if hasattr(response, 'content') else str(response).strip()


# ── ROUTER ────────────────────────────────────────────────────────────────────
def router_node(state: InterviewState) -> dict:
    """Pass-through. Conditional edge reads state['phase'] and dispatches."""
    return {}


def route_by_phase(state: InterviewState) -> str:
    phase = state.get("phase", "analysis")
    valid = {
        "analysis", "sara_intro", "sara_behavioral", "sara_behavioral_2",
        "alex_q1", "alex_q2", "alex_sysdesign",
        "raj_q1", "raj_cross", "raj_conditional",
        "closing", "scoring", "debate", "verdict", "done",
    }
    if phase not in valid:
        print(f"[router] Unknown phase '{phase}' — defaulting to analysis")
        return "analysis"
    print(f"[router] → {phase}")
    return phase


# ── Phase 1: Analysis ─────────────────────────────────────────────────────────
def analysis_node(state: InterviewState) -> dict:
    print("Starting resume analysis...")
    analysis = analyze_resume(
        state["resume_context"], state["role"], state.get("jd_context", "")
    )
    time.sleep(3)
    print("Building panel strategy...")
    strategy = build_panel_strategy(analysis, state["role"])
    return {
        "resume_analysis": analysis,
        "panel_strategy":  strategy,
        "phase":           "sara_intro",
    }


# ── Phase 2: Sara (3 rounds) ──────────────────────────────────────────────────
def sara_intro_node(state: InterviewState) -> dict:
    time.sleep(3)
    prompt   = sara_intro_prompt(
        state["resume_analysis"], state["panel_strategy"], state["role"]
    )
    question = get_text(call_llm(prompt))
    return {
        "current_question":    question,
        "current_interviewer": "Sara",
        "phase":               "sara_intro",
        "last_answer":         "",
        "topics_covered":      [],
    }


def sara_behavioral_node(state: InterviewState) -> dict:
    prompt   = sara_behavioral_prompt(
        state["resume_analysis"], state["panel_strategy"],
        state["role"], state["conversation"]
    )
    question = get_text(call_llm(prompt))
    return {
        "current_question":    question,
        "current_interviewer": "Sara",
        "phase":               "sara_behavioral",
        "topics_covered":      state.get("topics_covered", []) + [question],
    }


def sara_behavioral_2_node(state: InterviewState) -> dict:
    prompt   = sara_behavioral_2_prompt(
        state["resume_analysis"], state["panel_strategy"],
        state["role"], state["conversation"]
    )
    question = get_text(call_llm(prompt))
    return {
        "current_question":    question,
        "current_interviewer": "Sara",
        "phase":               "sara_behavioral_2",
        "topics_covered":      state.get("topics_covered", []) + [question],
    }


# ── Phase 3: Alex (3 rounds) ──────────────────────────────────────────────────
def alex_q1_node(state: InterviewState) -> dict:
    prompt   = alex_technical_prompt(
        state["resume_analysis"], state["panel_strategy"],
        state["role"], state["conversation"]
    )
    question = get_text(call_llm(prompt))
    return {
        "current_question":    question,
        "current_interviewer": "Alex",
        "phase":               "alex_q1",
    }


def alex_q2_node(state: InterviewState) -> dict:
    prompt   = alex_followup_prompt(
        state["resume_analysis"], state["conversation"]
    )
    question = get_text(call_llm(prompt))
    return {
        "current_question":    question,
        "current_interviewer": "Alex",
        "phase":               "alex_q2",
        "last_answer":         state["conversation"][-1]["answer"] if state["conversation"] else "",
        "topics_covered":      state.get("topics_covered", []) + [question],
    }


def alex_sysdesign_node(state: InterviewState) -> dict:
    prompt   = alex_sysdesign_prompt(
        state["resume_analysis"], state["role"], state["conversation"]
    )
    question = get_text(call_llm(prompt))
    return {
        "current_question":    question,
        "current_interviewer": "Alex",
        "phase":               "alex_sysdesign",
        "topics_covered":      state.get("topics_covered", []) + [question],
    }


# ── Phase 4: Raj (2 + optional 3rd) ──────────────────────────────────────────
def raj_q1_node(state: InterviewState) -> dict:
    prompt   = raj_skeptic_prompt(
        state["resume_analysis"], state["panel_strategy"],
        state["role"], state["conversation"]
    )
    question = get_text(call_llm(prompt))
    return {
        "current_question":    question,
        "current_interviewer": "Raj",
        "phase":               "raj_q1",
    }


def raj_crossq_node(state: InterviewState) -> dict:
    alex_exchanges = [c for c in state["conversation"] if c["interviewer"] == "Alex"]
    if alex_exchanges:
        last   = alex_exchanges[-1]
        prompt = raj_crossquestion_prompt(
            state["resume_analysis"], state["conversation"],
            last["question"], last["answer"]
        )
    else:
        prompt = raj_skeptic_prompt(
            state["resume_analysis"], state["panel_strategy"],
            state["role"], state["conversation"]
        )
    question = get_text(call_llm(prompt))
    return {
        "current_question":    question,
        "current_interviewer": "Raj",
        "phase":               "raj_cross",
        "last_answer":         state["conversation"][-1]["answer"] if state["conversation"] else "",
        "topics_covered":      state.get("topics_covered", []) + [question],
    }


def raj_conditional_node(state: InterviewState) -> dict:
    """Raj's optional 3rd question — only reached if candidate was vague."""
    prompt   = raj_conditional_prompt(
        state["resume_analysis"], state["conversation"]
    )
    question = get_text(call_llm(prompt))
    return {
        "current_question":    question,
        "current_interviewer": "Raj",
        "phase":               "raj_conditional",
        "topics_covered":      state.get("topics_covered", []) + [question],
    }


# ── Phase 5: Closing ──────────────────────────────────────────────────────────
def closing_node(state: InterviewState) -> dict:
    return {
        "current_question":    (
            "That concludes our questions. Is there anything you'd like to add — "
            "something we didn't cover, or anything you'd like to clarify about your background?"
        ),
        "current_interviewer": "Panel",
        "phase":               "closing",
    }


# ── Phase 6: Scoring ──────────────────────────────────────────────────────────
def scoring_node(state: InterviewState) -> dict:
    convo   = state["conversation"]
    alex_qa = [c for c in convo if c["interviewer"] == "Alex"]
    raj_qa  = [c for c in convo if c["interviewer"] == "Raj"]
    sara_qa = [c for c in convo if c["interviewer"] in ["Sara", "Panel"]]

    alex_score = None
    if alex_qa:
        r = call_llm(alex_score_prompt(state["resume_analysis"], state["role"], alex_qa[0]))
        alex_score = parse_json_safely(r, AgentScore).model_dump()

    sara_score = None
    if sara_qa:
        r = call_llm(sara_score_prompt(state["resume_analysis"], state["role"], sara_qa))
        sara_score = parse_json_safely(r, AgentScore).model_dump()

    raj_score = None
    if raj_qa:
        r = call_llm(raj_score_prompt(state["resume_analysis"], state["role"], raj_qa))
        raj_score = parse_json_safely(r, AgentScore).model_dump()

    return {
        "alex_scorecard": alex_score,
        "sara_scorecard": sara_score,
        "raj_scorecard":  raj_score,
        "phase":          "debate",
    }


# ── Phase 7: Debate ───────────────────────────────────────────────────────────
def debate_node(state: InterviewState) -> dict:
    scorecards = {
        "alex": state["alex_scorecard"],
        "sara": state["sara_scorecard"],
        "raj":  state["raj_scorecard"],
    }
    parts = []
    for agent in ["Alex", "Sara", "Raj"]:
        prompt   = debate_prompt(agent, scorecards, state["conversation"])
        response = call_llm(prompt)
        parts.append(f"**{agent}:** {get_text(response)}")

    return {
        "debate_transcript": "\n\n".join(parts),
        "phase":             "verdict",
    }


# ── Phase 8: Judge ────────────────────────────────────────────────────────────
def judge_node(state: InterviewState) -> dict:
    convo_text = "\n".join([
        f"[{c['interviewer']}] Q: {c['question']}\nCandidate: {c['answer']}"
        for c in state["conversation"]
    ])
    context = f"""
FULL INTERVIEW TRANSCRIPT:
{convo_text}

SCORECARDS:
Alex: {state['alex_scorecard']}
Sara: {state['sara_scorecard']}
Raj:  {state['raj_scorecard']}

PANEL DEBATE:
{state['debate_transcript']}
"""
    response = call_llm([
        {"role": "system", "content": JUDGE_PROMPT},
        {"role": "user",   "content": context},
    ])
    verdict = parse_json_safely(response, JudgeVerdict)
    return {"final_verdict": verdict.model_dump(), "phase": "done"}


# ── Build graph ───────────────────────────────────────────────────────────────
memory  = MemorySaver()
builder = StateGraph(InterviewState)

builder.add_node("router",            router_node)
builder.add_node("analysis",          analysis_node)
builder.add_node("sara_intro",        sara_intro_node)
builder.add_node("sara_behavioral",   sara_behavioral_node)
builder.add_node("sara_behavioral_2", sara_behavioral_2_node)
builder.add_node("alex_q1",           alex_q1_node)
builder.add_node("alex_q2",           alex_q2_node)
builder.add_node("alex_sysdesign",    alex_sysdesign_node)
builder.add_node("raj_q1",            raj_q1_node)
builder.add_node("raj_cross",         raj_crossq_node)
builder.add_node("raj_conditional",   raj_conditional_node)
builder.add_node("closing",           closing_node)
builder.add_node("scoring",           scoring_node)
builder.add_node("debate",            debate_node)
builder.add_node("judge",             judge_node)

# Entry: always the router
builder.set_entry_point("router")

builder.add_conditional_edges(
    "router",
    route_by_phase,
    {
        "analysis":          "analysis",
        "sara_intro":        "sara_intro",
        "sara_behavioral":   "sara_behavioral",
        "sara_behavioral_2": "sara_behavioral_2",
        "alex_q1":           "alex_q1",
        "alex_q2":           "alex_q2",
        "alex_sysdesign":    "alex_sysdesign",
        "raj_q1":            "raj_q1",
        "raj_cross":         "raj_cross",
        "raj_conditional":   "raj_conditional",
        "closing":           "closing",
        "scoring":           "scoring",
        "debate":            "debate",
        "verdict":           "judge",
        "done":              END,
    }
)

# analysis always chains into sara_intro, then stops for user input
builder.add_edge("analysis",          "sara_intro")

# Every question node stops for user input
builder.add_edge("sara_intro",        END)
builder.add_edge("sara_behavioral",   END)
builder.add_edge("sara_behavioral_2", END)
builder.add_edge("alex_q1",           END)
builder.add_edge("alex_q2",           END)
builder.add_edge("alex_sysdesign",    END)
builder.add_edge("raj_q1",            END)
builder.add_edge("raj_cross",         END)
builder.add_edge("raj_conditional",   END)
builder.add_edge("closing",           END)

# Scoring pipeline is fully automatic
builder.add_edge("scoring", "debate")
builder.add_edge("debate",  "judge")
builder.add_edge("judge",   END)

graph = builder.compile(checkpointer=memory)