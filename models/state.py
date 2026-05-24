from typing import TypedDict, Optional, List

class InterviewState(TypedDict):
    # Setup
    role:                str
    resume_context:      str
    jd_context:          str

    # Analysis phase
    resume_analysis:     Optional[dict]
    panel_strategy:      Optional[dict]

    # Interview flow
    phase:               str
    current_round:       int
    current_interviewer: str
    current_question:    str
    user_answer:         str
    last_answer:         str
    topics_covered:      List[str]

    # Full conversation log
    conversation:        List[dict]

    # Scorecards
    alex_scorecard:      Optional[dict]
    sara_scorecard:      Optional[dict]
    raj_scorecard:       Optional[dict]

    # Final
    debate_transcript:   str
    final_verdict:       Optional[dict]