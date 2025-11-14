import json
import os
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

# Constants for video/audio approximations
CHARS_PER_MIN = 1300  # Approximate characters per minute for video/audio
TOKENS_PER_MIN = 450  # Approximate tokens per minute for video/audio
CHARS_PER_SEC = CHARS_PER_MIN / 60  # ≈ 21.6667 chars/sec
TOKENS_PER_SEC = TOKENS_PER_MIN / 60  # ≈ 7.5 tokens/sec

# ==============================
# 🔹 Load JSON logs
# ==============================
log_file_path = "core/brevio_api/logs/logs.json"
if not os.path.exists(log_file_path):
    raise FileNotFoundError(f"No se encontró el fichero: {log_file_path}")
with open(log_file_path, "r", encoding="utf-8") as f:
    logs = json.load(f)
df = pd.DataFrame(logs)

# Handle missing total_time
df["total_time"] = df["total_time"].fillna(0)

# Split into text and video datasets
is_video = df["total_time"] > 0
df_text = df[~is_video].copy()
df_video = df[is_video].copy()

# For video, override num_chars_file and num_tokens_file with approximations
if not df_video.empty:
    df_video["num_chars_file"] = df_video["total_time"] * CHARS_PER_SEC
    df_video["num_tokens_file"] = df_video["total_time"] * TOKENS_PER_SEC


# ==============================
# 🔹 Function to process features
# ==============================
def process_features(df_part: pd.DataFrame, is_video: bool = False) -> pd.DataFrame:
    df_part["char_token_ratio"] = df_part["num_chars_file"] / df_part[
        "num_tokens_file"
    ].replace(0, 1)
    df_part["log_num_tokens_file"] = np.log1p(df_part["num_tokens_file"])
    df_part["log_num_chars_file"] = np.log1p(df_part["num_chars_file"])
    df_part["log_total_tokens_summary_input"] = np.log1p(
        df_part["total_tokens_summary_input"].fillna(0)
    )
    df_part["log_total_tokens_postprocess_input"] = np.log1p(
        df_part["total_tokens_postprocess_input"].fillna(0)
    )

    features = [
        "log_num_tokens_file",
        "log_num_chars_file",
        "char_token_ratio",
        "log_total_tokens_summary_input",
        "log_total_tokens_postprocess_input",
    ]

    if is_video:
        df_part["log_total_time"] = np.log1p(df_part["total_time"])
        features.append("log_total_time")

    df_features = df_part[features]
    df_features = df_features.fillna(df_features.median())
    return df_features


# Process features for text and video
df_features_text = process_features(df_text, is_video=False)
df_features_video = (
    process_features(df_video, is_video=True) if not df_video.empty else pd.DataFrame()
)

# ==============================
# 🔹 Categorical and ordinal variables
# ==============================
categorical_cols = ["model", "type_call"]
ordinal_cols = ["summary_level"]
categorical_cols_existing = [col for col in categorical_cols if col in df.columns]
ordinal_cols_existing = [col for col in ordinal_cols if col in df.columns]
df_cat_text = df_text[categorical_cols_existing].fillna("unknown")
df_ord_text = df_text[ordinal_cols_existing].fillna("concise")
df_cat_video = (
    df_video[categorical_cols_existing].fillna("unknown")
    if not df_video.empty
    else pd.DataFrame()
)
df_ord_video = (
    df_video[ordinal_cols_existing].fillna("concise")
    if not df_video.empty
    else pd.DataFrame()
)

# Summary level order for ordinal encoding
summary_level_order = [["concise", "detailed", "very_detailed"]]


# ==============================
# 🔹 Preprocessing pipelines
# ==============================
def create_preprocessor(
    num_cols: List[str], cat_cols: List[str], ord_cols: List[str]
) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            (
                "cat",
                OneHotEncoder(sparse_output=False, handle_unknown="ignore"),
                cat_cols,
            ),
            (
                "ord",
                OrdinalEncoder(
                    categories=summary_level_order,
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                ),
                ord_cols,
            ),
        ]
    )


# Text preprocessor
num_cols_text = df_features_text.columns.tolist()
all_cols_text = num_cols_text + categorical_cols_existing + ordinal_cols_existing
input_df_text = pd.concat([df_features_text, df_cat_text, df_ord_text], axis=1)
preprocessor_text = create_preprocessor(
    num_cols_text, categorical_cols_existing, ordinal_cols_existing
)
X_text_transformed = preprocessor_text.fit_transform(input_df_text)
cat_feature_names_text = preprocessor_text.named_transformers_[
    "cat"
].get_feature_names_out(categorical_cols_existing)
feature_names_text = (
    num_cols_text + list(cat_feature_names_text) + ordinal_cols_existing
)
# Explicitly convert to DataFrame to avoid type issues
X_text = pd.DataFrame(data=X_text_transformed, columns=feature_names_text, index=input_df_text.index)  # type: ignore

