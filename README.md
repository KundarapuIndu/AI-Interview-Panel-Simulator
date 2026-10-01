🎙️ AI Interview Panel Simulator

    A multi-agent AI system that simulates a real technical interview panel. Three AI interviewers ask questions based on your resume, debate your answers, and a Judge delivers a hire/no-hire verdict with a personalised coaching report.

✨ Features
    Resume-aware questions — agents read your resume before the interview starts
    3 distinct interviewers — Technical, Behavioral, and Skeptic
    Dynamic questioning — each question reacts to your previous answer
    Agent debate — interviewers discuss your performance before scoring
    Detailed verdict — hire decision, 6 dimension scores, strengths, weaknesses, and improvement roadmap
🤖 The Panel
    Agent	Role	Focus
    Sara	Behavioral	Opens the interview, probes soft skills and communication
    Alex	Technical	Drills on depth, correctness, and resume-specific projects
    Raj	Skeptic	Challenges vague claims and weak answers
    Judge	Verdict	Reads all scorecards and delivers the final decision
🗂️ Project Structure
ai-interview-panel/
├── app.py                    # Streamlit UI
├── requirements.txt
├── .env                      # API keys (not committed)
├── core/
│   └── llm.py                # Groq LLM + HuggingFace embeddings
├── agents/
│   ├── personas.py           # Prompt templates for all agents
│   └── resume_analyzer.py    # Resume analysis + panel strategy
├── rag/
│   └── resume_rag.py         # PDF parsing + ChromaDB indexing
├── models/
│   ├── schemas.py            # Pydantic output schemas
│   └── state.py              # LangGraph interview state
└── graph/
    └── interview_graph.py    # Full LangGraph interview flow
🛠️ Tech Stack
    Purpose	Tool
    LLM	Groq API — llama-3.3-70b-versatile
    Embeddings	HuggingFace all-MiniLM-L6-v2 (local)
    Vector DB	ChromaDB
    Agent Flow	LangGraph
    PDF Parsing	PyMuPDF
    UI	Streamlit
    Session Memory	LangGraph MemorySaver
🚀 Getting Started
    1. Clone the repo
    bash
    git clone https://github.com/indukundarapu/ai-interview-panel.git
    cd ai-interview-panel
    2. Create virtual environment
    bash
    python -m venv venv
    venv\Scripts\activate        # Windows
    source venv/bin/activate     # Mac/Linux
    3. Install dependencies
    bash
    pip install -r requirements.txt
    4. Set up environment variables
    
    Create a .env file in the root folder:
    
    GROQ_API_KEY=your_groq_api_key_here
    MODEL_NAME=llama-3.3-70b-versatile
    
   

    5. Run the app
    bash
    streamlit run app.py
