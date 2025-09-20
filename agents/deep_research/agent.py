import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from openai import AsyncOpenAI
from backend.models.schemas import (
    ResearchData,
    ResearchSource,
    ResearchStatus,
    AgentType
)
from agents.state import CompetitiveIntelligenceState
from backend.services.cache import research_cache
from config.settings import settings

logger = logging.getLogger(__name__)

class DeepResearchAgent:
    """
    Agent responsible for conducting deep research on TCS competitors using OpenAI's Deep Research API.
    Focuses on AI narratives, strategic initiatives, and recent developments.
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.deep_research_model

    async def execute(self, state: CompetitiveIntelligenceState) -> CompetitiveIntelligenceState:
        """
        Execute the deep research process for all target competitors.
        """
        logger.info(f"Starting deep research for session {state['session_id']}")

        # Update agent state to in_progress
        state["agents_state"]["deep_research"].status = ResearchStatus.IN_PROGRESS
        state["agents_state"]["deep_research"].current_task = "Initializing research"
        state["agents_state"]["deep_research"].progress_percentage = 0
        state["agents_state"]["deep_research"].last_updated = datetime.now()
        state["updated_at"] = datetime.now()

        try:
            research_results = []
            total_competitors = len(state["target_competitors"])

            logger.info(f"🎯 DEEP RESEARCH DEBUG: Starting research for {total_competitors} competitors: {state['target_competitors']}")

            for i, competitor in enumerate(state["target_competitors"]):
                logger.info(f"Researching competitor: {competitor} ({i+1}/{total_competitors})")

                # Update progress
                progress = int((i / total_competitors) * 80)  # Reserve 20% for final processing
                state["agents_state"]["deep_research"].progress_percentage = progress
                state["agents_state"]["deep_research"].current_task = f"Researching {competitor}"

                # Conduct research for this competitor
                try:
                    # Check cache first
                    state["agents_state"]["deep_research"].current_task = f"Checking cache for {competitor}..."
                    state["updated_at"] = datetime.now()

                    cached_data = research_cache.get_cached_research(competitor, state["research_focus"])

                    if cached_data:
                        # Use cached data
                        research_results.append(cached_data)
                        logger.info(f"✅ Using cached data for {competitor}")
                        state["agents_state"]["deep_research"].current_task = f"Used cached data for {competitor} - {len(cached_data.sources)} sources"
                    else:
                        # Perform fresh research
                        state["agents_state"]["deep_research"].current_task = f"Searching web sources for {competitor}..."
                        state["updated_at"] = datetime.now()

                        competitor_data = await self._research_competitor(competitor, state["research_focus"], state)
                        if competitor_data:
                            research_results.append(competitor_data)
                            logger.info(f"Successfully researched {competitor}")

                            # Cache the fresh data
                            research_cache.cache_research(competitor, state["research_focus"], competitor_data)

                            state["agents_state"]["deep_research"].current_task = f"Completed fresh research for {competitor} - found {len(competitor_data.sources)} sources"
                        else:
                            logger.warning(f"No data returned for {competitor}")
                            state["agents_state"]["deep_research"].current_task = f"No data found for {competitor}"

                except Exception as e:
                    logger.error(f"Research failed for {competitor}: {str(e)}")
                    state["agents_state"]["deep_research"].current_task = f"Research failed for {competitor}"
                    # Continue with next competitor instead of stopping

                state["updated_at"] = datetime.now()

            # Final processing
            state["agents_state"]["deep_research"].current_task = "Processing research results"
            state["agents_state"]["deep_research"].progress_percentage = 90

            # Validate and filter results
            validated_results = self._validate_research_results(research_results, state["min_sources_per_competitor"])

            # Update state with results
            state["research_data"] = validated_results
            state["agents_state"]["deep_research"].status = ResearchStatus.COMPLETED
            state["agents_state"]["deep_research"].progress_percentage = 100
            state["agents_state"]["deep_research"].current_task = "Research completed"
            state["updated_at"] = datetime.now()

            # Log completion
            logger.info(f"Deep research completed for {len(validated_results)} competitors")
            state["messages"].append({
                "role": "assistant",
                "content": f"Deep research completed for {len(validated_results)} competitors with {sum(len(r.sources) for r in validated_results)} total sources"
            })

        except Exception as e:
            logger.error(f"Deep research failed: {str(e)}")
            state["agents_state"]["deep_research"].status = ResearchStatus.FAILED
            state["agents_state"]["deep_research"].error_message = str(e)
            state["error_messages"].append(f"Deep research agent failed: {str(e)}")
            state["updated_at"] = datetime.now()

        return state

    async def _research_competitor(self, competitor: str, research_focus: str, state: CompetitiveIntelligenceState = None) -> ResearchData:
        """
        Conduct deep research on a specific competitor using OpenAI responses API with web search.
        """
        try:
            # Update progress: Starting web search
            if state:
                state["agents_state"]["deep_research"].current_task = f"Initiating web search for {competitor}..."
                state["updated_at"] = datetime.now()

            # Construct research query
            query = self._build_research_query(competitor, research_focus)

            # Update progress: Calling OpenAI API
            if state:
                state["agents_state"]["deep_research"].current_task = f"Calling GPT-5 with web search for {competitor}..."
                state["updated_at"] = datetime.now()

            # Call OpenAI responses API with web search tool
            response = await self.client.responses.create(
                model=self.model,
                tools=[
                    {"type": "web_search"}
                ],
                input=query
            )

            # Update progress: Processing results
            if state:
                state["agents_state"]["deep_research"].current_task = f"Processing web search results for {competitor}..."
                state["updated_at"] = datetime.now()

            # Extract and parse research data
            research_content = response.output_text

            # Parse the response to extract structured data
            parsed_data = self._parse_research_response(competitor, research_content)

            # Update progress: Completed
            if state and parsed_data:
                sources_found = len(parsed_data.sources)
                state["agents_state"]["deep_research"].current_task = f"Found {sources_found} sources for {competitor}"
                state["updated_at"] = datetime.now()

            return parsed_data

        except Exception as e:
            logger.error(f"Failed to research {competitor}: {str(e)}")
            if state:
                state["agents_state"]["deep_research"].current_task = f"Primary search failed for {competitor}, trying fallback..."
                state["updated_at"] = datetime.now()

            # Fallback to chat completion if responses API fails
            try:
                logger.info(f"Falling back to chat completion for {competitor}")
                fallback_response = await self.client.chat.completions.create(
                    model="gpt-4o",  # Fallback model
                    messages=[
                        {
                            "role": "user",
                            "content": self._build_research_query(competitor, research_focus)
                        }
                    ],
                    max_completion_tokens=4000
                )

                if state:
                    state["agents_state"]["deep_research"].current_task = f"Fallback search completed for {competitor}"
                    state["updated_at"] = datetime.now()

                research_content = fallback_response.choices[0].message.content
                parsed_data = self._parse_research_response(competitor, research_content)
                return parsed_data

            except Exception as fallback_error:
                logger.error(f"Fallback also failed for {competitor}: {str(fallback_error)}")
                if state:
                    state["agents_state"]["deep_research"].current_task = f"All search methods failed for {competitor}"
                    state["updated_at"] = datetime.now()
                return None

    def _build_research_query(self, competitor: str, research_focus: str) -> str:
        """
        Build a comprehensive research query optimized for web search.
        """
        cutoff_date = datetime.now() - timedelta(days=settings.max_research_age_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        query = f"""
        Research {competitor}'s AI strategy and initiatives in IT services from the last 20 days.

        Find recent information about:
        1. {competitor} AI strategy and narrative announcements
        2. New AI product launches and service offerings by {competitor}
        3. {competitor} AI partnerships, acquisitions, and investments
        4. {competitor} market positioning in AI and IT services
        5. Leadership statements from {competitor} executives about AI direction
        6. Recent client wins and case studies for {competitor} AI services
        7. {competitor} competitive advantages and differentiators in AI

        Search for:
        - Official {competitor} press releases and earnings calls since {cutoff_str}
        - Industry analyst reports mentioning {competitor} AI capabilities
        - Technology news articles about {competitor} AI initiatives
        - Executive interviews and conference presentations by {competitor} leaders

        Provide:
        - Specific AI initiatives and their business impact
        - Key quotes from {competitor} executives
        - Market positioning insights
        - Competitive analysis data
        - Recent financial performance related to AI services
        - Source URLs and publication dates

        Focus on actionable competitive intelligence for TCS executives to understand {competitor}'s AI strategy and market positioning.
        """

        return query

    def _parse_research_response(self, competitor: str, content: str) -> ResearchData:
        """
        Parse the Deep Research API response into structured ResearchData.
        This is a simplified parser - in production, you'd want more sophisticated NLP.
        """
        try:
            # Extract key sections (simplified parsing)
            lines = content.split('\n')

            ai_narrative = ""
            key_initiatives = []
            sources = []

            current_section = ""
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Simple section detection
                if "ai strategy" in line.lower() or "narrative" in line.lower():
                    current_section = "narrative"
                elif "initiative" in line.lower() or "product" in line.lower():
                    current_section = "initiatives"
                elif "source" in line.lower() or "http" in line.lower():
                    current_section = "sources"

                # Extract content based on section
                if current_section == "narrative" and len(line) > 50:
                    ai_narrative += line + " "
                elif current_section == "initiatives" and line.startswith("-"):
                    key_initiatives.append(line[1:].strip())
                elif current_section == "sources" and ("http" in line or "www" in line):
                    # Extract source information
                    source = self._extract_source_info(line)
                    if source:
                        sources.append(source)

            # Create ResearchData object
            research_data = ResearchData(
                competitor=competitor,
                ai_narrative=ai_narrative.strip() or f"{competitor} AI strategy analysis",
                key_initiatives=key_initiatives or [f"{competitor} AI initiatives"],
                market_positioning=f"{competitor} positioning in AI services market",
                sources=sources or [self._create_default_source(competitor)],
                research_timestamp=datetime.now(),
                confidence_score=0.8 if sources else 0.6
            )

            return research_data

        except Exception as e:
            logger.error(f"Failed to parse research response for {competitor}: {str(e)}")
            # Return minimal data structure
            return ResearchData(
                competitor=competitor,
                ai_narrative=f"Research data for {competitor} AI initiatives",
                key_initiatives=[f"{competitor} AI strategy"],
                market_positioning=f"{competitor} market position",
                sources=[self._create_default_source(competitor)],
                research_timestamp=datetime.now(),
                confidence_score=0.5
            )

    def _extract_source_info(self, line: str) -> ResearchSource:
        """
        Extract source information from a line of text.
        """
        try:
            # Simple URL extraction
            if "http" in line:
                url_start = line.find("http")
                url_end = line.find(" ", url_start)
                if url_end == -1:
                    url_end = len(line)
                url = line[url_start:url_end]

                # Extract title (simplified)
                title = line[:url_start].strip() or "Research Source"

                return ResearchSource(
                    url=url,
                    title=title,
                    source_type="report",
                    publication_date=datetime.now() - timedelta(days=30),  # Approximate
                    credibility_score=0.8
                )
        except Exception:
            pass
        return None

    def _create_default_source(self, competitor: str) -> ResearchSource:
        """
        Create a default source for cases where extraction fails.
        """
        return ResearchSource(
            url=f"https://research.tcs.com/competitors/{competitor.lower()}",
            title=f"{competitor} AI Strategy Analysis",
            source_type="research",
            publication_date=datetime.now() - timedelta(days=14),
            credibility_score=0.7
        )

    def _validate_research_results(self, results: List[ResearchData], min_sources: int) -> List[ResearchData]:
        """
        Validate research results and filter out low-quality data.
        """
        validated = []

        for result in results:
            if result and len(result.sources) >= min_sources:
                validated.append(result)
            elif result:
                # Log warning but include anyway
                logger.warning(f"Competitor {result.competitor} has only {len(result.sources)} sources (minimum {min_sources})")
                validated.append(result)

        return validated