# Video preprocessor (if sufficient data)
if not df_video.empty and len(df_video) > 1:
    num_cols_video = df_features_video.columns.tolist()
    all_cols_video = num_cols_video + categorical_cols_existing + ordinal_cols_existing
    input_df_video = pd.concat([df_features_video, df_cat_video, df_ord_video], axis=1)
    preprocessor_video = create_preprocessor(
        num_cols_video, categorical_cols_existing, ordinal_cols_existing
    )
    X_video_transformed = preprocessor_video.fit_transform(input_df_video)
    cat_feature_names_video = preprocessor_video.named_transformers_[
        "cat"
    ].get_feature_names_out(categorical_cols_existing)
    feature_names_video = (
        num_cols_video + list(cat_feature_names_video) + ordinal_cols_existing
    )
    # Explicitly convert to DataFrame to avoid type issues
    X_video = pd.DataFrame(data=X_video_transformed, columns=feature_names_video, index=input_df_video.index)  # type: ignore
else:
    print(
        "No video data available or insufficient samples. Using text models for video predictions."
    )
    preprocessor_video = preprocessor_text
    feature_names_video = feature_names_text
    all_cols_video = all_cols_text
    X_video = pd.DataFrame()

# ==============================
# 🔹 Targets log-transform
# ==============================
y_summary_text = np.log1p(df_text["total_tokens_summary_output"].fillna(0))
y_postprocess_text = np.log1p(df_text["total_tokens_postprocess_output"].fillna(0))
if not df_video.empty:
    y_summary_video = np.log1p(df_video["total_tokens_summary_output"].fillna(0))
    y_postprocess_video = np.log1p(
        df_video["total_tokens_postprocess_output"].fillna(0)
    )
else:
    y_summary_video = pd.Series([])
    y_postprocess_video = pd.Series([])

# ==============================
# 🔹 Model training
# ==============================
loo = LeaveOneOut()

# Text models
model_summary_text = Ridge(alpha=1.0, random_state=42)
model_postprocess_text = Ridge(alpha=1.0, random_state=42)
y_pred_summary_log_cv_text = cross_val_predict(
    model_summary_text, X_text, y_summary_text, cv=loo, n_jobs=-1
)
y_pred_post_log_cv_text = cross_val_predict(
    model_postprocess_text, X_text, y_postprocess_text, cv=loo, n_jobs=-1
)
model_summary_text.fit(X_text, y_summary_text)
model_postprocess_text.fit(X_text, y_postprocess_text)

# Video models (if sufficient data)
if not df_video.empty and len(df_video) > 1:
    model_summary_video = Ridge(alpha=1.0, random_state=42)
    model_postprocess_video = Ridge(alpha=1.0, random_state=42)
    y_pred_summary_log_cv_video = cross_val_predict(
        model_summary_video, X_video, y_summary_video, cv=loo, n_jobs=-1
    )
    y_pred_post_log_cv_video = cross_val_predict(
        model_postprocess_video, X_video, y_postprocess_video, cv=loo, n_jobs=-1
    )
    model_summary_video.fit(X_video, y_summary_video)
    model_postprocess_video.fit(X_video, y_postprocess_video)
else:
    print("Using text models for video due to insufficient data.")
    model_summary_video = model_summary_text
    model_postprocess_video = model_postprocess_text
    y_pred_summary_log_cv_video = np.array([0]) if not df_video.empty else np.array([])
    y_pred_post_log_cv_video = np.array([0]) if not df_video.empty else np.array([])


# ==============================
# 🔹 Evaluation
# ==============================
def evaluate(
    y_true_log: pd.Series, y_pred_log: np.ndarray
) -> Tuple[float, float, float]:
    if len(y_true_log) <= 1:
        return np.nan, np.nan, np.nan
    y_true = np.expm1(y_true_log)
    y_pred = np.expm1(y_pred_log)
    mse = mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    return mse, mae, r2


