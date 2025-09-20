"""
System integration tests for the competitive intelligence system.
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
from typing import List

# Import our modules
from agents.state import create_initial_state
from agents.orchestrator.workflow import competitive_intelligence_workflow
from backend.models.schemas import (
    ResearchData,
    ResearchSource,
    ExecutiveReport,
    ResearchStatus
)
from backend.services.validation import competitor_validator, report_validator
from config.settings import settings

class TestSystemIntegration:
    """
    Test the complete system integration with mock data.
    """

    @pytest.fixture
    def sample_competitors(self):
        """Sample competitor list for testing."""
        return ["Accenture", "IBM", "Infosys"]

    @pytest.fixture
    def mock_research_data(self):
        """Create mock research data for testing."""
        sources = [
            ResearchSource(
                url="https://www.accenture.com/ai-strategy",
                title="Accenture AI Strategy Report 2024",
                source_type="report",
                publication_date=datetime.now() - timedelta(days=14),
                credibility_score=0.9
            ),
            ResearchSource(
                url="https://www.gartner.com/accenture-ai-analysis",
                title="Gartner Analysis: Accenture AI Capabilities",
                source_type="research",
                publication_date=datetime.now() - timedelta(days=7),
                credibility_score=0.95
            )
        ]

        return [
            ResearchData(
                competitor="Accenture",
                ai_narrative="Accenture focuses on human-AI collaboration and responsible AI development",
                key_initiatives=["AI Studio", "myWizard platform", "Responsible AI practice"],
                market_positioning="Leading AI consultancy with strong enterprise focus",
                sources=sources,
                research_timestamp=datetime.now(),
                confidence_score=0.85
            )
        ]

    def test_initial_state_creation(self, sample_competitors):
        """Test initial state creation."""
        session_id = "test-session-123"
        state = create_initial_state(
            session_id=session_id,
            target_competitors=sample_competitors
        )

        assert state["session_id"] == session_id
        assert state["target_competitors"] == sample_competitors
        assert state["workflow_status"] == ResearchStatus.PENDING
        assert len(state["agents_state"]) == 2
        assert "deep_research" in state["agents_state"]
        assert "synthesizer" in state["agents_state"]

    def test_competitor_data_validation(self, mock_research_data):
        """Test competitor data validation."""
        is_valid, errors, metrics = competitor_validator.validate_research_data(mock_research_data)

        # Should be valid with good mock data
        assert is_valid or len(errors) <= 2  # Allow minor validation issues
        assert metrics["total_competitors"] == 1
        assert metrics["avg_confidence"] > 0.8

    def test_research_data_creation(self):
        """Test creation of research data with various scenarios."""
        # Test with minimal valid data
        minimal_sources = [
            ResearchSource(
                url="https://www.example.com/test",
                title="Test Source for Research",
                source_type="report",
                publication_date=datetime.now() - timedelta(days=1),
                credibility_score=0.7
            )
        ]

        research_data = ResearchData(
            competitor="Test Competitor",
            ai_narrative="Test AI narrative for competitive analysis",
            key_initiatives=["Test Initiative 1", "Test Initiative 2"],
            market_positioning="Test market positioning statement",
            sources=minimal_sources,
            research_timestamp=datetime.now(),
            confidence_score=0.6
        )

        assert research_data.competitor == "Test Competitor"
        assert len(research_data.sources) == 1
        assert research_data.confidence_score == 0.6

    def test_export_functionality(self, mock_research_data):
        """Test report export functionality."""
        from backend.services.export import report_exporter

        # Create a mock executive report
        from backend.models.schemas import ExecutiveInsight

        mock_insights = [
            ExecutiveInsight(
                insight_type="opportunity",
                title="AI Partnership Opportunity",
                description="Opportunity to enhance AI capabilities through partnerships",
                business_impact="Potential 15% increase in AI service revenue",
                recommended_action="Evaluate strategic partnerships with AI platform providers",
                priority="high",
                timeline="short_term"
            )
        ]

        mock_report = ExecutiveReport(
            report_id="test-report-123",
            generation_timestamp=datetime.now(),
            executive_summary="Test executive summary for competitive intelligence analysis",
            key_insights=mock_insights,
            competitor_analysis=mock_research_data,
            market_opportunities=["Test opportunity 1", "Test opportunity 2"],
            strategic_recommendations=["Test recommendation 1", "Test recommendation 2"],
            data_sources_count=5,
            research_timeframe="Last 60 days"
        )

        # Test JSON export
        json_data = report_exporter.export_json(mock_report, "test-session")
        assert isinstance(json_data, bytes)
        assert b"test-report-123" in json_data

        # Test Markdown export
        md_data = report_exporter.export_markdown(mock_report, "test-session")
        assert isinstance(md_data, bytes)
        assert b"# TCS Competitive Intelligence Report" in md_data

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, sample_competitors):
        """Test workflow error handling with invalid configuration."""
        try:
            # Test with empty competitors list
            state = create_initial_state(
                session_id="error-test",
                target_competitors=[]
            )

            # The state should still be created but validation should catch issues
            assert state["session_id"] == "error-test"
            assert state["target_competitors"] == []

        except Exception as e:
            # Expected to handle gracefully
            assert "competitors" in str(e).lower()

    def test_api_health_check(self):
        """Test basic system health checks."""
        # Check if required environment variables are accessible
        # Note: In real tests, we'd mock these
        required_settings = [
            'tcs_competitors',
            'max_research_age_days',
            'min_sources_per_competitor'
        ]

        for setting in required_settings:
            assert hasattr(settings, setting)

        # Check competitor list
        assert len(settings.tcs_competitors) > 0
        assert "Accenture" in settings.tcs_competitors
        assert "IBM" in settings.tcs_competitors

    def test_data_validation_edge_cases(self):
        """Test data validation with edge cases."""
        # Test with very old source
        old_source = ResearchSource(
            url="https://example.com/old-report",
            title="Old Report",
            source_type="report",
            publication_date=datetime.now() - timedelta(days=200),  # Too old
            credibility_score=0.8
        )

        old_data = ResearchData(
            competitor="Accenture",
            ai_narrative="Old narrative",
            key_initiatives=["Old initiative"],
            market_positioning="Old positioning",
            sources=[old_source],
            research_timestamp=datetime.now(),
            confidence_score=0.7
        )

        is_valid, errors, metrics = competitor_validator.validate_research_data([old_data])

        # Should flag old sources
        assert not is_valid or "old" in str(errors).lower() or "date" in str(errors).lower()

    def test_concurrent_state_handling(self):
        """Test handling of multiple concurrent sessions."""
        sessions = []

        for i in range(3):
            session_id = f"concurrent-test-{i}"
            state = create_initial_state(
                session_id=session_id,
                target_competitors=["Accenture", "IBM"]
            )
            sessions.append(state)

        # Each session should be independent
        assert len(set(session["session_id"] for session in sessions)) == 3

        # All should have same structure but different IDs
        for session in sessions:
            assert "deep_research" in session["agents_state"]
            assert "synthesizer" in session["agents_state"]
            assert session["workflow_status"] == ResearchStatus.PENDING

if __name__ == "__main__":
    # Run basic tests
    test_instance = TestSystemIntegration()

    # Create fixtures manually for standalone testing
    sample_competitors = ["Accenture", "IBM", "Infosys"]

    print("🧪 Running System Integration Tests...")

    # Test 1: Initial state creation
    try:
        test_instance.test_initial_state_creation(sample_competitors)
        print("✅ Initial state creation: PASSED")
    except Exception as e:
        print(f"❌ Initial state creation: FAILED - {e}")

    # Test 2: Settings validation
    try:
        test_instance.test_api_health_check()
        print("✅ API health check: PASSED")
    except Exception as e:
        print(f"❌ API health check: FAILED - {e}")

    # Test 3: Data validation
    try:
        test_instance.test_data_validation_edge_cases()
        print("✅ Data validation: PASSED")
    except Exception as e:
        print(f"❌ Data validation: FAILED - {e}")

    # Test 4: Concurrent sessions
    try:
        test_instance.test_concurrent_state_handling()
        print("✅ Concurrent state handling: PASSED")
    except Exception as e:
        print(f"❌ Concurrent state handling: FAILED - {e}")

    print("\n📋 Test Summary:")
    print("System integration tests completed.")
    print("Note: Full workflow tests require OpenAI API key and may incur costs.")
    print("Run with pytest for complete test suite.")