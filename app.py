import streamlit as st
import uuid, os, tempfile
from rag.resume_rag import build_resume_index, get_resume_context
from graph.interview_graph import graph
from agents.personas import should_raj_ask_third

st.set_page_config(page_title="AI Interview Panel", page_icon="🎙️", layout="wide")

# ── Session init ──────────────────────────────────────────────────────────────
DEFAULTS = {
    "session_id":         str(uuid.uuid4()),
    "vectorstore":        None,
    "phase":              "setup",
    "conversation":       [],
    "current_question":   "",
    "current_interviewer":"",
    "resume_analysis":    None,
    "panel_strategy":     None,
    "alex_scorecard":     None,
    "sara_scorecard":     None,
    "raj_scorecard":      None,
    "debate_transcript":  "",
    "final_verdict":      None,
    "resume_context":     "",
    "role":               "ML Engineer",
    "topics_covered":     [],
    "last_answer":        ""
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

config = {"configurable": {"thread_id": st.session_state.session_id}}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Setup")

    if st.session_state.phase == "setup":
        st.session_state.role = st.selectbox("🎯 Target Role", [
            "ML Engineer", "Data Scientist", "Backend Engineer",
            "Frontend Engineer", "DevOps Engineer", "Full Stack Developer"
        ])
        resume_pdf = st.file_uploader("📄 Resume (PDF)", type="pdf")
        jd_text    = st.text_area("📋 Job Description (optional)", height=120)

        if resume_pdf:
            if st.button("🚀 Start Interview"):
                with st.spinner("Analyzing resume and preparing panel..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                        f.write(resume_pdf.read())
                        tmp = f.name
                    vs = build_resume_index(tmp)
                    os.unlink(tmp)
                    st.session_state.vectorstore = vs
                    context = get_resume_context(vs, st.session_state.role, k=6)
                    st.session_state.resume_context = context

                    result = graph.invoke({
                        "role":               st.session_state.role,
                        "resume_context":     context,
                        "jd_context":         jd_text or "",
                        "phase":              "analysis",
                        "current_round":      0,
                        "conversation":       [],
                        "current_question":   "",
                        "current_interviewer":"",
                        "user_answer":        "",
                        "last_answer":        "",
                        "topics_covered":     [],
                        "resume_analysis":    None,
                        "panel_strategy":     None,
                        "alex_scorecard":     None,
                        "sara_scorecard":     None,
                        "raj_scorecard":      None,
                        "debate_transcript":  "",
                        "final_verdict":      None
                    }, config=config)

                    st.session_state.resume_analysis     = result["resume_analysis"]
                    st.session_state.panel_strategy      = result["panel_strategy"]
                    st.session_state.current_question    = result["current_question"]
                    st.session_state.current_interviewer = result["current_interviewer"]
                    st.session_state.topics_covered      = result.get("topics_covered", [])
                    st.session_state.phase               = "sara_intro"
                st.rerun()
        else:
            st.info("Upload your resume to begin.")

    else:
        # ── Progress tracker ──────────────────────────────────────────────────
        st.markdown("### 📊 Progress")
        phases = [
            ("sara_intro",        "🤝 Sara — Introduction"),
            ("sara_behavioral",   "🤝 Sara — Behavioral 1"),
            ("sara_behavioral_2", "🤝 Sara — Behavioral 2"),
            ("alex_q1",           "🧑‍💻 Alex — Technical Q1"),
            ("alex_q2",           "🧑‍💻 Alex — Technical Q2"),
            ("alex_sysdesign",    "🧑‍💻 Alex — System Design"),
            ("raj_q1",            "🔍 Raj — Skeptic"),
            ("raj_cross",         "🔍 Raj — Cross Question"),
            ("raj_conditional",   "🔍 Raj — Final Challenge"),
            ("closing",           "🎤 Closing Statement"),
            ("scoring",           "📊 Scoring"),
            ("verdict",           "⚖️ Verdict"),
        ]
        phase_order = [p[0] for p in phases]
        current_idx = phase_order.index(st.session_state.phase) \
                      if st.session_state.phase in phase_order else 0

        for i, (p, label) in enumerate(phases):
            # Hide raj_conditional in sidebar unless it actually triggers
            if p == "raj_conditional" and st.session_state.phase not in (
                "raj_conditional", "closing", "scoring", "verdict"
            ):
                continue
            if i < current_idx:
                st.markdown(f"✅ {label}")
            elif i == current_idx:
                st.markdown(f"🔵 **{label}**")
            else:
                st.markdown(f"⬜ {label}")

        st.divider()

        if st.session_state.resume_analysis:
            with st.expander("🔍 Resume Analysis (Panel Only)"):
                ra = st.session_state.resume_analysis
                st.markdown("**Strengths:**")
                for s in ra.get("strengths", []):
                    st.markdown(f"• {s}")
                st.markdown("**Weak Areas:**")
                for w in ra.get("weak_areas", []):
                    st.markdown(f"• {w}")
                st.markdown("**Suspicious Claims:**")
                for c in ra.get("suspicious_claims", []):
                    st.markdown(f"• {c}")
                st.markdown("**Suggested Deep Dives:**")
                for d in ra.get("suggested_deep_dives", []):
                    st.markdown(f"• {d}")

        st.divider()

        if st.session_state.topics_covered:
            with st.expander("📌 Topics Covered So Far"):
                for t in st.session_state.topics_covered:
                    st.markdown(f"• {t}")

        st.divider()
        if st.button("🔄 Reset"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────
st.title("🎙️ AI Interview Panel Simulator")

if st.session_state.phase == "setup":
    st.markdown("### Welcome! Upload your resume in the sidebar to begin.")
    st.stop()

INTERVIEWER_ICONS = {"Sara": "🤝", "Alex": "🧑‍💻", "Raj": "🔍", "Panel": "🎤"}

# ── Phase title map ───────────────────────────────────────────────────────────
phase_titles = {
    "sara_intro":        "Round 1 — Introduction (Sara)",
    "sara_behavioral":   "Round 2 — Behavioral Follow-up (Sara)",
    "sara_behavioral_2": "Round 3 — Behavioral Deep Dive (Sara)",
    "alex_q1":           "Round 4 — Technical Interview (Alex)",
    "alex_q2":           "Round 5 — Technical Follow-up (Alex)",
    "alex_sysdesign":    "Round 6 — System Design (Alex)",
    "raj_q1":            "Round 7 — Skeptic Challenge (Raj)",
    "raj_cross":         "Round 8 — Cross Question (Raj)",
    "raj_conditional":   "Round 9 — Final Challenge (Raj)",
    "closing":           "Closing Statement",
}

# ── Linear next-phase map (Raj conditional handled separately) ────────────────
next_phases = {
    "sara_intro":        "sara_behavioral",
    "sara_behavioral":   "sara_behavioral_2",
    "sara_behavioral_2": "alex_q1",
    "alex_q1":           "alex_q2",
    "alex_q2":           "alex_sysdesign",
    "alex_sysdesign":    "raj_q1",
    "raj_q1":            "raj_cross",
    # raj_cross is handled specially below — may go to raj_conditional or closing
    "raj_conditional":   "closing",
    "closing":           "scoring",
}


# ── Helper — show completed rounds ───────────────────────────────────────────
def show_past_rounds():
    for item in st.session_state.conversation:
        interviewer = item["interviewer"]
        icon = INTERVIEWER_ICONS.get(interviewer, "💬")
        with st.expander(f"✅ {icon} {interviewer} — Completed"):
            st.markdown(f"**Q:** {item['question']}")
            st.markdown(f"**A:** {item['answer']}")


# ── Helper — invoke graph with a given target phase ───────────────────────────
def invoke_graph(next_phase: str, answer: str, context: str) -> dict:
    return graph.invoke({
        "role":               st.session_state.role,
        "resume_context":     context,
        "jd_context":         "",
        "phase":              next_phase,          # router reads this
        "conversation":       st.session_state.conversation,
        "current_question":   "",
        "current_interviewer":"",
        "user_answer":        answer,
        "last_answer":        answer,
        "topics_covered":     st.session_state.get("topics_covered", []),
        "resume_analysis":    st.session_state.resume_analysis,
        "panel_strategy":     st.session_state.panel_strategy,
        "alex_scorecard":     None,
        "sara_scorecard":     None,
        "raj_scorecard":      None,
        "debate_transcript":  "",
        "final_verdict":      None,
    }, config=config)


# ── Helper — submit answer and advance ───────────────────────────────────────
def submit_answer(answer: str, next_phase: str):
    # Save Q&A
    st.session_state.conversation.append({
        "interviewer": st.session_state.current_interviewer,
        "question":    st.session_state.current_question,
        "answer":      answer,
        "phase":       st.session_state.phase,
    })

    # ── Special case: after raj_cross, decide whether to trigger raj_conditional
    if st.session_state.phase == "raj_cross":
        if should_raj_ask_third(st.session_state.conversation):
            next_phase = "raj_conditional"
        else:
            next_phase = "closing"

    # ── If next phase is scoring, just flip phase and rerun.
    # The scoring elif block handles the graph invoke on next render.
    # Do NOT call invoke_graph("scoring") here — it runs all the way to
    # "done" in one shot and the result phase never gets rendered.
    if next_phase == "scoring":
        st.session_state.phase = "scoring"
        st.rerun()

    # RAG: candidate answer drives which resume chunks come back
    context = get_resume_context(st.session_state.vectorstore, answer, k=4)

    with st.spinner("Preparing next question..."):
        result = invoke_graph(next_phase, answer, context)

    st.session_state.current_question    = result.get("current_question", "")
    st.session_state.current_interviewer = result.get("current_interviewer", "")
    st.session_state.phase               = result.get("phase", next_phase)
    st.session_state.topics_covered      = result.get("topics_covered", [])
    st.rerun()


# ── Active interview rounds ───────────────────────────────────────────────────
active_phases = set(next_phases.keys()) | {"raj_cross"}

if st.session_state.phase in active_phases:
    show_past_rounds()

    phase = st.session_state.phase
    icon  = INTERVIEWER_ICONS.get(st.session_state.current_interviewer, "💬")

    st.markdown(f"## {phase_titles.get(phase, 'Interview')}")
    st.info(
        f"{icon} **{st.session_state.current_interviewer} asks:** "
        f"{st.session_state.current_question}"
    )

    answer = st.chat_input("Your answer...")
    if answer:
        # raj_cross next_phase is resolved inside submit_answer
        nphase = next_phases.get(phase, "closing")
        submit_answer(answer, nphase)

# ── Scoring ───────────────────────────────────────────────────────────────────
elif st.session_state.phase == "scoring":
    show_past_rounds()
    st.markdown("## ⏳ Panel is deliberating...")

    with st.spinner("Agents are scoring, debating, and reaching a verdict... (1-2 min)"):
        result = graph.invoke({
            "role":               st.session_state.role,
            "resume_context":     st.session_state.resume_context,
            "jd_context":         "",
            "phase":              "scoring",
            "conversation":       st.session_state.conversation,
            "current_question":   "",
            "current_interviewer":"",
            "user_answer":        "",
            "last_answer":        "",
            "topics_covered":     st.session_state.get("topics_covered", []),
            "resume_analysis":    st.session_state.resume_analysis,
            "panel_strategy":     st.session_state.panel_strategy,
            "alex_scorecard":     None,
            "sara_scorecard":     None,
            "raj_scorecard":      None,
            "debate_transcript":  "",
            "final_verdict":      None,
        }, config=config)

    st.session_state.alex_scorecard    = result["alex_scorecard"]
    st.session_state.sara_scorecard    = result["sara_scorecard"]
    st.session_state.raj_scorecard     = result["raj_scorecard"]
    st.session_state.debate_transcript = result["debate_transcript"]
    st.session_state.final_verdict     = result["final_verdict"]
    st.session_state.phase             = "verdict"
    st.rerun()

# ── Verdict ───────────────────────────────────────────────────────────────────
elif st.session_state.phase == "verdict":
    st.markdown("## 📋 Interview Complete — Final Report")

    with st.expander("📜 Full Interview Transcript"):
        for item in st.session_state.conversation:
            icon = INTERVIEWER_ICONS.get(item["interviewer"], "💬")
            st.markdown(f"**{icon} {item['interviewer']}:** {item['question']}")
            st.markdown(f"*You:* {item['answer']}")
            st.divider()

    st.subheader("📊 Individual Scorecards")
    c1, c2, c3 = st.columns(3)
    if st.session_state.alex_scorecard:
        with c1:
            st.metric("🧑‍💻 Alex — Technical",
                      f"{st.session_state.alex_scorecard['score']}/10")
            st.caption(st.session_state.alex_scorecard["reasoning"])
    if st.session_state.sara_scorecard:
        with c2:
            st.metric("🤝 Sara — Behavioral",
                      f"{st.session_state.sara_scorecard['score']}/10")
            st.caption(st.session_state.sara_scorecard["reasoning"])
    if st.session_state.raj_scorecard:
        with c3:
            st.metric("🔍 Raj — Skeptic",
                      f"{st.session_state.raj_scorecard['score']}/10")
            st.caption(st.session_state.raj_scorecard["reasoning"])

    with st.expander("🗣️ Panel Debate"):
        st.markdown(st.session_state.debate_transcript)

    st.divider()

    v = st.session_state.final_verdict
    decision = v.get("hire_decision", "Borderline")

    hire_colors = {
        "Strong Hire": "🟢", "Hire": "🟡",
        "Borderline":  "🟠", "No Hire": "🔴",
    }
    hire_bg = {
        "Strong Hire": "rgba(0,200,100,0.12)",
        "Hire":        "rgba(255,220,0,0.12)",
        "Borderline":  "rgba(255,140,0,0.12)",
        "No Hire":     "rgba(220,50,50,0.15)",
    }

    # ── Decision banner ───────────────────────────────────────────────────────
    bg = hire_bg.get(decision, "transparent")
    composite = v.get("composite_score", "—")
    st.markdown(
        f"""<div style="background:{bg};border-radius:10px;padding:20px 24px;margin-bottom:12px">
        <h2 style="margin:0">{hire_colors.get(decision,'⚪')} {decision}</h2>
        <p style="margin:6px 0 0;opacity:0.8">Composite score: <strong>{composite}/10</strong></p>
        </div>""",
        unsafe_allow_html=True
    )
    st.markdown(f"*{v.get('summary', '')}*")

    # ── Rejection reasons (only for No Hire / Borderline) ────────────────────
    rejection = v.get("rejection_reasons", [])
    if rejection and decision in ("No Hire", "Borderline"):
        st.divider()
        label = "❌ Why Not Hired" if decision == "No Hire" else "⚠️ Concerns That Held You Back"
        st.subheader(label)
        for r in rejection:
            st.error(r)

    # ── Dimension scores ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("📐 Dimension Scores")

    WEIGHTS = {
        "technical_depth":     0.25,
        "problem_solving":     0.20,
        "practical_knowledge": 0.20,
        "communication":       0.15,
        "confidence":          0.10,
        "ownership":           0.10,
    }

    dims = [
        ("Technical Depth",     "technical_depth",     "weight 25%"),
        ("Problem Solving",     "problem_solving",      "weight 20%"),
        ("Practical Knowledge", "practical_knowledge",  "weight 20%"),
        ("Communication",       "communication",        "weight 15%"),
        ("Confidence",          "confidence",           "weight 10%"),
        ("Ownership",           "ownership",            "weight 10%"),
    ]

    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    for i, (label, key, hint) in enumerate(dims):
        score = v.get(key, 0)
        # show delta vs passing bar (6.5) so candidate sees gap clearly
        delta = round(score - 6.5, 1)
        cols[i % 3].metric(
            label,
            f"{score}/10",
            delta=f"{delta:+.1f} vs passing",
            delta_color="normal",
            help=hint
        )

    # ── Strengths & weaknesses ────────────────────────────────────────────────
    st.divider()
    col_s, col_w = st.columns(2)
    with col_s:
        st.subheader("✅ Strengths")
        for s in v.get("strengths", []):
            st.success(s)
    with col_w:
        st.subheader("⚠️ Weaknesses")
        for w in v.get("weaknesses", []):
            st.warning(w)

    # ── Improvement roadmap ───────────────────────────────────────────────────
    st.divider()
    st.subheader("🗺️ Improvement Roadmap")
    for i, step in enumerate(v.get("improvement_roadmap", []), 1):
        st.info(f"**Step {i}:** {step}")

    # ── Agent scorecards (below verdict for context) ──────────────────────────
    st.divider()
    st.subheader("📊 Agent Scorecards")
    c1, c2, c3 = st.columns(3)
    if st.session_state.alex_scorecard:
        with c1:
            st.metric("🧑‍💻 Alex — Technical",
                      f"{st.session_state.alex_scorecard['score']}/10")
            st.caption(st.session_state.alex_scorecard["reasoning"])
    if st.session_state.sara_scorecard:
        with c2:
            st.metric("🤝 Sara — Behavioral",
                      f"{st.session_state.sara_scorecard['score']}/10")
            st.caption(st.session_state.sara_scorecard["reasoning"])
    if st.session_state.raj_scorecard:
        with c3:
            st.metric("🔍 Raj — Skeptic",
                      f"{st.session_state.raj_scorecard['score']}/10")
            st.caption(st.session_state.raj_scorecard["reasoning"])

    with st.expander("🗣️ Panel Debate"):
        st.markdown(st.session_state.debate_transcript)

    st.divider()
    if st.button("🔄 Start New Interview"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()