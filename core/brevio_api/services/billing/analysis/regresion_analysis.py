import logging
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor  # type: ignore[import]
from sklearn.metrics import mean_squared_error  # type: ignore[import]
from sklearn.model_selection import KFold  # type: ignore[import]
from sklearn.preprocessing import StandardScaler  # type: ignore[import]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

try:
    from scipy import stats  # type: ignore[import]
except ImportError as e:
    logger.error(f"Failed to import scipy.stats: {e}")
    stats = None


def load_logs(logs: List[Dict]) -> pd.DataFrame:
    """Convert logs to a preprocessed DataFrame."""
    try:
        df = pd.DataFrame(logs)
        df["language_pair"] = df["language_input"] + "->" + df["language_output"]

        # Preprocesamiento: eliminar valores inválidos
        initial_len = len(df)
        logger.info(
            f"Missing values: {df[['language_input', 'language_output', 'num_chars_file', 'num_tokens_file']].isna().sum()}"
        )
        logger.info(
            f"Zero values: {(df[['num_chars_file', 'num_tokens_file']] == 0).sum()}"
        )
        df = df.dropna(
            subset=[
                "language_input",
                "language_output",
                "num_chars_file",
                "num_tokens_file",
                "num_tokens_summary_input",
                "num_tokens_summary_output",
                "num_tokens_postprocess_input",
                "num_tokens_postprocess_output",
            ]
        )
        df = df[(df["num_chars_file"] > 0) & (df["num_tokens_file"] > 0)]
        df = df[
            (df["num_tokens_summary_input"] >= 0)
            & (df["num_tokens_summary_output"] >= 0)
        ]
        df = df[
            (df["num_tokens_postprocess_input"] >= 0)
            & (df["num_tokens_postprocess_output"] >= 0)
        ]

        # Eliminar outliers usando MAD
        for col in [
            "num_chars_file",
            "num_tokens_file",
            "num_tokens_summary_input",
            "num_tokens_summary_output",
        ]:
            median = df[col].median()
            mad = np.median(np.abs(df[col] - median))
            df = df[(df[col] >= median - 3 * mad) & (df[col] <= median + 3 * mad)]

        logger.info(
            f"Logs procesados: {initial_len} iniciales, {len(df)} tras limpieza"
        )
        return df
    except Exception as e:
        logger.error(f"Error en load_logs: {e}")
        raise


