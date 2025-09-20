from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ResearchStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentType(str, Enum):
    DEEP_RESEARCH = "deep_research"
    SYNTHESIZER = "synthesizer"

class CompetitorInfo(BaseModel):
    name: str
    industry_focus: Optional[str] = None
    market_cap: Optional[float] = None
    revenue: Optional[float] = None

class ResearchSource(BaseModel):
    url: str
    title: str
    source_type: str  # "report", "press_release", "earnings_call", etc.
    publication_date: datetime
    author: Optional[str] = None
    credibility_score: float = Field(ge=0, le=1)

class ResearchData(BaseModel):
    competitor: str
    ai_narrative: str
    key_initiatives: List[str]
    investment_data: Optional[Dict[str, Any]] = None
    market_positioning: str
    sources: List[ResearchSource]
    research_timestamp: datetime
    confidence_score: float = Field(ge=0, le=1)

class ExecutiveInsight(BaseModel):
    insight_type: str  # "opportunity", "threat", "trend", "action"
    title: str
    description: str
    business_impact: str
    recommended_action: str
    priority: str  # "high", "medium", "low"
    timeline: str  # "immediate", "short_term", "long_term"

class ExecutiveReport(BaseModel):
    report_id: str
    generation_timestamp: datetime
    executive_summary: str
    key_insights: List[ExecutiveInsight]
    competitor_analysis: List[ResearchData]
    market_opportunities: List[str]
    strategic_recommendations: List[str]
    data_sources_count: int
    research_timeframe: str

class AgentState(BaseModel):
    agent_type: AgentType
    status: ResearchStatus
    current_task: Optional[str] = None
    progress_percentage: int = Field(ge=0, le=100)
    error_message: Optional[str] = None
    last_updated: datetime

class WorkflowState(BaseModel):
    session_id: str
    research_query: str
    target_competitors: List[str]
    agents_state: Dict[str, AgentState]
    research_data: List[ResearchData] = []
    executive_report: Optional[ExecutiveReport] = None
    workflow_status: ResearchStatus
    created_at: datetime
    updated_at: datetime

class ResearchRequest(BaseModel):
    competitors: Optional[List[str]] = None  # If None, use all default competitors
    research_focus: str = "AI narrative and strategic initiatives"
    max_age_days: int = 60
    min_sources_per_competitor: int = 3

class ResearchResponse(BaseModel):
    session_id: str
    status: ResearchStatus
    message: str
    estimated_completion_time: Optional[int] = None  # minutes