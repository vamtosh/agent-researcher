from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from datetime import datetime
from backend.models.schemas import (
    ResearchData,
    ExecutiveReport,
    ResearchStatus,
    AgentState,
    AgentType
)

class CompetitiveIntelligenceState(TypedDict):
    """
    State schema for the competitive intelligence workflow.
    This represents the shared state between all agents in the LangGraph workflow.
    """

    # Session management
    session_id: str
    workflow_status: ResearchStatus
    created_at: datetime
    updated_at: datetime

    # Research parameters
    target_competitors: List[str]
    research_focus: str
    max_age_days: int
    min_sources_per_competitor: int

    # Agent states
    agents_state: Dict[str, AgentState]

    # Research data (populated by Deep Research Agent)
    research_data: List[ResearchData]

    # Executive report (populated by Synthesizer Agent)
    executive_report: Optional[ExecutiveReport]

    # Error handling
    error_messages: List[str]

    # Workflow control
    validation_result: Optional[str]
    retry_count: Optional[int]

    # Messages for logging and debugging
    messages: Annotated[List[Dict[str, Any]], add_messages]

def create_initial_state(
    session_id: str,
    target_competitors: List[str],
    research_focus: str = "AI narrative and strategic initiatives",
    max_age_days: int = 60,
    min_sources_per_competitor: int = 3
) -> CompetitiveIntelligenceState:
    """
    Create the initial state for a new competitive intelligence workflow.
    """
    current_time = datetime.now()

    return CompetitiveIntelligenceState(
        session_id=session_id,
        workflow_status=ResearchStatus.PENDING,
        created_at=current_time,
        updated_at=current_time,
        target_competitors=target_competitors,
        research_focus=research_focus,
        max_age_days=max_age_days,
        min_sources_per_competitor=min_sources_per_competitor,
        agents_state={
            "deep_research": AgentState(
                agent_type=AgentType.DEEP_RESEARCH,
                status=ResearchStatus.PENDING,
                progress_percentage=0,
                last_updated=current_time
            ),
            "synthesizer": AgentState(
                agent_type=AgentType.SYNTHESIZER,
                status=ResearchStatus.PENDING,
                progress_percentage=0,
                last_updated=current_time
            )
        },
        research_data=[],
        executive_report=None,
        error_messages=[],
        validation_result=None,
        retry_count=0,
        messages=[]
    )