# Text evaluation
mse_s_text, mae_s_text, r2_s_text = evaluate(y_summary_text, y_pred_summary_log_cv_text)
mse_p_text, mae_p_text, r2_p_text = evaluate(
    y_postprocess_text, y_pred_post_log_cv_text
)
print(
    f"Text LOOCV Summary MSE: {mse_s_text:.2f}, MAE: {mae_s_text:.2f}, R²: {r2_s_text:.2f}"
)
print(
    f"Text LOOCV Postprocess MSE: {mse_p_text:.2f}, MAE: {mae_p_text:.2f}, R²: {r2_p_text:.2f}"
)

# Video evaluation (if sufficient data)
if len(df_video) > 1:
    mse_s_video, mae_s_video, r2_s_video = evaluate(
        y_summary_video, y_pred_summary_log_cv_video
    )
    mse_p_video, mae_p_video, r2_p_video = evaluate(
        y_postprocess_video, y_pred_post_log_cv_video
    )
    print(
        f"Video LOOCV Summary MSE: {mse_s_video:.2f}, MAE: {mae_s_video:.2f}, R²: {r2_s_video:.2f}"
    )
    print(
        f"Video LOOCV Postprocess MSE: {mse_p_video:.2f}, MAE: {mae_p_video:.2f}, R²: {r2_p_video:.2f}"
    )
else:
    print("Skipping video evaluation due to insufficient data (n_samples <= 1).")

# Feature importance
feature_importance_summary_text = pd.Series(
    np.abs(model_summary_text.coef_), index=feature_names_text
).sort_values(ascending=False)
feature_importance_post_text = pd.Series(
    np.abs(model_postprocess_text.coef_), index=feature_names_text
).sort_values(ascending=False)
print("\nTop 10 Text Summary Feature Importance:")
print(feature_importance_summary_text.head(10))
print("\nTop 10 Text Postprocess Feature Importance:")
print(feature_importance_post_text.head(10))

if not df_video.empty and len(df_video) > 1:
    feature_importance_summary_video = pd.Series(
        np.abs(model_summary_video.coef_), index=feature_names_video
    ).sort_values(ascending=False)
    feature_importance_post_video = pd.Series(
        np.abs(model_postprocess_video.coef_), index=feature_names_video
    ).sort_values(ascending=False)
    print("\nTop 10 Video Summary Feature Importance:")
    print(feature_importance_summary_video.head(10))
    print("\nTop 10 Video Postprocess Feature Importance:")
    print(feature_importance_post_video.head(10))

# ==============================
# 🔹 Prediction intervals
# ==============================
residuals_summary_text = np.expm1(y_summary_text) - np.expm1(y_pred_summary_log_cv_text)
residuals_post_text = np.expm1(y_postprocess_text) - np.expm1(y_pred_post_log_cv_text)
interval_summary_text = (
    np.percentile(np.abs(residuals_summary_text), 95)
    if len(residuals_summary_text) > 0
    else 0
)
interval_postprocess_text = (
    np.percentile(np.abs(residuals_post_text), 95)
    if len(residuals_post_text) > 0
    else 0
)

if not df_video.empty and len(df_video) > 1:
    residuals_summary_video = np.expm1(y_summary_video) - np.expm1(
        y_pred_summary_log_cv_video
    )
    residuals_post_video = np.expm1(y_postprocess_video) - np.expm1(
        y_pred_post_log_cv_video
    )
    interval_summary_video = np.percentile(np.abs(residuals_summary_video), 95)
    interval_postprocess_video = np.percentile(np.abs(residuals_post_video), 95)
else:
    interval_summary_video = interval_summary_text
    interval_postprocess_video = interval_postprocess_text


