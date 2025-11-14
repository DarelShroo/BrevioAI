from .arabic import ArabicPrompts
from .chinese import ChinesePrompts
from .english import EnglishPrompts
from .french import FrenchPrompts
from .german import GermanPrompts
from .hindi import HindiPrompts
from .italian import ItalianPrompts
from .japanese import JapanesePrompts
from .korean import KoreanPrompts
from .portuguese import PortuguesePrompts
from .russian import RussianPrompts
from .spanish import SpanishPrompts

__all__ = [
    "ARABIC",
    "ENGLISH",
    "CHINESE",
    "SPANISH",
    "FRENCH",
    "GERMAN",
    "HINDI",
    "ITALIAN",
    "JAPANESE",
    "KOREAN",
    "PORTUGUESE",
    "RUSSIAN",
]

ARABIC = ArabicPrompts()
ENGLISH = EnglishPrompts()
CHINESE = ChinesePrompts()
SPANISH = SpanishPrompts()
FRENCH = FrenchPrompts()
GERMAN = GermanPrompts()
HINDI = HindiPrompts()
ITALIAN = ItalianPrompts()
JAPANESE = JapanesePrompts()
KOREAN = KoreanPrompts()
PORTUGUESE = PortuguesePrompts()
RUSSIAN = RussianPrompts()
