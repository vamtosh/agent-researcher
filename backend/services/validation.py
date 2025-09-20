"""
Data validation services for competitive intelligence system.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from backend.models.schemas import (
    ResearchData,
    ResearchSource,
    ExecutiveReport,
    ExecutiveInsight
)
from config.settings import settings

logger = logging.getLogger(__name__)

class CompetitorDataValidator:
    """
    Validates research data for competitors to ensure quality and compliance.
    """

    def __init__(self):
        self.valid_competitors = set(settings.tcs_competitors)
        self.max_age_days = settings.max_research_age_days
        self.min_sources = settings.min_sources_per_competitor

    def validate_research_data(self, research_data: List[ResearchData]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate complete research data set.

        Returns:
            Tuple of (is_valid, error_messages, validation_metrics)
        """
        errors = []
        metrics = {
            "total_competitors": len(research_data),
            "valid_competitors": 0,
            "total_sources": 0,
            "valid_sources": 0,
            "avg_confidence": 0.0,
            "date_compliance": 0,
            "coverage_percentage": 0.0
        }

        try:
            valid_count = 0
            total_confidence = 0.0
            total_sources = 0
            valid_sources = 0
            date_compliant = 0

            for data in research_data:
                # Validate individual competitor data
                is_valid, competitor_errors = self._validate_competitor_data(data)

                if is_valid:
                    valid_count += 1

                # Collect metrics
                total_confidence += data.confidence_score
                competitor_sources = len(data.sources)
                total_sources += competitor_sources

                # Validate sources
                valid_competitor_sources = 0
                for source in data.sources:
                    source_valid, _ = self._validate_source(source)
                    if source_valid:
                        valid_competitor_sources += 1

                valid_sources += valid_competitor_sources

                # Check date compliance
                if self._check_date_compliance(data):
                    date_compliant += 1

                # Add any errors
                errors.extend(competitor_errors)

            # Calculate metrics
            metrics["valid_competitors"] = valid_count
            metrics["total_sources"] = total_sources
            metrics["valid_sources"] = valid_sources
            metrics["avg_confidence"] = total_confidence / len(research_data) if research_data else 0.0
            metrics["date_compliance"] = date_compliant
            metrics["coverage_percentage"] = (valid_count / len(settings.tcs_competitors)) * 100 if settings.tcs_competitors else 0

            # Determine overall validity
            is_valid = (
                valid_count >= len(research_data) * 0.7 and  # 70% of competitors valid
                metrics["avg_confidence"] >= 0.6 and  # Average confidence 60%+
                metrics["date_compliance"] >= len(research_data) * 0.8  # 80% date compliant
            )

            logger.info(f"Research validation completed: {valid_count}/{len(research_data)} competitors valid")

        except Exception as e:
            logger.error(f"Research validation failed: {str(e)}")
            errors.append(f"Validation process failed: {str(e)}")
            is_valid = False

        return is_valid, errors, metrics

    def _validate_competitor_data(self, data: ResearchData) -> Tuple[bool, List[str]]:
        """
        Validate data for a single competitor.
        """
        errors = []

        try:
            # Check competitor name
            if not data.competitor or data.competitor not in self.valid_competitors:
                errors.append(f"Invalid competitor: {data.competitor}")

            # Check AI narrative quality
            if not data.ai_narrative or len(data.ai_narrative.strip()) < 50:
                errors.append(f"AI narrative too short for {data.competitor}")

            # Check key initiatives
            if not data.key_initiatives or len(data.key_initiatives) == 0:
                errors.append(f"No key initiatives found for {data.competitor}")

            # Check minimum sources
            if len(data.sources) < self.min_sources:
                errors.append(f"Insufficient sources for {data.competitor}: {len(data.sources)} < {self.min_sources}")

            # Check confidence score
            if data.confidence_score < 0.5:
                errors.append(f"Low confidence score for {data.competitor}: {data.confidence_score}")

            # Validate sources
            valid_sources = 0
            for source in data.sources:
                is_valid, source_errors = self._validate_source(source)
                if is_valid:
                    valid_sources += 1
                else:
                    errors.extend([f"{data.competitor} - {error}" for error in source_errors])

            # Check source validity ratio
            if valid_sources < len(data.sources) * 0.7:  # 70% of sources should be valid
                errors.append(f"Too many invalid sources for {data.competitor}")

        except Exception as e:
            errors.append(f"Competitor data validation error for {data.competitor}: {str(e)}")

        is_valid = len(errors) == 0

        return is_valid, errors

    def _validate_source(self, source: ResearchSource) -> Tuple[bool, List[str]]:
        """
        Validate a research source.
        """
        errors = []

        try:
            # Validate URL
            if not self._is_valid_url(source.url):
                errors.append(f"Invalid URL: {source.url}")

            # Check title
            if not source.title or len(source.title.strip()) < 10:
                errors.append("Source title too short or missing")

            # Check publication date
            if not self._is_recent_date(source.publication_date):
                errors.append(f"Source too old: {source.publication_date}")

            # Check credibility score
            if source.credibility_score < 0.3:
                errors.append(f"Low credibility score: {source.credibility_score}")

            # Validate source type
            valid_types = ["report", "press_release", "earnings_call", "news", "research", "whitepaper"]
            if source.source_type not in valid_types:
                errors.append(f"Invalid source type: {source.source_type}")

        except Exception as e:
            errors.append(f"Source validation error: {str(e)}")

        is_valid = len(errors) == 0

        return is_valid, errors

    def _is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid and from a reputable domain.
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False

            # List of reputable domains
            reputable_domains = [
                'mckinsey.com', 'gartner.com', 'pwc.com', 'deloitte.com',
                'accenture.com', 'ibm.com', 'infosys.com', 'cognizant.com',
                'capgemini.com', 'wipro.com', 'hcltech.com', 'tcs.com',
                'reuters.com', 'bloomberg.com', 'techcrunch.com', 'zdnet.com',
                'computerworld.com', 'infoworld.com', 'cio.com'
            ]

            domain = parsed.netloc.lower()
            # Check if domain or any parent domain is in reputable list
            return any(rep_domain in domain for rep_domain in reputable_domains)

        except Exception:
            return False

    def _is_recent_date(self, date: datetime) -> bool:
        """
        Check if date is within the acceptable age limit.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
            return date >= cutoff_date
        except Exception:
            return False

    def _check_date_compliance(self, data: ResearchData) -> bool:
        """
        Check if research data meets date compliance requirements.
        """
        try:
            # Check research timestamp
            if not self._is_recent_date(data.research_timestamp):
                return False

            # Check source dates
            recent_sources = sum(1 for source in data.sources if self._is_recent_date(source.publication_date))
            return recent_sources >= len(data.sources) * 0.8  # 80% of sources should be recent

        except Exception:
            return False


class ExecutiveReportValidator:
    """
    Validates executive reports for quality and completeness.
    """

    def validate_executive_report(self, report: ExecutiveReport) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate an executive report.
        """
        errors = []
        metrics = {
            "summary_length": len(report.executive_summary),
            "insights_count": len(report.key_insights),
            "opportunities_count": len(report.market_opportunities),
            "recommendations_count": len(report.strategic_recommendations),
            "competitors_analyzed": len(report.competitor_analysis),
            "avg_insight_quality": 0.0
        }

        try:
            # Validate executive summary
            if not report.executive_summary or len(report.executive_summary.strip()) < 100:
                errors.append("Executive summary too short or missing")

            if len(report.executive_summary) > 1000:
                errors.append("Executive summary too long (should be concise)")

            # Validate insights
            if len(report.key_insights) < 3:
                errors.append("Insufficient key insights (minimum 3 required)")

            insight_quality_scores = []
            for insight in report.key_insights:
                quality_score = self._assess_insight_quality(insight)
                insight_quality_scores.append(quality_score)

                if quality_score < 0.6:
                    errors.append(f"Low quality insight: {insight.title}")

            metrics["avg_insight_quality"] = sum(insight_quality_scores) / len(insight_quality_scores) if insight_quality_scores else 0

            # Validate opportunities
            if len(report.market_opportunities) < 2:
                errors.append("Insufficient market opportunities identified")

            # Validate recommendations
            if len(report.strategic_recommendations) < 3:
                errors.append("Insufficient strategic recommendations")

            # Validate competitor analysis
            if len(report.competitor_analysis) < 3:
                errors.append("Insufficient competitor analysis")

            # Check data sources
            if report.data_sources_count < 5:
                errors.append(f"Insufficient data sources: {report.data_sources_count}")

        except Exception as e:
            errors.append(f"Report validation error: {str(e)}")

        is_valid = len(errors) == 0 and metrics["avg_insight_quality"] >= 0.7

        return is_valid, errors, metrics

    def _assess_insight_quality(self, insight: ExecutiveInsight) -> float:
        """
        Assess the quality of an individual insight.
        """
        try:
            quality_score = 0.0

            # Check title quality
            if insight.title and len(insight.title.strip()) >= 10:
                quality_score += 0.2

            # Check description quality
            if insight.description and len(insight.description.strip()) >= 30:
                quality_score += 0.2

            # Check business impact
            if insight.business_impact and len(insight.business_impact.strip()) >= 20:
                quality_score += 0.2

            # Check recommended action
            if insight.recommended_action and len(insight.recommended_action.strip()) >= 20:
                quality_score += 0.2

            # Check priority and timeline
            valid_priorities = ["high", "medium", "low"]
            valid_timelines = ["immediate", "short_term", "long_term"]

            if insight.priority in valid_priorities and insight.timeline in valid_timelines:
                quality_score += 0.2

            return quality_score

        except Exception:
            return 0.0


# Global validator instances
competitor_validator = CompetitorDataValidator()
report_validator = ExecutiveReportValidator()