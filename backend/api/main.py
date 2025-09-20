import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from backend.models.schemas import (
    ResearchRequest,
    ResearchResponse,
    ExecutiveReport,
    ResearchStatus,
    WorkflowState
)
from agents.orchestrator.workflow import competitive_intelligence_workflow
from backend.services.cache import research_cache
from config.settings import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# In-memory storage for workflow states (in production, use database)
workflow_sessions: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    logger.info("Starting TCS Competitive Intelligence API")
    yield
    logger.info("Shutting down TCS Competitive Intelligence API")

app = FastAPI(
    title="TCS Competitive Intelligence API",
    description="Multi-agent system for analyzing AI narratives of TCS competitors",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/competitors")
async def get_competitors() -> List[str]:
    """
    Get the list of TCS competitors for research.
    """
    return settings.tcs_competitors

@app.post("/research/start", response_model=ResearchResponse)
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Start a new competitive intelligence research workflow.
    """
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())

        # Use default competitors if none specified
        target_competitors = request.competitors or settings.tcs_competitors

        # Validate request
        if not target_competitors:
            raise HTTPException(status_code=400, detail="No competitors specified")

        if request.max_age_days < 1 or request.max_age_days > 365:
            raise HTTPException(status_code=400, detail="max_age_days must be between 1 and 365")

        # Create research response
        response = ResearchResponse(
            session_id=session_id,
            status=ResearchStatus.PENDING,
            message=f"Research initiated for {len(target_competitors)} competitors",
            estimated_completion_time=25  # minutes
        )

        # Start workflow in background
        background_tasks.add_task(
            execute_research_workflow,
            session_id,
            target_competitors,
            request.research_focus,
            request.max_age_days,
            request.min_sources_per_competitor
        )

        # Store initial state
        workflow_sessions[session_id] = {
            "status": ResearchStatus.PENDING,
            "created_at": datetime.now(),
            "target_competitors": target_competitors,
            "research_focus": request.research_focus
        }

        logger.info(f"Research workflow started for session {session_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to start research: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start research: {str(e)}")

async def execute_research_workflow(
    session_id: str,
    target_competitors: List[str],
    research_focus: str,
    max_age_days: int,
    min_sources_per_competitor: int
):
    """
    Execute the research workflow in the background.
    """
    try:
        logger.info(f"Executing research workflow for session {session_id}")

        # Update session status
        if session_id in workflow_sessions:
            workflow_sessions[session_id]["status"] = ResearchStatus.IN_PROGRESS

        # Execute workflow
        final_state = await competitive_intelligence_workflow.execute_workflow(
            session_id=session_id,
            target_competitors=target_competitors,
            research_focus=research_focus,
            max_age_days=max_age_days,
            min_sources_per_competitor=min_sources_per_competitor
        )

        # Update session with final state
        workflow_sessions[session_id] = {
            "status": final_state["workflow_status"],
            "created_at": workflow_sessions[session_id]["created_at"],
            "completed_at": datetime.now(),
            "target_competitors": target_competitors,
            "research_focus": research_focus,
            "final_state": final_state
        }

        logger.info(f"Research workflow completed for session {session_id} with status: {final_state['workflow_status']}")

    except Exception as e:
        logger.error(f"Research workflow failed for session {session_id}: {str(e)}")
        # Update session with error status
        if session_id in workflow_sessions:
            workflow_sessions[session_id]["status"] = ResearchStatus.FAILED
            workflow_sessions[session_id]["error"] = str(e)

@app.get("/research/{session_id}/status")
async def get_research_status(session_id: str):
    """
    Get the current status of a research workflow.
    """
    try:
        if session_id not in workflow_sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        session_data = workflow_sessions[session_id]

        # Get current workflow state if available
        workflow_state = await competitive_intelligence_workflow.get_workflow_state(session_id)

        if workflow_state:
            return {
                "session_id": session_id,
                "status": workflow_state["workflow_status"],
                "agents_state": workflow_state["agents_state"],
                "created_at": session_data["created_at"],
                "updated_at": workflow_state["updated_at"],
                "target_competitors": workflow_state["target_competitors"],
                "messages": workflow_state.get("messages", [])[-5:],  # Last 5 messages
                "error_messages": workflow_state.get("error_messages", [])
            }
        else:
            return {
                "session_id": session_id,
                "status": session_data["status"],
                "created_at": session_data["created_at"],
                "target_competitors": session_data["target_competitors"],
                "error": session_data.get("error")
            }

    except Exception as e:
        logger.error(f"Failed to get research status for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get research status")

@app.get("/research/{session_id}/report", response_model=ExecutiveReport)
async def get_executive_report(session_id: str):
    """
    Get the executive report for a completed research workflow.
    """
    try:
        if session_id not in workflow_sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        session_data = workflow_sessions[session_id]

        if session_data["status"] != ResearchStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Research not completed yet")

        # Get final state with executive report
        final_state = session_data.get("final_state")
        if not final_state or not final_state.get("executive_report"):
            raise HTTPException(status_code=404, detail="Executive report not found")

        return final_state["executive_report"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get executive report for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get executive report")

@app.get("/research/sessions")
async def list_research_sessions():
    """
    List all research sessions.
    """
    try:
        sessions = []
        for session_id, session_data in workflow_sessions.items():
            sessions.append({
                "session_id": session_id,
                "status": session_data["status"],
                "created_at": session_data["created_at"],
                "target_competitors": session_data["target_competitors"],
                "research_focus": session_data["research_focus"]
            })

        # Sort by creation time (newest first)
        sessions.sort(key=lambda x: x["created_at"], reverse=True)
        return sessions

    except Exception as e:
        logger.error(f"Failed to list research sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list research sessions")

@app.delete("/research/{session_id}")
async def delete_research_session(session_id: str):
    """
    Delete a research session.
    """
    try:
        if session_id not in workflow_sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        del workflow_sessions[session_id]
        logger.info(f"Deleted research session {session_id}")

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

@app.get("/cache/info")
async def get_cache_info():
    """
    Get information about cached research data.
    """
    try:
        cache_info = research_cache.get_cache_info()
        return cache_info
    except Exception as e:
        logger.error(f"Failed to get cache info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get cache information")

@app.delete("/cache/clear")
async def clear_cache(competitor: str = None):
    """
    Clear cache for a specific competitor or all cache.
    """
    try:
        deleted_count = research_cache.clear_cache(competitor)
        message = f"Cleared {deleted_count} cache files"
        if competitor:
            message += f" for {competitor}"

        logger.info(message)
        return {"message": message, "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@app.post("/cache/cleanup")
async def cleanup_expired_cache():
    """
    Clean up expired cache files.
    """
    try:
        deleted_count = research_cache.cleanup_expired_cache()
        message = f"Cleaned up {deleted_count} expired cache files"

        logger.info(message)
        return {"message": message, "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Failed to cleanup cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cleanup expired cache")

@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "TCS Competitive Intelligence API",
        "version": "1.0.0",
        "description": "Multi-agent system for analyzing AI narratives of TCS competitors",
        "endpoints": {
            "health": "/health",
            "competitors": "/competitors",
            "start_research": "/research/start",
            "research_status": "/research/{session_id}/status",
            "executive_report": "/research/{session_id}/report",
            "list_sessions": "/research/sessions",
            "cache_info": "/cache/info",
            "clear_cache": "/cache/clear",
            "cleanup_cache": "/cache/cleanup"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development"
    )