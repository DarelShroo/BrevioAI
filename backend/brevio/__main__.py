import sys
from .models.config_model import ConfigModel as Config
from .generate import Generate
from .constants.constants import Constants
from .enums.model import ModelType
from .enums.language import LanguageType
from .constants.type_messages import TypeMessages
from .services.yt_service import YTService
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def main(argv):
    try:
        url = argv[0] if len(argv) > 0 else ""
        language_str = argv[1] if len(argv) > 1 else LanguageType.SPANISH.name

        content = argv[2] if len(argv) > 2 else Constants.CONTENT
        model_str = argv[3] if len(argv) > 3 else ModelType.GPT_4O_MINI.name

        try:
            language = LanguageType[language_str.upper()]
        except KeyError:
            raise ValueError(f"{TypeMessages.ERROR_INVALID_INPUT} ({
                             TypeMessages.AVAILABLE_LANGUAGES} {[e.name for e in LanguageType]}")

        try:
            model = ModelType[model_str.upper()]
        except KeyError:
            raise ValueError(f"{TypeMessages.ERROR_INVALID_INPUT} ({
                             TypeMessages.AVAILABLE_MODELS} {[e.name for e in ModelType]})")

        config = Config(url=url, content=content,
                        model=model, language=language)
        generate = Generate(config)

        response_dict = generate.organize_audio_files_into_folders()
        return response_dict.to_dict()

    except ValueError as ve:
        print(f"{ve}")
        sys.exit(1)
    except Exception as e:
        print(f"{TypeMessages.ERROR_UNEXPECTED}: {e}")
        sys.exit(1)


def count_yt_videos(url: str):
    return YTService.count_videos_in_yt_playlist(url)


if __name__ == "__main__":
    main(sys.argv[1:])
