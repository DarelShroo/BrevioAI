import logging
from enum import Enum
from math import ceil
from typing import Dict, List, Optional, Tuple

import numpy as np
from fastapi import HTTPException

from core.brevio.enums.language import LanguageType
from core.brevio.enums.summary_level import SummaryLevel
from core.shared.enums.model import ModelType
from core.shared.models.history_token_model import HistoryTokenModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)


class LanguageGroup(Enum):
    LATIN = "latin"
    CYRILLIC = "cyrillic"
    ARABIC_HEBREW = "arabic_hebrew"
    LOGOGRAPHIC = "logographic"
    INDIAN = "indian"
    SOUTHEAST_ASIAN = "southeast_asian"
    OTHER = "other"


LANGUAGE_TO_GROUP = {
    "es": LanguageGroup.LATIN,
    "en": LanguageGroup.LATIN,
    "fr": LanguageGroup.LATIN,
    "de": LanguageGroup.LATIN,
    "it": LanguageGroup.LATIN,
    "pt": LanguageGroup.LATIN,
    "nl": LanguageGroup.LATIN,
    "ca": LanguageGroup.LATIN,
    "ro": LanguageGroup.LATIN,
    "sk": LanguageGroup.LATIN,
    "ru": LanguageGroup.CYRILLIC,
    "bg": LanguageGroup.CYRILLIC,
    "uk": LanguageGroup.CYRILLIC,
    "ar": LanguageGroup.ARABIC_HEBREW,
    "he": LanguageGroup.ARABIC_HEBREW,
    "zh": LanguageGroup.LOGOGRAPHIC,
    "ja": LanguageGroup.LOGOGRAPHIC,
    "ko": LanguageGroup.LOGOGRAPHIC,
    "hi": LanguageGroup.INDIAN,
    "ta": LanguageGroup.INDIAN,
    "te": LanguageGroup.INDIAN,
    "th": LanguageGroup.SOUTHEAST_ASIAN,
}