def robust_regression_fit(
    X: np.ndarray,
    y: np.ndarray,
    title: str,
    xlabel: str,
    ylabel: str,
    filename: str,
    weights: Optional[np.ndarray] = None,
) -> Tuple[float, float, Tuple[float, float]]:
    """Perform robust regression with cross-validation and visualization."""
    try:
        X = np.array(X, dtype=np.float64).reshape(-1, 1)
        y = np.array(y, dtype=np.float64)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        if scaler.scale_ is None:
            raise ValueError(
                "Scaler has not been fitted properly. Ensure X is not empty or invalid."
            )
        if weights is None:
            weights = np.ones(len(X), dtype=np.float64)
        weights = np.array(weights, dtype=np.float64)

        # Validación cruzada
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        mse_scores = []
        factors = []

        for train_idx, test_idx in kf.split(X_scaled):
            X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            w_train = weights[train_idx]

            model = HuberRegressor(epsilon=1.35, max_iter=1000)
            model.fit(X_train, y_train, sample_weight=w_train)
            logger.debug(
                f"HuberRegressor converged in {model.n_iter_} iterations for {title}"
            )
            y_pred = model.predict(X_test)
            mse_scores.append(mean_squared_error(y_test, y_pred))
            factors.append(float(model.coef_[0] / scaler.scale_[0]))

        # Modelo final con todos los datos
        model = HuberRegressor(epsilon=1.35, max_iter=1000)
        model.fit(X_scaled, y, sample_weight=weights)
        y_pred = model.predict(X_scaled)
        mse = float(mean_squared_error(y, y_pred))
        factor = float(model.coef_[0] / scaler.scale_[0])

        # Intervalo de confianza (95%)
        if stats is not None:
            try:
                n = len(X)
                se = np.std(factors) / np.sqrt(n)
                ci = stats.t.interval(0.95, df=n - 1, loc=factor, scale=se)
                ci = (round(float(ci[0]), 4), round(float(ci[1]), 4))
            except Exception as e:
                logger.error(f"Failed to compute confidence interval for {title}: {e}")
                ci = (factor - 0.01, factor + 0.01)  # Fallback CI
        else:
            logger.warning(
                "scipy.stats not available, using fallback confidence interval"
            )
            ci = (factor - 0.01, factor + 0.01)  # Fallback CI

        # Visualización
        plt.figure(figsize=(10, 6))
        plt.scatter(X, y, color="blue", alpha=0.5, label="Datos reales")
        plt.plot(
            X,
            scaler.inverse_transform(X_scaled) * factor + model.intercept_,
            color="red",
            label=f"Regresión (factor={factor:.4f})",
        )
        plt.fill_between(
            X.flatten(),
            (
                scaler.inverse_transform(X_scaled) * factor
                + model.intercept_
                - 1.96 * se
            ).flatten(),
            (
                scaler.inverse_transform(X_scaled) * factor
                + model.intercept_
                + 1.96 * se
            ).flatten(),
            color="red",
            alpha=0.1,
            label="Intervalo confianza 95%",
        )
        plt.title(f"{title} (MSE={mse:.2f}, CI={ci})")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.legend()
        plt.savefig(filename)
        plt.close()

        return factor, mse, ci
    except Exception as e:
        logger.error(
            f"Error en robust_regression_fit ({title}): {e}, data shape={X.shape}, min/max X={X.min()}/{X.max()}, min/max y={y.min()}/{y.max()}"
        )
        # Fallback: Median-based estimation
        factor = float(np.median(y / X.flatten()))
        mse = float(mean_squared_error(y, factor * X.flatten()))
        ci = (factor - 0.01, factor + 0.01)
        logger.info(
            f"Fallback to median-based factor for {title}: factor={factor:.4f}, mse={mse:.2f}"
        )
        return factor, mse, ci


