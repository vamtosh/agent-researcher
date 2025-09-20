import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any
from openai import AsyncOpenAI
from backend.models.schemas import (
    ResearchData,
    ExecutiveReport,
    ExecutiveInsight,
    ResearchStatus
)
from agents.state import CompetitiveIntelligenceState
from config.settings import settings

logger = logging.getLogger(__name__)

class SynthesizerAgent:
    """
    Agent responsible for synthesizing research data into executive-ready insights.
    Transforms raw competitive intelligence into business-focused recommendations.
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.synthesis_model

    async def execute(self, state: CompetitiveIntelligenceState) -> CompetitiveIntelligenceState:
        """
        Execute the synthesis process to generate executive report.
        """
        logger.info(f"Starting synthesis for session {state['session_id']}")

        # Update agent state to in_progress
        state["agents_state"]["synthesizer"].status = ResearchStatus.IN_PROGRESS
        state["agents_state"]["synthesizer"].current_task = "Analyzing research data"
        state["agents_state"]["synthesizer"].progress_percentage = 0
        state["agents_state"]["synthesizer"].last_updated = datetime.now()
        state["updated_at"] = datetime.now()

        try:
            research_data = state["research_data"]
            if not research_data:
                raise ValueError("No research data available for synthesis")

            # Step 1: Generate executive summary
            state["agents_state"]["synthesizer"].current_task = "Generating executive summary"
            state["agents_state"]["synthesizer"].progress_percentage = 20

            executive_summary = await self._generate_executive_summary(research_data)

            # Step 2: Extract key insights
            state["agents_state"]["synthesizer"].current_task = "Extracting key insights"
            state["agents_state"]["synthesizer"].progress_percentage = 40

            key_insights = await self._extract_key_insights(research_data)

            # Step 3: Identify market opportunities
            state["agents_state"]["synthesizer"].current_task = "Identifying market opportunities"
            state["agents_state"]["synthesizer"].progress_percentage = 60

            market_opportunities = await self._identify_market_opportunities(research_data)

            # Step 4: Generate strategic recommendations
            state["agents_state"]["synthesizer"].current_task = "Generating strategic recommendations"
            state["agents_state"]["synthesizer"].progress_percentage = 80

            strategic_recommendations = await self._generate_strategic_recommendations(research_data)

            # Step 5: Compile final report
            state["agents_state"]["synthesizer"].current_task = "Compiling final report"
            state["agents_state"]["synthesizer"].progress_percentage = 90

            executive_report = ExecutiveReport(
                report_id=str(uuid.uuid4()),
                generation_timestamp=datetime.now(),
                executive_summary=executive_summary,
                key_insights=key_insights,
                competitor_analysis=research_data,
                market_opportunities=market_opportunities,
                strategic_recommendations=strategic_recommendations,
                data_sources_count=sum(len(rd.sources) for rd in research_data),
                research_timeframe=f"Last {settings.max_research_age_days} days"
            )

            # Update state with results
            state["executive_report"] = executive_report
            state["agents_state"]["synthesizer"].status = ResearchStatus.COMPLETED
            state["agents_state"]["synthesizer"].progress_percentage = 100
            state["agents_state"]["synthesizer"].current_task = "Synthesis completed"
            state["workflow_status"] = ResearchStatus.COMPLETED
            state["updated_at"] = datetime.now()

            logger.info(f"Synthesis completed for session {state['session_id']}")
            state["messages"].append({
                "role": "assistant",
                "content": f"Executive report generated with {len(key_insights)} insights and {len(strategic_recommendations)} recommendations"
            })

        except Exception as e:
            logger.error(f"Synthesis failed: {str(e)}")
            state["agents_state"]["synthesizer"].status = ResearchStatus.FAILED
            state["agents_state"]["synthesizer"].error_message = str(e)
            state["error_messages"].append(f"Synthesizer agent failed: {str(e)}")
            state["workflow_status"] = ResearchStatus.FAILED
            state["updated_at"] = datetime.now()

        return state

    async def _generate_executive_summary(self, research_data: List[ResearchData]) -> str:
        """
        Generate a concise executive summary from research data.
        """
        try:
            # Prepare context for GPT
            context = self._prepare_research_context(research_data)

            prompt = f"""
            Based on the following competitive intelligence data about TCS competitors' AI strategies,
            generate a concise executive summary for TCS senior leadership.

            Research Data:
            {context}

            Guidelines:
            - Maximum 150 words
            - Focus on key competitive threats and opportunities
            - Business-impact oriented language
            - Actionable insights for TCS executives
            - No technical jargon

            Executive Summary:
            """

            # Use Responses API for GPT-5-mini with proper parameters
            response = await self.client.responses.create(
                model=self.model,
                input=prompt,
                reasoning={
                    "effort": "low"  # Fast response for executive summary
                },
                text={
                    "verbosity": "low"  # Concise executive summary
                }
            )

            return response.output_text.strip()

        except Exception as e:
            logger.error(f"Failed to generate executive summary: {str(e)}")
            return "Executive summary generation failed. Manual review required."

    async def _extract_key_insights(self, research_data: List[ResearchData]) -> List[ExecutiveInsight]:
        """
        Extract key insights categorized by type and priority.
        """
        try:
            context = self._prepare_research_context(research_data)

            prompt = f"""
            Analyze the following competitive intelligence data and extract key insights for TCS executives.

            Research Data:
            {context}

            Extract insights in these categories:
            1. Competitive Threats (immediate risks from competitor moves)
            2. Market Opportunities (gaps TCS can exploit)
            3. Strategic Trends (industry directions TCS should follow)
            4. Action Items (specific steps TCS should take)

            For each insight, provide:
            - Title (10 words max)
            - Description (50 words max)
            - Business Impact (30 words max)
            - Recommended Action (40 words max)
            - Priority (high/medium/low)
            - Timeline (immediate/short_term/long_term)

            Format as JSON array with objects containing: insight_type, title, description, business_impact, recommended_action, priority, timeline

            Insights:
            """

            # Use Responses API for GPT-5-mini with proper parameters
            response = await self.client.responses.create(
                model=self.model,
                input=prompt,
                reasoning={
                    "effort": "medium"  # Balanced effort for insights
                },
                text={
                    "verbosity": "medium"  # Detailed insights needed
                }
            )

            # Parse JSON response (simplified - production would need robust parsing)
            insights_text = response.output_text.strip()
            insights = self._parse_insights_response(insights_text)

            return insights

        except Exception as e:
            logger.error(f"Failed to extract insights: {str(e)}")
            return [self._create_default_insight()]

    async def _identify_market_opportunities(self, research_data: List[ResearchData]) -> List[str]:
        """
        Identify market opportunities based on competitor analysis.
        """
        try:
            context = self._prepare_research_context(research_data)

            prompt = f"""
            Based on the competitive intelligence data below, identify market opportunities for TCS.

            Research Data:
            {context}

            Focus on:
            - Underserved market segments
            - Technology gaps competitors haven't addressed
            - Geographic opportunities
            - Service delivery innovations
            - Partnership opportunities
            - Emerging AI use cases

            Provide 5-7 specific opportunities, each in 20-30 words.
            Format as a numbered list.

            Market Opportunities:
            """

            # Use Responses API for GPT-5-mini with proper parameters
            response = await self.client.responses.create(
                model=self.model,
                input=prompt,
                reasoning={
                    "effort": "medium"  # Balanced effort for opportunities
                },
                text={
                    "verbosity": "medium"  # Detailed opportunities needed
                }
            )

            opportunities_text = response.output_text.strip()
            opportunities = self._parse_list_response(opportunities_text)

            return opportunities

        except Exception as e:
            logger.error(f"Failed to identify opportunities: {str(e)}")
            return ["Market opportunity analysis failed - manual review required"]

    async def _generate_strategic_recommendations(self, research_data: List[ResearchData]) -> List[str]:
        """
        Generate strategic recommendations for TCS leadership.
        """
        try:
            context = self._prepare_research_context(research_data)

            prompt = f"""
            Based on the competitive intelligence analysis, provide strategic recommendations for TCS leadership.

            Research Data:
            {context}

            Focus on:
            - AI capability investments
            - Market positioning strategies
            - Partnership and acquisition targets
            - Service portfolio adjustments
            - Client engagement approaches
            - Competitive differentiation

            Provide 5-7 actionable recommendations with clear business rationale.
            Each recommendation should be 25-35 words.
            Format as a numbered list.

            Strategic Recommendations:
            """

            # Use Responses API for GPT-5-mini with proper parameters
            response = await self.client.responses.create(
                model=self.model,
                input=prompt,
                reasoning={
                    "effort": "medium"  # Balanced effort for recommendations
                },
                text={
                    "verbosity": "medium"  # Detailed recommendations needed
                }
            )

            recommendations_text = response.output_text.strip()
            recommendations = self._parse_list_response(recommendations_text)

            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            return ["Strategic recommendations generation failed - manual review required"]

    def _prepare_research_context(self, research_data: List[ResearchData]) -> str:
        """
        Prepare research data as context for GPT prompts.
        """
        context_parts = []

        for data in research_data:
            context_part = f"""
            Competitor: {data.competitor}
            AI Narrative: {data.ai_narrative[:500]}...
            Key Initiatives: {', '.join(data.key_initiatives[:3])}
            Market Position: {data.market_positioning[:200]}...
            Source Count: {len(data.sources)}
            Confidence: {data.confidence_score:.2f}
            """
            context_parts.append(context_part)

        return "\n".join(context_parts)

    def _parse_insights_response(self, response_text: str) -> List[ExecutiveInsight]:
        """
        Parse insights from GPT response (simplified JSON parsing).
        """
        try:
            # In production, use proper JSON parsing with error handling
            # For now, create sample insights
            insights = []

            # Extract insights based on common patterns
            lines = response_text.split('\n')
            current_insight = {}

            for line in lines:
                line = line.strip()
                if 'title' in line.lower() and ':' in line:
                    if current_insight:
                        insights.append(self._create_insight_from_dict(current_insight))
                        current_insight = {}
                    current_insight['title'] = line.split(':', 1)[1].strip().strip('"')
                elif 'description' in line.lower() and ':' in line:
                    current_insight['description'] = line.split(':', 1)[1].strip().strip('"')
                elif 'priority' in line.lower() and ':' in line:
                    current_insight['priority'] = line.split(':', 1)[1].strip().strip('"')

            if current_insight:
                insights.append(self._create_insight_from_dict(current_insight))

            return insights if insights else [self._create_default_insight()]

        except Exception as e:
            logger.error(f"Failed to parse insights: {str(e)}")
            return [self._create_default_insight()]

    def _create_insight_from_dict(self, insight_dict: Dict[str, str]) -> ExecutiveInsight:
        """
        Create ExecutiveInsight from parsed dictionary.
        """
        return ExecutiveInsight(
            insight_type=insight_dict.get('type', 'opportunity'),
            title=insight_dict.get('title', 'Strategic Insight')[:50],
            description=insight_dict.get('description', 'Analysis of competitive landscape')[:200],
            business_impact=insight_dict.get('business_impact', 'Potential market impact for TCS')[:150],
            recommended_action=insight_dict.get('recommended_action', 'Evaluate strategic response')[:200],
            priority=insight_dict.get('priority', 'medium'),
            timeline=insight_dict.get('timeline', 'short_term')
        )

    def _create_default_insight(self) -> ExecutiveInsight:
        """
        Create a default insight when parsing fails.
        """
        return ExecutiveInsight(
            insight_type="opportunity",
            title="Competitive Analysis Required",
            description="Manual review of competitive intelligence data needed",
            business_impact="Strategic positioning may be affected",
            recommended_action="Conduct detailed analysis of competitor AI strategies",
            priority="high",
            timeline="immediate"
        )

    def _parse_list_response(self, response_text: str) -> List[str]:
        """
        Parse numbered list responses from GPT.
        """
        try:
            lines = response_text.split('\n')
            items = []

            for line in lines:
                line = line.strip()
                # Look for numbered items
                if line and (line[0].isdigit() or line.startswith('-')):
                    # Remove numbering and clean up
                    clean_line = line
                    if '. ' in line:
                        clean_line = line.split('. ', 1)[1]
                    elif '- ' in line:
                        clean_line = line.split('- ', 1)[1]

                    if len(clean_line) > 10:  # Filter out very short items
                        items.append(clean_line.strip())

            return items if items else ["Analysis completed - detailed review recommended"]

        except Exception as e:
            logger.error(f"Failed to parse list response: {str(e)}")
            return ["Response parsing failed - manual review required"]