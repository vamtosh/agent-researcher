import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents.state import CompetitiveIntelligenceState, create_initial_state
from agents.deep_research.agent import DeepResearchAgent
from agents.synthesizer.agent import SynthesizerAgent
from backend.models.schemas import ResearchStatus

logger = logging.getLogger(__name__)

class CompetitiveIntelligenceWorkflow:
    """
    LangGraph workflow orchestrator for the competitive intelligence system.
    Manages the flow between Deep Research and Synthesizer agents.
    """

    def __init__(self):
        self.deep_research_agent = DeepResearchAgent()
        self.synthesizer_agent = SynthesizerAgent()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow with explicit control flow.
        """
        # Create workflow graph
        workflow = StateGraph(CompetitiveIntelligenceState)

        # Add nodes (agents)
        workflow.add_node("deep_research", self._deep_research_node)
        workflow.add_node("validate_research", self._validate_research_node)
        workflow.add_node("synthesizer", self._synthesizer_node)
        workflow.add_node("finalize", self._finalize_node)

        # Define the workflow edges (explicit control flow)
        workflow.set_entry_point("deep_research")
        workflow.add_edge("deep_research", "validate_research")
        workflow.add_conditional_edges(
            "validate_research",
            self._should_proceed_to_synthesis,
            {
                "proceed": "synthesizer",
                "retry": "deep_research",
                "fail": "finalize"
            }
        )
        workflow.add_edge("synthesizer", "finalize")
        workflow.add_edge("finalize", END)

        # Add memory for state persistence
        memory = MemorySaver()
        workflow = workflow.compile(checkpointer=memory)

        return workflow

    async def _deep_research_node(self, state: CompetitiveIntelligenceState) -> CompetitiveIntelligenceState:
        """
        Execute the deep research agent.
        """
        logger.info(f"Executing deep research node for session {state['session_id']}")

        try:
            updated_state = await self.deep_research_agent.execute(state)
            return updated_state
        except Exception as e:
            logger.error(f"Deep research node failed: {str(e)}")
            state["error_messages"].append(f"Deep research failed: {str(e)}")
            state["workflow_status"] = ResearchStatus.FAILED
            return state

    async def _validate_research_node(self, state: CompetitiveIntelligenceState) -> CompetitiveIntelligenceState:
        """
        Validate the research results before proceeding to synthesis.
        """
        logger.info(f"Validating research for session {state['session_id']}")

        try:
            research_data = state["research_data"]
            target_competitors = state["target_competitors"]

            logger.info(f"Validating {len(target_competitors)} target competitors with {len(research_data)} research results")

            # Validation checks
            if not research_data:
                state["error_messages"].append("No research data found")
                state["validation_result"] = "fail"
                return state

            # Check minimum data quality
            valid_competitors = 0
            total_sources = 0

            for data in research_data:
                if data.confidence_score >= 0.5:  # Minimum confidence threshold
                    valid_competitors += 1
                    total_sources += len(data.sources)

            # Calculate thresholds
            required_70_percent = len(target_competitors) * 0.7
            required_50_percent = len(target_competitors) * 0.5

            # Determine validation result
            # Special case: if only 1 competitor selected and we got 1 valid result, proceed
            if len(target_competitors) == 1 and valid_competitors >= 1:
                state["validation_result"] = "proceed"
                logger.info(f"✅ Validation PASSED (single competitor): {valid_competitors} valid competitors, {total_sources} total sources")
            elif valid_competitors >= required_70_percent:  # 70% success rate
                state["validation_result"] = "proceed"
                logger.info(f"✅ Validation PASSED: {valid_competitors} valid competitors, {total_sources} total sources")
            elif valid_competitors >= required_50_percent:  # 50% - retry
                state["validation_result"] = "retry"
                logger.warning(f"⚠️ Validation MARGINAL: {valid_competitors} valid competitors - considering retry")
            else:
                state["validation_result"] = "fail"
                logger.error(f"❌ Validation FAILED: only {valid_competitors} valid competitors out of {len(target_competitors)} required")

            state["messages"].append({
                "role": "assistant",
                "content": f"Research validation: {valid_competitors} valid competitors with {total_sources} sources"
            })

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            state["error_messages"].append(f"Validation error: {str(e)}")
            state["validation_result"] = "fail"

        return state

    async def _synthesizer_node(self, state: CompetitiveIntelligenceState) -> CompetitiveIntelligenceState:
        """
        Execute the synthesizer agent.
        """
        logger.info(f"Executing synthesizer for session {state['session_id']}")

        try:
            updated_state = await self.synthesizer_agent.execute(state)
            logger.info(f"Synthesis completed for session {state['session_id']}")
            return updated_state
        except Exception as e:
            logger.error(f"Synthesis failed for session {state['session_id']}: {str(e)}")
            state["error_messages"].append(f"Synthesis failed: {str(e)}")
            state["workflow_status"] = ResearchStatus.FAILED
            return state

    async def _finalize_node(self, state: CompetitiveIntelligenceState) -> CompetitiveIntelligenceState:
        """
        Finalize the workflow and clean up.
        """
        logger.info(f"Finalizing workflow for session {state['session_id']}")

        try:
            # Update final status if not already set
            if state["workflow_status"] == ResearchStatus.IN_PROGRESS or state["workflow_status"] == ResearchStatus.PENDING:
                if state["executive_report"]:
                    state["workflow_status"] = ResearchStatus.COMPLETED
                else:
                    state["workflow_status"] = ResearchStatus.FAILED

            # Add final message
            if state["workflow_status"] == ResearchStatus.COMPLETED:
                state["messages"].append({
                    "role": "assistant",
                    "content": "Competitive intelligence workflow completed successfully"
                })
            else:
                state["messages"].append({
                    "role": "assistant",
                    "content": f"Workflow completed with status: {state['workflow_status']}"
                })

            logger.info(f"Workflow finalized with status: {state['workflow_status']}")

        except Exception as e:
            logger.error(f"Finalization failed: {str(e)}")
            state["error_messages"].append(f"Finalization error: {str(e)}")

        return state

    def _should_proceed_to_synthesis(self, state: CompetitiveIntelligenceState) -> str:
        """
        Conditional logic to determine next step after validation.
        """
        validation_result = state.get("validation_result", "fail")
        logger.info(f"Validation decision: {validation_result}")

        if validation_result == "proceed":
            logger.info("Proceeding to synthesizer")
            return "proceed"
        elif validation_result == "retry":
            # Check if we've already retried
            retry_count = state.get("retry_count", 0)
            if retry_count < 1:  # Allow one retry
                state["retry_count"] = retry_count + 1
                logger.info(f"Retrying research (attempt {retry_count + 1})")
                return "retry"
            else:
                logger.warning("Maximum retries reached, proceeding with available data")
                return "proceed"
        else:
            logger.warning(f"Validation failed, going to finalize: {validation_result}")
            return "fail"

    async def execute_workflow(
        self,
        session_id: str,
        target_competitors: list,
        research_focus: str = "AI narrative and strategic initiatives",
        max_age_days: int = 60,
        min_sources_per_competitor: int = 3
    ) -> CompetitiveIntelligenceState:
        """
        Execute the complete competitive intelligence workflow.
        """
        logger.info(f"Starting workflow execution for session {session_id}")

        try:
            # Create initial state
            initial_state = create_initial_state(
                session_id=session_id,
                target_competitors=target_competitors,
                research_focus=research_focus,
                max_age_days=max_age_days,
                min_sources_per_competitor=min_sources_per_competitor
            )

            # Execute workflow
            config = {"configurable": {"thread_id": session_id}}
            final_state = await self.workflow.ainvoke(initial_state, config)

            logger.info(f"Workflow completed for session {session_id} with status: {final_state['workflow_status']}")
            return final_state

        except Exception as e:
            logger.error(f"Workflow execution failed for session {session_id}: {str(e)}")
            # Return error state
            error_state = create_initial_state(session_id, target_competitors)
            error_state["workflow_status"] = ResearchStatus.FAILED
            error_state["error_messages"] = [f"Workflow execution failed: {str(e)}"]
            return error_state

    async def get_workflow_state(self, session_id: str) -> CompetitiveIntelligenceState:
        """
        Get the current state of a workflow session.
        """
        try:
            config = {"configurable": {"thread_id": session_id}}
            state = await self.workflow.aget_state(config)
            return state.values if state else None
        except Exception as e:
            logger.error(f"Failed to get workflow state for session {session_id}: {str(e)}")
            return None

# Global workflow instance
competitive_intelligence_workflow = CompetitiveIntelligenceWorkflow()