def analyze_factors(df: pd.DataFrame) -> Dict[str, Dict]:
    """Analyze factors for token prediction."""
    results: Dict[str, Dict] = {}

    # Pesos basados en la frecuencia de los datos
    lang_counts = df["language_input"].value_counts().to_dict()
    pair_counts = df["language_pair"].value_counts().to_dict()

    # 1. char_to_token_factor por idioma
    char_to_token: Dict[str, Dict] = {}
    for lang in df["language_input"].unique():
        lang_df = df[df["language_input"] == lang]
        if len(lang_df) >= 10:
            try:
                weights = np.array(
                    [lang_counts.get(lang, 1) / len(lang_df)] * len(lang_df),
                    dtype=np.float64,
                )
                factor, mse, ci = robust_regression_fit(
                    lang_df["num_chars_file"].to_numpy(),
                    lang_df["num_tokens_file"].to_numpy(),
                    f"char_to_token_factor ({lang})",
                    "Caracteres (num_chars_file)",
                    "Tokens (num_tokens_file)",
                    f"char_to_token_{lang}.png",
                    weights=weights,
                )
                char_to_token[lang] = {
                    "factor": round(max(0.1, min(factor, 1.0)), 4),
                    "mse": mse,
                    "ci": ci,
                }
                logger.info(
                    f"char_to_token_factor para {lang}: factor={factor:.4f}, mse={mse:.2f}, ci={ci}"
                )
            except Exception as e:
                logger.warning(f"Error en char_to_token_factor para {lang}: {e}")
                char_to_token[lang] = {
                    "factor": 0.5,
                    "mse": 0.0,
                    "ci": (0.0, 0.0),
                }  # Fallback
                logger.info(f"Usando factor por defecto para {lang}: 0.5")
        else:
            char_to_token[lang] = {
                "factor": 0.5,
                "mse": 0.0,
                "ci": (0.0, 0.0),
            }  # Fallback for insufficient data

    results["char_to_token_factor"] = char_to_token

    # 2. input_factor (general)
    input_df = df[df["num_tokens_file"] > 0]
    if len(input_df) >= 10:
        try:
            weights = np.ones(len(input_df), dtype=np.float64)
            input_factor, mse, ci = robust_regression_fit(
                input_df["num_tokens_file"].to_numpy(),
                input_df["num_tokens_summary_input"].to_numpy(),
                "input_factor",
                "Tokens archivo (num_tokens_file)",
                "Tokens entrada resumen (num_tokens_summary_input)",
                "input_factor.png",
                weights=weights,
            )
            results["input_factor"] = {
                "factor": round(max(0.05, min(input_factor, 1.0)), 4),
                "mse": mse,
                "ci": ci,
            }
            logger.info(
                f"input_factor: factor={input_factor:.4f}, mse={mse:.2f}, ci={ci}"
            )
        except Exception as e:
            logger.warning(f"Error en input_factor: {e}")
            results["input_factor"] = {
                "factor": 0.1884,
                "mse": 0.0,
                "ci": (0.0, 0.0),
            }  # Fallback
    else:
        results["input_factor"] = {
            "factor": 0.1884,
            "mse": 0.0,
            "ci": (0.0, 0.0),
        }  # Fallback

    # 3. output_factor_map_summary por idioma
    summary_factor: Dict[str, Dict] = {}
    for lang in df["language_input"].unique():
        lang_df = df[
            (df["language_input"] == lang) & (df["num_tokens_summary_input"] > 0)
        ]
        if len(lang_df) >= 10:
            try:
                weights = np.array(
                    [lang_counts.get(lang, 1) / len(lang_df)] * len(lang_df),
                    dtype=np.float64,
                )
                factor, mse, ci = robust_regression_fit(
                    lang_df["num_tokens_summary_input"].to_numpy(),
                    lang_df["num_tokens_summary_output"].to_numpy(),
                    f"output_factor_map_summary ({lang})",
                    "Tokens entrada resumen (num_tokens_summary_input)",
                    "Tokens salida resumen (num_tokens_summary_output)",
                    f"summary_factor_{lang}.png",
                    weights=weights,
                )
                summary_factor[lang] = {
                    "factor": round(max(0.0, min(factor, 0.5)), 4),
                    "mse": mse,
                    "ci": ci,
                }
                logger.info(
                    f"output_factor_map_summary para {lang}: factor={factor:.4f}, mse={mse:.2f}, ci={ci}"
                )
            except Exception as e:
                logger.warning(f"Error en output_factor_map_summary para {lang}: {e}")
                summary_factor[lang] = {
                    "factor": 0.17,
                    "mse": 0.0,
                    "ci": (0.0, 0.0),
                }  # Fallback
        else:
            summary_factor[lang] = {
                "factor": 0.17,
                "mse": 0.0,
                "ci": (0.0, 0.0),
            }  # Fallback

    results["output_factor_map_summary"] = summary_factor

    # 4. output_factor_map_postprocess
    postprocess_df = df[df["num_tokens_postprocess_input"] > 0]
    if len(postprocess_df) >= 10:
        try:
            weights = np.ones(len(postprocess_df), dtype=np.float64)
            postprocess_factor, mse, ci = robust_regression_fit(
                postprocess_df["num_tokens_postprocess_input"].to_numpy(),
                postprocess_df["num_tokens_postprocess_output"].to_numpy(),
                "output_factor_map_postprocess",
                "Tokens entrada posprocesamiento (num_tokens_postprocess_input)",
                "Tokens salida posprocesamiento (num_tokens_postprocess_output)",
                "postprocess_factor.png",
                weights=weights,
            )
            results["output_factor_map_postprocess"] = {
                "factor": round(max(0.0, min(postprocess_factor, 0.5)), 4),
                "mse": mse,
                "ci": ci,
            }
            logger.info(
                f"output_factor_map_postprocess: factor={postprocess_factor:.4f}, mse={mse:.2f}, ci={ci}"
            )
        except Exception as e:
            logger.warning(f"Error en output_factor_map_postprocess: {e}")
            results["output_factor_map_postprocess"] = {
                "factor": 0.4508,
                "mse": 0.0,
                "ci": (0.0, 0.0),
            }  # Fallback
    else:
        results["output_factor_map_postprocess"] = {
            "factor": 0.4508,
            "mse": 0.0,
            "ci": (0.0, 0.0),
        }  # Fallback

    # 5. translation_adjustment_factors por par de idiomas
    translation_factor: Dict[str, Dict] = {}
    for pair in df["language_pair"].unique():
        pair_df = df[
            (df["language_pair"] == pair) & (df["num_tokens_summary_input"] > 0)
        ].copy()
        if len(pair_df) >= 10:
            try:
                lang_in = pair.split("->")[0]
                base_summary_factor = summary_factor.get(lang_in, {"factor": 0.17})[
                    "factor"
                ]
                if base_summary_factor > 0:
                    pair_df["adjusted_output"] = (
                        pair_df["num_tokens_summary_output"]
                        / pair_df["num_tokens_summary_input"]
                        / base_summary_factor
                    )
                    weights = np.array(
                        [pair_counts.get(pair, 1) / len(pair_df)] * len(pair_df),
                        dtype=np.float64,
                    )
                    factor, mse, ci = robust_regression_fit(
                        pair_df["num_tokens_summary_input"].to_numpy(),
                        pair_df["adjusted_output"].to_numpy(),
                        f"translation_adjustment_factor ({pair})",
                        "Tokens entrada resumen (num_tokens_summary_input)",
                        "Tokens salida ajustados",
                        f'translation_factor_{pair.replace("->", "_")}.png',
                        weights=weights,
                    )
                    translation_factor[pair] = {
                        "factor": round(max(0.1, min(factor, 2.0)), 4),
                        "mse": mse,
                        "ci": ci,
                    }
                    logger.info(
                        f"translation_adjustment_factor para {pair}: factor={factor:.4f}, mse={mse:.2f}, ci={ci}"
                    )
            except Exception as e:
                logger.warning(
                    f"Error en translation_adjustment_factor para {pair}: {e}"
                )
                translation_factor[pair] = {
                    "factor": 1.0,
                    "mse": 0.0,
                    "ci": (0.0, 0.0),
                }  # Fallback
        else:
            translation_factor[pair] = {
                "factor": 1.0,
                "mse": 0.0,
                "ci": (0.0, 0.0),
            }  # Fallback

    results["translation_adjustment_factors"] = translation_factor

    return results


