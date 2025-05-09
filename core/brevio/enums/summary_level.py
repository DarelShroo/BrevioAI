from enum import Enum


class SummaryLevel(Enum):
    VERY_CONCISE = "very_concise"
    CONCISE = "concise"
    MODERATE = "moderate"
    DETAILED = "detailed"
    VERY_DETAILED = "very_detailed"


WORD_LIMITS_BY_SUMMARY_LEVEL = {
    SummaryLevel.VERY_CONCISE: "100",
    SummaryLevel.CONCISE: "200",
    SummaryLevel.MODERATE: "300",
    SummaryLevel.DETAILED: "400",
    SummaryLevel.VERY_DETAILED: "500",
}
