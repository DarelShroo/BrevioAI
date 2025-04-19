from enum import Enum

from core.brevio.constants.contents import Contents


class ContentType(Enum):
    """Enum for different content types"""

    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    PDF = "pdf"
    URL = "url"


class ContentCategory(Enum):
    """Enum for different content categories"""

    PROGRAMMING_CONTENT = Contents.PROGRAMMING_CONTENT
    SCIENTIFIC_CONTENT = Contents.SCIENTIFIC_CONTENT
    BUSINESS_CONTENT = Contents.BUSINESS_CONTENT
    EDUCATIONAL_CONTENT = Contents.EDUCATIONAL_CONTENT
    CULTURAL_CONTENT = Contents.CULTURAL_CONTENT
    DEPORTIVE_CONTENT = Contents.DEPORTIVE_CONTENT
    POLITICAL_CONTENT = Contents.POLITICAL_CONTENT
    LEGAL_CONTENT = Contents.LEGAL_CONTENT
    HEALTH_CONTENT = Contents.HEALTH_CONTENT
    ENTERTAINMENT_CONTENT = Contents.ENTERTAINMENT_CONTENT