def generate_updated_config(results: Dict[str, Dict]) -> Dict:
    """Generate updated configuration from regression results."""
    try:
        config = {
            "char_to_token_factor": {
                lang: float(data["factor"])
                for lang, data in results["char_to_token_factor"].items()
            },
            "input_factor": float(
                results.get("input_factor", {"factor": 0.1884})["factor"]
            ),
            "output_factor_map_summary": {
                "very_concise": {
                    lang: float(data["factor"])
                    for lang, data in results["output_factor_map_summary"].items()
                }
            },
            "output_factor_map_postprocess": {
                "very_concise": float(
                    results.get("output_factor_map_postprocess", {"factor": 0.4508})[
                        "factor"
                    ]
                )
            },
            "translation_adjustment_factors": {
                tuple(pair.split("->")): float(data["factor"])
                for pair, data in results["translation_adjustment_factors"].items()
            },
        }
        return config
    except Exception as e:
        logger.error(f"Error en generate_updated_config: {e}")
        raise


def main(logs: List[Dict]) -> Dict:
    """Main function to process logs and generate configuration."""
    try:
        df = load_logs(logs)
        results = analyze_factors(df)
        config = generate_updated_config(results)

        print("Resultados de la regresión:")
        for key, value in results.items():
            print(f"{key}:")
            if isinstance(value, dict) and all(
                isinstance(v, dict) for v in value.values()
            ):
                for subkey, subvalue in value.items():
                    print(
                        f"  {subkey}: factor={subvalue['factor']:.4f}, mse={subvalue['mse']:.2f}, ci={subvalue['ci']}"
                    )
            else:
                print(
                    f"  factor={value['factor']:.4f}, mse={value['mse']:.2f}, ci={value['ci']}"
                )

        print("\nConfiguración actualizada:")
        print(config)

        return config
    except Exception as e:
        logger.error(f"Error en main: {e}")
        raise
