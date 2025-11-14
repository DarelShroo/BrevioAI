from enum import Enum


class StyleType(Enum):
    # simple_summary
    SIMPLE_SUMMARY_DEFAULT = "default"

    # journalism
    JOURNALISM_CHRONICLE = "chronicle"
    JOURNALISM_NEWS_WIRE = "news_wire"
    JOURNALISM_ANALYSIS = "analysis"

    # marketing
    MARKETING_HIGHLIGHTS = "highlights"
    MARKETING_STORYTELLING = "storytelling"
    MARKETING_REPORT = "report"

    # health
    HEALTH_REPORT = "report"
    HEALTH_SUMMARY = "summary"
    HEALTH_CASE = "case"

    # technology
    TECHNOLOGY_CHANGELOG = "changelog"
    TECHNOLOGY_PROPOSAL = "proposal"
    TECHNOLOGY_DIAGRAM = "diagram"

    # education
    EDUCATION_GUIDE = "guide"
    EDUCATION_QUICK_REF = "quick_ref"
    EDUCATION_TIMELINE = "timeline"

    # architecture
    ARCHITECTURE_CHRONICLE = "chronicle"
    ARCHITECTURE_REPORT = "report"
    ARCHITECTURE_LIST = "list"

    # finance
    FINANCE_REPORT = "report"
    FINANCE_TABLE = "table"
    FINANCE_EXECUTIVE = "executive"

    # tourism
    TOURISM_CHRONICLE = "chronicle"
    TOURISM_REPORT = "report"
    TOURISM_LIST = "list"

    # requirements
    REQUIREMENTS__ELICITATION = "elicitation"