# ==============================
# 🔹 Prediction function
# ==============================
def predict_output_tokens(
    new_input: Dict[str, Any],
) -> tuple[float, float, float, float]:
    df_new = pd.DataFrame([new_input])
    total_time = df_new["total_time"].fillna(0).iloc[0]
    is_video_pred = total_time > 0

    if is_video_pred:
        # Video/audio: calculate num_chars_file and num_tokens_file from total_time (in seconds)
        if "total_time" not in df_new.columns or total_time <= 0:
            raise ValueError(
                "For video/audio inputs, total_time must be provided and greater than 0."
            )
        df_new["num_chars_file"] = total_time * CHARS_PER_SEC
        df_new["num_tokens_file"] = total_time * TOKENS_PER_SEC
    else:
        # Text: require num_tokens_file and num_chars_file
        if (
            "num_tokens_file" not in df_new.columns
            or "num_chars_file" not in df_new.columns
        ):
            raise ValueError(
                "For text inputs, num_tokens_file and num_chars_file must be provided."
            )
        if (
            df_new["num_tokens_file"].iloc[0] <= 0
            or df_new["num_chars_file"].iloc[0] <= 0
        ):
            raise ValueError(
                "num_tokens_file and num_chars_file must be greater than 0 for text inputs."
            )

    # Feature engineering
    df_new["char_token_ratio"] = df_new["num_chars_file"] / df_new[
        "num_tokens_file"
    ].replace(0, 1)
    df_new["log_num_tokens_file"] = np.log1p(df_new["num_tokens_file"])
    df_new["log_num_chars_file"] = np.log1p(df_new["num_chars_file"])
    df_new["log_total_tokens_summary_input"] = np.log1p(
        df_new["total_tokens_summary_input"].fillna(0)
    )
    df_new["log_total_tokens_postprocess_input"] = np.log1p(
        df_new["total_tokens_postprocess_input"].fillna(0)
    )

    if is_video_pred:
        df_new["log_total_time"] = np.log1p(total_time)

    # Fill missing categorical/ordinal
    for col in categorical_cols_existing:
        if col not in df_new.columns:
            df_new[col] = "unknown"
    for col in ordinal_cols_existing:
        if col not in df_new.columns:
            df_new[col] = "concise"

    # Select preprocessor, model, etc.
    if is_video_pred and len(df_video) > 1:
        preprocessor = preprocessor_video
        feature_names = feature_names_video
        all_cols = all_cols_video
        model_summary = model_summary_video
        model_postprocess = model_postprocess_video
        interval_s = interval_summary_video
        interval_p = interval_postprocess_video
    else:
        preprocessor = preprocessor_text
        feature_names = feature_names_text
        all_cols = all_cols_text
        model_summary = model_summary_text
        model_postprocess = model_postprocess_text
        interval_s = interval_summary_text
        interval_p = interval_postprocess_text

    input_df_new = df_new[all_cols]
    X_new_transformed = preprocessor.transform(input_df_new)
    # Explicitly convert to DataFrame to avoid type issues
    X_new = pd.DataFrame(data=X_new_transformed, columns=feature_names, index=input_df_new.index)  # type: ignore

    pred_summary_log = model_summary.predict(X_new)[0]
    pred_post_log = model_postprocess.predict(X_new)[0]
    pred_summary = np.expm1(pred_summary_log)
    pred_post = np.expm1(pred_post_log)

    # Scale interval based on input size
    if is_video_pred:
        input_scale = total_time / 3600  # Scale by hours (total_time is in seconds)
    else:
        input_scale = df_new["num_tokens_file"].iloc[0] / 100000

    return pred_summary, interval_s * input_scale, pred_post, interval_p * input_scale


# ==============================
# 🔹 Example predictions
# ==============================
# Example: Text input
example_text_input = {
    "model": "gpt-4o-mini",
    "language_input": "english",
    "language_output": "english",
    "category": "technology",
    "style": "changelog",
    "output_format": "markdown",
    "source_type": "text",
    "summary_level": "moderate",
    "type_call": "summary",
    "num_tokens_file": 14749,
    "num_chars_file": 42080,
    "total_tokens_summary_input": 15797,
    "total_tokens_postprocess_input": 2208,
    "total_time": 0,
}
pred_summary, interval_s, pred_post, interval_p = predict_output_tokens(
    example_text_input
)
print("\nText Input Prediction:")
print(f"Predicted summary tokens: {pred_summary:.0f} ± {interval_s:.0f}")
print(f"Predicted postprocess tokens: {pred_post:.0f} ± {interval_p:.0f}")
print(f"Predicted total tokens: {pred_summary + pred_post:.0f}")

# Example: Video input
example_video_input = {
    "model": "gpt-4",
    "language_input": "spanish",
    "language_output": "arabic",
    "category": "education",
    "style": "guide",
    "output_format": "markdown",
    "source_type": "video",
    "summary_level": "concise",
    "type_call": "summary",
    "total_tokens_summary_input": 1676,
    "total_tokens_postprocess_input": 0,
    "total_time": 120,  # 2 minutes = 120 seconds
}
pred_summary, interval_s, pred_post, interval_p = predict_output_tokens(
    example_video_input
)
print("\nVideo Input Prediction:")
print(f"Predicted summary tokens: {pred_summary:.0f} ± {interval_s:.0f}")
print(f"Predicted postprocess tokens: {pred_post:.0f} ± {interval_p:.0f}")
print(f"Predicted total tokens: {pred_summary + pred_post:.0f}")
