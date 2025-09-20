"""
Export services for executive reports and research data.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import tempfile
import zipfile
from io import BytesIO

from backend.models.schemas import ExecutiveReport, ResearchData

logger = logging.getLogger(__name__)

class ReportExporter:
    """
    Service for exporting executive reports in various formats.
    """

    def __init__(self):
        self.export_dir = Path("data/exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_json(self, report: ExecutiveReport, session_id: str) -> bytes:
        """
        Export report as JSON.
        """
        try:
            # Convert report to dict for JSON serialization
            report_dict = self._report_to_dict(report)

            # Add metadata
            export_data = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    "format": "json",
                    "version": "1.0"
                },
                "report": report_dict
            }

            # Convert to JSON bytes
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
            return json_str.encode('utf-8')

        except Exception as e:
            logger.error(f"JSON export failed: {str(e)}")
            raise

    def export_csv(self, report: ExecutiveReport, session_id: str) -> bytes:
        """
        Export report data as CSV (insights and competitor analysis).
        """
        try:
            import csv
            from io import StringIO

            output = StringIO()

            # Export insights as CSV
            output.write("=== KEY INSIGHTS ===\n")
            insights_writer = csv.writer(output)
            insights_writer.writerow([
                "Type", "Title", "Description", "Business Impact",
                "Recommended Action", "Priority", "Timeline"
            ])

            for insight in report.key_insights:
                insights_writer.writerow([
                    insight.insight_type,
                    insight.title,
                    insight.description,
                    insight.business_impact,
                    insight.recommended_action,
                    insight.priority,
                    insight.timeline
                ])

            output.write("\n=== COMPETITOR ANALYSIS ===\n")
            competitor_writer = csv.writer(output)
            competitor_writer.writerow([
                "Competitor", "AI Narrative", "Key Initiatives",
                "Market Positioning", "Confidence Score", "Sources Count"
            ])

            for comp_data in report.competitor_analysis:
                competitor_writer.writerow([
                    comp_data.competitor,
                    comp_data.ai_narrative[:200] + "..." if len(comp_data.ai_narrative) > 200 else comp_data.ai_narrative,
                    "; ".join(comp_data.key_initiatives[:3]),
                    comp_data.market_positioning[:150] + "..." if len(comp_data.market_positioning) > 150 else comp_data.market_positioning,
                    comp_data.confidence_score,
                    len(comp_data.sources)
                ])

            return output.getvalue().encode('utf-8')

        except Exception as e:
            logger.error(f"CSV export failed: {str(e)}")
            raise

    def export_markdown(self, report: ExecutiveReport, session_id: str) -> bytes:
        """
        Export report as Markdown for easy reading and sharing.
        """
        try:
            md_content = self._generate_markdown_report(report, session_id)
            return md_content.encode('utf-8')

        except Exception as e:
            logger.error(f"Markdown export failed: {str(e)}")
            raise

    def export_complete_package(self, report: ExecutiveReport, session_id: str) -> bytes:
        """
        Export a complete package with multiple formats in a ZIP file.
        """
        try:
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add JSON export
                json_data = self.export_json(report, session_id)
                zip_file.writestr(f"tcs-competitive-intelligence-{session_id}.json", json_data)

                # Add CSV export
                csv_data = self.export_csv(report, session_id)
                zip_file.writestr(f"tcs-competitive-intelligence-{session_id}.csv", csv_data)

                # Add Markdown export
                md_data = self.export_markdown(report, session_id)
                zip_file.writestr(f"tcs-competitive-intelligence-{session_id}.md", md_data)

                # Add summary text file
                summary_data = self._generate_summary_text(report)
                zip_file.writestr(f"executive-summary-{session_id}.txt", summary_data.encode('utf-8'))

            zip_buffer.seek(0)
            return zip_buffer.getvalue()

        except Exception as e:
            logger.error(f"Complete package export failed: {str(e)}")
            raise

    def _report_to_dict(self, report: ExecutiveReport) -> Dict[str, Any]:
        """
        Convert ExecutiveReport to dictionary for JSON serialization.
        """
        try:
            return {
                "report_id": report.report_id,
                "generation_timestamp": report.generation_timestamp.isoformat(),
                "executive_summary": report.executive_summary,
                "key_insights": [
                    {
                        "insight_type": insight.insight_type,
                        "title": insight.title,
                        "description": insight.description,
                        "business_impact": insight.business_impact,
                        "recommended_action": insight.recommended_action,
                        "priority": insight.priority,
                        "timeline": insight.timeline
                    }
                    for insight in report.key_insights
                ],
                "competitor_analysis": [
                    {
                        "competitor": comp.competitor,
                        "ai_narrative": comp.ai_narrative,
                        "key_initiatives": comp.key_initiatives,
                        "investment_data": comp.investment_data,
                        "market_positioning": comp.market_positioning,
                        "sources": [
                            {
                                "url": source.url,
                                "title": source.title,
                                "source_type": source.source_type,
                                "publication_date": source.publication_date.isoformat(),
                                "author": source.author,
                                "credibility_score": source.credibility_score
                            }
                            for source in comp.sources
                        ],
                        "research_timestamp": comp.research_timestamp.isoformat(),
                        "confidence_score": comp.confidence_score
                    }
                    for comp in report.competitor_analysis
                ],
                "market_opportunities": report.market_opportunities,
                "strategic_recommendations": report.strategic_recommendations,
                "data_sources_count": report.data_sources_count,
                "research_timeframe": report.research_timeframe
            }

        except Exception as e:
            logger.error(f"Report to dict conversion failed: {str(e)}")
            raise

    def _generate_markdown_report(self, report: ExecutiveReport, session_id: str) -> str:
        """
        Generate a formatted Markdown report.
        """
        try:
            md_lines = [
                "# TCS Competitive Intelligence Report",
                f"**Session ID:** {session_id}",
                f"**Generated:** {report.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Data Sources:** {report.data_sources_count}",
                f"**Research Timeframe:** {report.research_timeframe}",
                "",
                "## Executive Summary",
                report.executive_summary,
                "",
                "## Key Insights",
                ""
            ]

            # Add insights
            for i, insight in enumerate(report.key_insights, 1):
                md_lines.extend([
                    f"### {i}. {insight.title}",
                    f"**Type:** {insight.insight_type} | **Priority:** {insight.priority} | **Timeline:** {insight.timeline}",
                    "",
                    f"**Description:** {insight.description}",
                    "",
                    f"**Business Impact:** {insight.business_impact}",
                    "",
                    f"**Recommended Action:** {insight.recommended_action}",
                    ""
                ])

            # Add market opportunities
            md_lines.extend([
                "## Market Opportunities",
                ""
            ])

            for i, opportunity in enumerate(report.market_opportunities, 1):
                md_lines.append(f"{i}. {opportunity}")

            md_lines.append("")

            # Add strategic recommendations
            md_lines.extend([
                "## Strategic Recommendations",
                ""
            ])

            for i, recommendation in enumerate(report.strategic_recommendations, 1):
                md_lines.append(f"{i}. {recommendation}")

            md_lines.append("")

            # Add competitor analysis
            md_lines.extend([
                "## Competitor Analysis",
                ""
            ])

            for comp_data in report.competitor_analysis:
                md_lines.extend([
                    f"### {comp_data.competitor}",
                    f"**Confidence Score:** {comp_data.confidence_score:.2f} | **Sources:** {len(comp_data.sources)}",
                    "",
                    "**AI Narrative:**",
                    comp_data.ai_narrative,
                    "",
                    "**Key Initiatives:**"
                ])

                for initiative in comp_data.key_initiatives:
                    md_lines.append(f"- {initiative}")

                md_lines.extend([
                    "",
                    "**Market Positioning:**",
                    comp_data.market_positioning,
                    "",
                    "**Sources:**"
                ])

                for source in comp_data.sources[:5]:  # Show top 5 sources
                    md_lines.append(f"- [{source.title}]({source.url}) ({source.source_type})")

                md_lines.append("")

            # Add footer
            md_lines.extend([
                "---",
                "*Generated by TCS Competitive Intelligence System*",
                f"*Report ID: {report.report_id}*"
            ])

            return "\n".join(md_lines)

        except Exception as e:
            logger.error(f"Markdown generation failed: {str(e)}")
            raise

    def _generate_summary_text(self, report: ExecutiveReport) -> str:
        """
        Generate a plain text summary for executives.
        """
        try:
            lines = [
                "TCS COMPETITIVE INTELLIGENCE - EXECUTIVE SUMMARY",
                "=" * 50,
                f"Generated: {report.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Data Sources: {report.data_sources_count}",
                f"Competitors Analyzed: {len(report.competitor_analysis)}",
                "",
                "EXECUTIVE SUMMARY:",
                report.executive_summary,
                "",
                "KEY INSIGHTS SUMMARY:",
            ]

            # Add high priority insights
            high_priority_insights = [insight for insight in report.key_insights if insight.priority == "high"]

            for insight in high_priority_insights[:3]:  # Top 3 high priority
                lines.extend([
                    f"• {insight.title}",
                    f"  Action: {insight.recommended_action}",
                    ""
                ])

            lines.extend([
                "TOP STRATEGIC RECOMMENDATIONS:"
            ])

            for i, recommendation in enumerate(report.strategic_recommendations[:5], 1):
                lines.append(f"{i}. {recommendation}")

            lines.extend([
                "",
                "COMPETITIVE POSITIONING:",
                f"TCS is analyzed against {len(report.competitor_analysis)} key competitors in AI services.",
                "Detailed analysis available in full report.",
                "",
                "=" * 50,
                "End of Executive Summary"
            ])

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Summary text generation failed: {str(e)}")
            raise


# Global exporter instance
report_exporter = ReportExporter()