class BillingEstimatorService:
    def __init__(self, model: ModelType = ModelType.GPT_4_1_NANO):
        self.model: ModelType = model
        self.input_factor: np.float64 = np.float64(0.0812)
        self.max_tokens_per_chunk: int = 8192
        self.context_token_limit: int = 100
        self.tokens_overheads: int = 100
        self._percent_chunk_overlap: float = 0.10
        self.min_tokens_for_chunking: int = 1000

        # Factores por grupo lingüístico
        self.group_char_to_token_factor: Dict[LanguageGroup, Dict[str, float]] = {
            LanguageGroup.LATIN: {"default": 0.5730, "min": 0.2484, "max": 0.7049},
            LanguageGroup.CYRILLIC: {"default": 0.5338, "min": 0.5313, "max": 0.5363},
            LanguageGroup.ARABIC_HEBREW: {
                "default": 0.6871,
                "min": 0.6487,
                "max": 0.7255,
            },
            LanguageGroup.LOGOGRAPHIC: {
                "default": 0.5181,
                "min": 0.5000,
                "max": 0.5400,
            },
            LanguageGroup.INDIAN: {"default": 0.4442, "min": 0.4000, "max": 0.5000},
            LanguageGroup.SOUTHEAST_ASIAN: {
                "default": 0.5522,
                "min": 0.5000,
                "max": 0.6000,
            },
            LanguageGroup.OTHER: {"default": 0.5522, "min": 0.5000, "max": 0.6000},
        }

        self.group_summary_factor: Dict[SummaryLevel, Dict[LanguageGroup, float]] = {
            SummaryLevel.VERY_CONCISE: {
                LanguageGroup.LATIN: 0.1193,
                LanguageGroup.CYRILLIC: 0.0732,
                LanguageGroup.ARABIC_HEBREW: 0.2338,
                LanguageGroup.LOGOGRAPHIC: 0.1197,
                LanguageGroup.INDIAN: 0.1206,
                LanguageGroup.SOUTHEAST_ASIAN: 0.1151,
                LanguageGroup.OTHER: 0.1151,
            },
            SummaryLevel.CONCISE: {
                LanguageGroup.LATIN: 0.23,
                LanguageGroup.CYRILLIC: 0.23,
                LanguageGroup.ARABIC_HEBREW: 0.26,
                LanguageGroup.LOGOGRAPHIC: 0.28,
                LanguageGroup.INDIAN: 0.25,
                LanguageGroup.SOUTHEAST_ASIAN: 0.25,
                LanguageGroup.OTHER: 0.25,
            },
            SummaryLevel.MODERATE: {
                LanguageGroup.LATIN: 0.26,
                LanguageGroup.CYRILLIC: 0.26,
                LanguageGroup.ARABIC_HEBREW: 0.29,
                LanguageGroup.LOGOGRAPHIC: 0.31,
                LanguageGroup.INDIAN: 0.28,
                LanguageGroup.SOUTHEAST_ASIAN: 0.28,
                LanguageGroup.OTHER: 0.28,
            },
            SummaryLevel.DETAILED: {
                LanguageGroup.LATIN: 0.29,
                LanguageGroup.CYRILLIC: 0.29,
                LanguageGroup.ARABIC_HEBREW: 0.32,
                LanguageGroup.LOGOGRAPHIC: 0.34,
                LanguageGroup.INDIAN: 0.31,
                LanguageGroup.SOUTHEAST_ASIAN: 0.31,
                LanguageGroup.OTHER: 0.31,
            },
            SummaryLevel.VERY_DETAILED: {
                LanguageGroup.LATIN: 0.39,
                LanguageGroup.CYRILLIC: 0.39,
                LanguageGroup.ARABIC_HEBREW: 0.42,
                LanguageGroup.LOGOGRAPHIC: 0.45,
                LanguageGroup.INDIAN: 0.41,
                LanguageGroup.SOUTHEAST_ASIAN: 0.41,
                LanguageGroup.OTHER: 0.41,
            },
        }

        self.postprocess_factor: Dict[SummaryLevel, np.float64] = {
            SummaryLevel.VERY_CONCISE: np.float64(0.4561),
            SummaryLevel.CONCISE: np.float64(0.05),
            SummaryLevel.MODERATE: np.float64(0.10),
            SummaryLevel.DETAILED: np.float64(0.15),
            SummaryLevel.VERY_DETAILED: np.float64(0.25),
        }

        self.group_translation_factor: Dict[
            Tuple[LanguageGroup, LanguageGroup], Dict[str, float]
        ] = {
            (LanguageGroup.LATIN, LanguageGroup.LATIN): {
                "default": 1.2376,
                "min": 0.9859,
                "max": 1.4952,
            },
            (LanguageGroup.LATIN, LanguageGroup.CYRILLIC): {
                "default": 0.6862,
                "min": 0.6739,
                "max": 0.6986,
            },
            (LanguageGroup.LATIN, LanguageGroup.ARABIC_HEBREW): {
                "default": 0.6609,
                "min": 0.6609,
                "max": 0.6609,
            },
            (LanguageGroup.LATIN, LanguageGroup.INDIAN): {
                "default": 0.8893,
                "min": 0.8893,
                "max": 0.8893,
            },
            (LanguageGroup.LATIN, LanguageGroup.LOGOGRAPHIC): {
                "default": 1.4,
                "min": 1.2,
                "max": 1.6,
            },
            (LanguageGroup.LATIN, LanguageGroup.SOUTHEAST_ASIAN): {
                "default": 1.1,
                "min": 1.0,
                "max": 1.2,
            },
            (LanguageGroup.LATIN, LanguageGroup.OTHER): {
                "default": 1.1,
                "min": 1.0,
                "max": 1.2,
            },
            (LanguageGroup.CYRILLIC, LanguageGroup.LATIN): {
                "default": 0.9984,
                "min": 0.9984,
                "max": 0.9984,
            },
            (LanguageGroup.CYRILLIC, LanguageGroup.CYRILLIC): {
                "default": 0.2734,
                "min": 0.2734,
                "max": 0.2734,
            },
            (LanguageGroup.CYRILLIC, LanguageGroup.INDIAN): {
                "default": 0.6301,
                "min": 0.6301,
                "max": 0.6301,
            },
            (LanguageGroup.CYRILLIC, LanguageGroup.ARABIC_HEBREW): {
                "default": 1.25,
                "min": 1.15,
                "max": 1.35,
            },
            (LanguageGroup.CYRILLIC, LanguageGroup.LOGOGRAPHIC): {
                "default": 1.45,
                "min": 1.25,
                "max": 1.65,
            },
            (LanguageGroup.CYRILLIC, LanguageGroup.SOUTHEAST_ASIAN): {
                "default": 1.15,
                "min": 1.05,
                "max": 1.25,
            },
            (LanguageGroup.CYRILLIC, LanguageGroup.OTHER): {
                "default": 1.15,
                "min": 1.05,
                "max": 1.25,
            },
            (LanguageGroup.ARABIC_HEBREW, LanguageGroup.LATIN): {
                "default": 0.9417,
                "min": 0.8808,
                "max": 1.0026,
            },
            (LanguageGroup.ARABIC_HEBREW, LanguageGroup.CYRILLIC): {
                "default": 1.25,
                "min": 1.15,
                "max": 1.35,
            },
            (LanguageGroup.ARABIC_HEBREW, LanguageGroup.ARABIC_HEBREW): {
                "default": 1.0,
                "min": 0.95,
                "max": 1.05,
            },
            (LanguageGroup.ARABIC_HEBREW, LanguageGroup.LOGOGRAPHIC): {
                "default": 1.5,
                "min": 1.3,
                "max": 1.7,
            },
            (LanguageGroup.ARABIC_HEBREW, LanguageGroup.INDIAN): {
                "default": 1.3,
                "min": 1.2,
                "max": 1.4,
            },
            (LanguageGroup.ARABIC_HEBREW, LanguageGroup.SOUTHEAST_ASIAN): {
                "default": 1.25,
                "min": 1.15,
                "max": 1.35,
            },
            (LanguageGroup.ARABIC_HEBREW, LanguageGroup.OTHER): {
                "default": 1.25,
                "min": 1.15,
                "max": 1.35,
            },
            (LanguageGroup.LOGOGRAPHIC, LanguageGroup.LATIN): {
                "default": 1.4,
                "min": 1.2,
                "max": 1.6,
            },
            (LanguageGroup.LOGOGRAPHIC, LanguageGroup.CYRILLIC): {
                "default": 1.45,
                "min": 1.25,
                "max": 1.65,
            },
            (LanguageGroup.LOGOGRAPHIC, LanguageGroup.ARABIC_HEBREW): {
                "default": 1.5,
                "min": 1.3,
                "max": 1.7,
            },
            (LanguageGroup.LOGOGRAPHIC, LanguageGroup.LOGOGRAPHIC): {
                "default": 1.0,
                "min": 0.95,
                "max": 1.05,
            },
            (LanguageGroup.LOGOGRAPHIC, LanguageGroup.INDIAN): {
                "default": 1.35,
                "min": 1.15,
                "max": 1.55,
            },
            (LanguageGroup.LOGOGRAPHIC, LanguageGroup.SOUTHEAST_ASIAN): {
                "default": 1.3,
                "min": 1.1,
                "max": 1.5,
            },
            (LanguageGroup.LOGOGRAPHIC, LanguageGroup.OTHER): {
                "default": 1.3,
                "min": 1.1,
                "max": 1.5,
            },
            (LanguageGroup.INDIAN, LanguageGroup.LATIN): {
                "default": 0.9859,
                "min": 0.9859,
                "max": 0.9859,
            },
            (LanguageGroup.INDIAN, LanguageGroup.CYRILLIC): {
                "default": 1.2,
                "min": 1.1,
                "max": 1.3,
            },
            (LanguageGroup.INDIAN, LanguageGroup.ARABIC_HEBREW): {
                "default": 1.3,
                "min": 1.2,
                "max": 1.4,
            },
            (LanguageGroup.INDIAN, LanguageGroup.LOGOGRAPHIC): {
                "default": 1.35,
                "min": 1.15,
                "max": 1.55,
            },
            (LanguageGroup.INDIAN, LanguageGroup.INDIAN): {
                "default": 1.0,
                "min": 0.95,
                "max": 1.05,
            },
            (LanguageGroup.INDIAN, LanguageGroup.SOUTHEAST_ASIAN): {
                "default": 1.15,
                "min": 1.05,
                "max": 1.25,
            },
            (LanguageGroup.INDIAN, LanguageGroup.OTHER): {
                "default": 1.15,
                "min": 1.05,
                "max": 1.25,
            },
            (LanguageGroup.SOUTHEAST_ASIAN, LanguageGroup.LATIN): {
                "default": 1.1,
                "min": 1.0,
                "max": 1.2,
            },
            (LanguageGroup.SOUTHEAST_ASIAN, LanguageGroup.CYRILLIC): {
                "default": 1.15,
                "min": 1.05,
                "max": 1.25,
            },
            (LanguageGroup.SOUTHEAST_ASIAN, LanguageGroup.ARABIC_HEBREW): {
                "default": 1.25,
                "min": 1.15,
                "max": 1.35,
            },
            (LanguageGroup.SOUTHEAST_ASIAN, LanguageGroup.LOGOGRAPHIC): {
                "default": 1.3,
                "min": 1.1,
                "max": 1.5,
            },
            (LanguageGroup.SOUTHEAST_ASIAN, LanguageGroup.INDIAN): {
                "default": 1.15,
                "min": 1.05,
                "max": 1.25,
            },
            (LanguageGroup.SOUTHEAST_ASIAN, LanguageGroup.SOUTHEAST_ASIAN): {
                "default": 1.0,
                "min": 0.95,
                "max": 1.05,
            },
            (LanguageGroup.SOUTHEAST_ASIAN, LanguageGroup.OTHER): {
                "default": 1.0,
                "min": 0.95,
                "max": 1.05,
            },
            (LanguageGroup.OTHER, LanguageGroup.LATIN): {
                "default": 1.1,
                "min": 1.0,
                "max": 1.2,
            },
            (LanguageGroup.OTHER, LanguageGroup.CYRILLIC): {
                "default": 1.15,
                "min": 1.05,
                "max": 1.25,
            },
            (LanguageGroup.OTHER, LanguageGroup.ARABIC_HEBREW): {
                "default": 1.25,
                "min": 1.15,
                "max": 1.35,
            },
            (LanguageGroup.OTHER, LanguageGroup.LOGOGRAPHIC): {
                "default": 1.3,
                "min": 1.1,
                "max": 1.5,
            },
            (LanguageGroup.OTHER, LanguageGroup.INDIAN): {
                "default": 1.15,
                "min": 1.05,
                "max": 1.25,
            },
            (LanguageGroup.OTHER, LanguageGroup.SOUTHEAST_ASIAN): {
                "default": 1.0,
                "min": 0.95,
                "max": 1.05,
            },
            (LanguageGroup.OTHER, LanguageGroup.OTHER): {
                "default": 1.0,
                "min": 0.95,
                "max": 1.05,
            },
        }

        self.language_specific_factors: Dict[str, Dict[str, np.float64]] = {
            "ru": {
                "char_to_token": np.float64(0.5338),
                "summary_very_concise": np.float64(0.0732),
            },
            "en": {
                "char_to_token": np.float64(0.5729),
                "summary_very_concise": np.float64(0.1193),
            },
            "ar": {
                "char_to_token": np.float64(0.6871),
                "summary_very_concise": np.float64(0.2338),
            },
            "hi": {
                "char_to_token": np.float64(0.4442),
                "summary_very_concise": np.float64(0.1206),
            },
            "es": {
                "char_to_token": np.float64(0.5730),
                "summary_very_concise": np.float64(0.1193),
            },
            "th": {
                "char_to_token": np.float64(0.5522),
                "summary_very_concise": np.float64(0.1151),
            },
        }

        self.language_pair_factors: Dict[Tuple[str, str], Dict[str, np.float64]] = {
            ("ar", "es"): {"translation": np.float64(0.9417)},
            ("en", "ru"): {"translation": np.float64(0.6862)},
            ("ru", "es"): {"translation": np.float64(0.9984)},
            ("en", "es"): {"translation": np.float64(1.2376)},
            ("hi", "es"): {"translation": np.float64(0.9859)},
            ("ru", "ru"): {"translation": np.float64(0.2734)},
            ("es", "ru"): {"translation": np.float64(0.9803)},
            ("en", "ar"): {"translation": np.float64(0.6609)},
            ("en", "hi"): {"translation": np.float64(0.8893)},
            ("ru", "hi"): {"translation": np.float64(0.6301)},
        }

        self.regression_diagnostics: Dict[
            str, Dict[str, Dict[str, float | Tuple[float, float]]]
        ] = {
            "char_to_token_factor": {
                "ru": {"mse": 26699552422.76, "ci": (0.5313, 0.5363)},
                "en": {"mse": 17870751395.42, "ci": (0.5728, 0.573)},
                "ar": {"mse": 66053984670.26, "ci": (0.6487, 0.7255)},
                "es": {"mse": 29737532058.99, "ci": (0.5269, 0.6192)},
                "hi": {"mse": 7989798467.99, "ci": (0.4342, 0.4542)},
                "th": {"mse": 15999486522.26, "ci": (0.5422, 0.5622)},
            },
            "input_factor": {"default": {"mse": 2925520089.34, "ci": (0.0806, 0.0817)}},
            "output_factor_map_summary": {
                "ru": {"mse": 2802843.67, "ci": (0.0693, 0.0771)},
                "ar": {"mse": 13245366.23, "ci": (0.2258, 0.2418)},
                "es": {"mse": 13368020.52, "ci": (0.1075, 0.131)},
                "th": {"mse": 465054.33, "ci": (0.097, 0.1331)},
                "hi": {"mse": 106135968.29, "ci": (0.0623, 0.1789)},
                "en": {"mse": 0.0, "ci": (0.0, 0.0)},
            },
            "output_factor_map_postprocess": {
                "default": {"mse": 222086.45, "ci": (0.4443, 0.4679)}
            },
            "translation_adjustment_factors": {
                "ar->es": {"mse": 183132572.85, "ci": (0.8808, 1.0026)},
                "en->ru": {"mse": 32415285.55, "ci": (0.6739, 0.6986)},
                "en->es": {"mse": 0.0, "ci": (0.0, 0.0)},
                "ru->ru": {"mse": 0.0, "ci": (0.0, 0.0)},
            },
        }

    def get_char_to_token_factor(self, language: str) -> float:
        """Obtiene el factor de conversión de caracteres a tokens para un idioma."""
        if language in self.language_specific_factors:
            return float(
                self.language_specific_factors[language].get("char_to_token", 0.5)
            )
        group = LANGUAGE_TO_GROUP.get(language, LanguageGroup.OTHER)
        return self.group_char_to_token_factor[group]["default"]

    def get_summary_factor(
        self, language: LanguageType, summary_level: SummaryLevel
    ) -> float:
        """Obtiene el factor de resumen para un idioma y nivel de resumen."""
        if (
            language in self.language_specific_factors
            and summary_level == SummaryLevel.VERY_CONCISE
        ):
            return float(
                self.language_specific_factors[language.value].get(
                    "summary_very_concise", 0.17
                )
            )
        group = LANGUAGE_TO_GROUP.get(language.value, LanguageGroup.OTHER)
        return self.group_summary_factor[summary_level].get(
            group, self.group_summary_factor[summary_level][LanguageGroup.OTHER]
        )

    def get_translation_factor(
        self, lang_in: LanguageType, lang_out: LanguageType
    ) -> float:
        """Obtiene el factor de ajuste para traducción entre dos idiomas."""
        pair = (lang_in.value, lang_out.value)
        if pair in self.language_pair_factors:
            return float(self.language_pair_factors[pair].get("translation", 1.0))
        group_in = LANGUAGE_TO_GROUP.get(lang_in.value, LanguageGroup.OTHER)
        group_out = LANGUAGE_TO_GROUP.get(lang_out.value, LanguageGroup.OTHER)
        return self.group_translation_factor.get(
            (group_in, group_out), {"default": 1.0}
        )["default"]

    def summary_tokens_predict(
        self,
        file_tokens: int,
        language_output: LanguageType,
        language_input: Optional[LanguageType] = LanguageType.ENGLISH,
        summary_level: SummaryLevel = SummaryLevel.VERY_CONCISE,
        history: Optional[HistoryTokenModel] = None,
    ) -> Tuple[int, int, int, int]:
        """Predice los tokens de entrada, salida de resumen y salida de posprocesamiento."""
        try:
            logger.debug(f"file_tokens: {file_tokens})")

            summary_input_tokens = ceil(file_tokens * self.input_factor)
            if file_tokens > self.min_tokens_for_chunking:
                chunk_size = self.max_tokens_per_chunk - ceil(
                    self.max_tokens_per_chunk * self._percent_chunk_overlap
                )
                num_chunks = (
                    ceil(
                        (file_tokens - chunk_size)
                        / (chunk_size * (1 - self._percent_chunk_overlap))
                    )
                    + 1
                )
                summary_input_tokens = ceil(
                    num_chunks * self.max_tokens_per_chunk * self.input_factor
                )
            summary_input_tokens += self.context_token_limit + self.tokens_overheads
            logger.debug(f"summary_input_tokens: {summary_input_tokens}")

            # Calcular tokens de salida para resumen
            if language_input is not None:
                summary_factor = self.get_summary_factor(language_input, summary_level)
            summary_output_tokens = ceil(summary_input_tokens * summary_factor)
            logger.debug(
                f"summary_output_tokens: {summary_output_tokens} (summary_factor={summary_factor})"
            )

            # Ajustar por traducción si se especifica idioma de salida
            translation_factor = 1.0
            if (
                language_output
                and language_output != language_input
                and language_input is not None
            ):
                translation_factor = self.get_translation_factor(
                    language_input, language_output
                )
                summary_output_tokens = ceil(summary_output_tokens * translation_factor)
                logger.debug(
                    f"summary_output_tokens after translation: {summary_output_tokens} (translation_factor={translation_factor})"
                )

            # Calcular tokens de posprocesamiento
            postprocess_input_tokens = summary_output_tokens
            postprocess_factor = self.postprocess_factor[summary_level]
            postprocess_output_tokens = ceil(
                postprocess_input_tokens * postprocess_factor
            )
            logger.debug(
                f"postprocess_output_tokens: {postprocess_output_tokens} (postprocess_factor={postprocess_factor})"
            )

            if history is not None:
                history.input_factor = float(
                    self.input_factor
                )  # Convertimos np.float64 a float
                if language_input is not None:
                    language_group = LANGUAGE_TO_GROUP.get(
                        language_input.value, LanguageGroup.OTHER
                    )
                summary_factor_for_group = self.group_summary_factor[summary_level].get(
                    language_group,
                    self.group_summary_factor[summary_level][LanguageGroup.OTHER],
                )
                history.output_factor_map_summary = summary_factor_for_group

            return (
                summary_input_tokens,
                summary_output_tokens,
                postprocess_input_tokens,
                postprocess_output_tokens,
            )
        except Exception as e:
            logger.error(f"Error en summary_tokens_predict: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error predicting tokens: {str(e)}"
            )

    def update_factors_from_logs(self, logs: List[Dict]) -> None:
        """Actualiza los factores específicos de idioma usando logs recientes."""
        try:
            char_ratios: Dict[str, List[float]] = {}
            summary_ratios: Dict[str, List[float]] = {}
            translation_ratios: Dict[Tuple[str, str], List[float]] = {}
            alpha = 0.1  # Factor de suavizado

            for log in logs:
                lang_in = log.get("language_input")
                lang_out = log.get("language_output")
                if not lang_in or not lang_out:
                    continue

                # Actualizar char_to_token
                if (
                    log.get("num_chars_file", 0) > 0
                    and log.get("num_tokens_file", 0) > 0
                ):
                    ratio = log["num_tokens_file"] / log["num_chars_file"]
                    char_ratios.setdefault(lang_in, []).append(ratio)

                # Actualizar summary_factor (very_concise)
                if (
                    log.get("num_tokens_summary_input", 0) > 0
                    and log.get("num_tokens_summary_output", 0) > 0
                ):
                    ratio = (
                        log["num_tokens_summary_output"]
                        / log["num_tokens_summary_input"]
                    )
                    summary_ratios.setdefault(lang_in, []).append(ratio)

                # Actualizar translation_factor
                if lang_in != lang_out and log.get("num_tokens_summary_input", 0) > 0:
                    base_summary_factor = self.language_specific_factors.get(
                        lang_in, {}
                    ).get("summary_very_concise", 0.17)
                    if base_summary_factor > 0:
                        ratio = (
                            log["num_tokens_summary_output"]
                            / log["num_tokens_summary_input"]
                        ) / base_summary_factor
                        translation_ratios.setdefault((lang_in, lang_out), []).append(
                            ratio
                        )

            # Aplicar actualización exponencial
            for lang, ratios in char_ratios.items():
                if lang not in self.language_specific_factors:
                    self.language_specific_factors[lang] = {}
                current = self.language_specific_factors[lang].get("char_to_token", 0.5)
                new_ratio = alpha * np.mean(ratios) + (1 - alpha) * current
                self.language_specific_factors[lang]["char_to_token"] = np.float64(
                    round(new_ratio, 4)
                )
                logger.info(f"Updated char_to_token for {lang}: {new_ratio:.4f}")

            for lang, ratios in summary_ratios.items():
                if lang not in self.language_specific_factors:
                    self.language_specific_factors[lang] = {}
                current = self.language_specific_factors[lang].get(
                    "summary_very_concise", 0.17
                )
                new_ratio = alpha * np.mean(ratios) + (1 - alpha) * current
                self.language_specific_factors[lang][
                    "summary_very_concise"
                ] = np.float64(round(new_ratio, 4))
                logger.info(f"Updated summary_very_concise for {lang}: {new_ratio:.4f}")

            for pair, ratios in translation_ratios.items():
                current = self.language_pair_factors.get(pair, {"translation": 1.0})[
                    "translation"
                ]
                new_ratio = alpha * np.mean(ratios) + (1 - alpha) * current
                self.language_pair_factors[pair] = {
                    "translation": np.float64(round(new_ratio, 4))
                }
                logger.info(f"Updated translation for {pair}: {new_ratio:.4f}")
        except Exception as e:
            logger.error(f"Error en update_factors_from_logs: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating factors: {str(e)}"
            )

    def update_factors_from_regression(self, config: Dict) -> None:
        """Actualiza los factores usando resultados de regresión."""
        try:
            # Actualizar char_to_token_factor
            for lang, factor in config.get("char_to_token_factor", {}).items():
                if lang not in self.language_specific_factors:
                    self.language_specific_factors[lang] = {}
                self.language_specific_factors[lang]["char_to_token"] = np.float64(
                    factor
                )
                logger.info(f"Updated char_to_token for {lang}: {factor:.4f}")

            # Actualizar input_factor
            self.input_factor = np.float64(config.get("input_factor", 0.0812))
            logger.info(f"Updated input_factor: {self.input_factor:.4f}")

            # Actualizar summary_factor (very_concise)
            for lang, factor in (
                config.get("output_factor_map_summary", {})
                .get("very_concise", {})
                .items()
            ):
                if lang not in self.language_specific_factors:
                    self.language_specific_factors[lang] = {}
                self.language_specific_factors[lang][
                    "summary_very_concise"
                ] = np.float64(factor)
                logger.info(f"Updated summary_very_concise for {lang}: {factor:.4f}")

            # Actualizar postprocess_factor
            self.postprocess_factor[SummaryLevel.VERY_CONCISE] = np.float64(
                config.get("output_factor_map_postprocess", {}).get(
                    "very_concise", 0.4561
                )
            )
            logger.info(
                f"Updated postprocess_factor (very_concise): {self.postprocess_factor[SummaryLevel.VERY_CONCISE]:.4f}"
            )

            # Actualizar translation_adjustment_factors
            for (lang_in, lang_out), factor in config.get(
                "translation_adjustment_factors", {}
            ).items():
                self.language_pair_factors[(lang_in, lang_out)] = {
                    "translation": np.float64(factor)
                }
                logger.info(
                    f"Updated translation for ({lang_in}, {lang_out}): {factor:.4f}"
                )
        except Exception as e:
            logger.error(f"Error en update_factors_from_regression: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error updating factors from regression: {str(e)}",
            )
