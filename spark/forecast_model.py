"""
PySpark MLlib Forecasting Model
================================
Executes a GBTRegressor (Gradient-Boosted Tree) model to predict
disease case counts. Generates windowed time-lag variables, runs
a structured ML pipeline, scores predictions against 2024 test sets,
and outputs results to forecast_results.

Output: data/processed/forecast_results
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pyspark.sql import DataFrame, SparkSession, functions as F, types as T
from pyspark.sql.window import Window

from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.regression import GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml import Pipeline, PipelineModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("spark_forecast")

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR: str = os.path.join(BASE_DIR, "data", "processed", "staging_spark_clean")
OUTPUT_DIR: str = os.path.join(BASE_DIR, "data", "processed", "forecast_results")
MODEL_DIR: str = os.path.join(BASE_DIR, "data", "models", "gbt_forecast_model")

TEST_YEARS: List[int] = [2024]
TRAIN_YEARS_RANGE: Tuple[int, int] = (2015, 2023)
TRAIN_RATIO: float = 0.8
LAG_WINDOW_SIZES: List[int] = [1, 2]


def create_spark_session(app_name: str = "HealthcareForecast") -> SparkSession:
    spark: SparkSession = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .getOrCreate()
    )
    logger.info(f"Spark session created: {app_name}")
    return spark


def load_clean_data(spark: SparkSession, input_path: str) -> Optional[DataFrame]:
    if not os.path.exists(input_path):
        logger.warning(f"Clean data not found at {input_path}")
        logger.info("Attempting to run clean_transform first...")
        try:
            from spark.clean_transform import run as run_clean
            run_clean()
        except ImportError:
            logger.error("Cannot import clean_transform. Please run it manually first.")
            return None
        except Exception as e:
            logger.error(f"Failed to run clean_transform: {e}")
            return None
    try:
        df: DataFrame = spark.read.parquet(input_path)
        logger.info(f"Loaded {df.count()} rows from {input_path}")
        return df
    except Exception as e:
        logger.error(f"Failed to load clean data: {e}")
        return None


def prepare_time_series(df: DataFrame) -> DataFrame:
    ts_cols: List[str] = ["region", "disease_name", "year", "case_count"]
    available: List[str] = [c for c in ts_cols if c in df.columns]
    ts_df: DataFrame = df.select(*available)
    ts_df = ts_df.groupBy("region", "disease_name", "year").agg(
        F.avg("case_count").alias("case_count")
    )
    ts_df = ts_df.filter(F.col("year").isNotNull())
    ts_df = ts_df.withColumn("year", F.col("year").cast(T.IntegerType()))
    ts_df = ts_df.filter(F.col("year") >= 2000)
    ts_df = ts_df.orderBy("region", "disease_name", "year")
    logger.info(f"Time series prepared: {ts_df.count()} rows")
    return ts_df


def create_lag_features(df: DataFrame, window_sizes: List[int]) -> DataFrame:
    window_spec = Window.partitionBy("region", "disease_name").orderBy("year")
    for lag_size in window_sizes:
        df = df.withColumn(f"lag_{lag_size}", F.lag("case_count", lag_size).over(window_spec))
    df = df.withColumn("year_diff", F.col("year") - F.lag("year", 1).over(window_spec))
    df = df.withColumn("rolling_avg_2", (
        F.lag("case_count", 1).over(window_spec) +
        F.lag("case_count", 2).over(window_spec)
    ) / 2.0)
    return df


def prepare_features(df: DataFrame) -> DataFrame:
    feature_cols: List[str] = [c for c in df.columns if c.startswith("lag_") or c in ["year_diff", "rolling_avg_2"]]
    df_features: DataFrame = df.dropna(subset=feature_cols + ["case_count"])
    df_features = df_features.withColumn("label", F.col("case_count"))
    logger.info(f"Feature matrix: {df_features.count()} rows with {len(feature_cols)} features")
    return df_features, feature_cols


def compute_year_split(df: DataFrame) -> Tuple[Tuple[int, int], List[int]]:
    years: List[int] = sorted([
        r["year"] for r in
        df.select(F.col("year")).distinct().orderBy(F.col("year")).collect()
    ])
    if not years:
        logger.warning("No years found in data, using defaults")
        return TRAIN_YEARS_RANGE, TEST_YEARS
    max_year: int = years[-1]
    n_test: int = max(1, int(len(years) * (1 - TRAIN_RATIO)))
    test_years: List[int] = years[-n_test:]
    train_years: List[int] = years[:-n_test]
    train_range: Tuple[int, int] = (train_years[0], train_years[-1]) if train_years else (max_year - 5, max_year - n_test)
    logger.info(f"Computed split: train={train_range}, test={test_years} (from available years {years[0]}..{max_year})")
    return train_range, test_years


def split_data(df: DataFrame, train_range: Tuple[int, int], test_years: List[int]) -> Tuple[DataFrame, DataFrame]:
    train_start, train_end = train_range
    train_df: DataFrame = df.filter(
        (F.col("year") >= train_start) & (F.col("year") <= train_end)
    )
    test_df: DataFrame = df.filter(F.col("year").isin(test_years))
    logger.info(f"Train: {train_df.count()} rows ({train_start}-{train_end})")
    logger.info(f"Test: {test_df.count()} rows (years {test_years})")
    return train_df, test_df


def build_pipeline(feature_cols: List[str]) -> Pipeline:
    assembler: VectorAssembler = VectorAssembler(
        inputCols=feature_cols,
        outputCol="feature_vector",
        handleInvalid="skip",
    )
    scaler: StandardScaler = StandardScaler(
        inputCol="feature_vector",
        outputCol="scaled_features",
        withStd=True,
        withMean=True,
    )
    gbt: GBTRegressor = GBTRegressor(
        featuresCol="scaled_features",
        labelCol="label",
        predictionCol="prediction",
        maxIter=100,
        maxDepth=5,
        stepSize=0.1,
        subsamplingRate=0.8,
        minInstancesPerNode=5,
        minInfoGain=0.01,
        lossType="squared",
        seed=42,
    )
    pipeline: Pipeline = Pipeline(stages=[assembler, scaler, gbt])
    return pipeline


def train_model(train_df: DataFrame, feature_cols: List[str]) -> PipelineModel:
    pipeline: Pipeline = build_pipeline(feature_cols)
    logger.info("Training GBTRegressor pipeline...")
    model: PipelineModel = pipeline.fit(train_df)
    logger.info("Model training completed")
    return model


def evaluate_model(model: PipelineModel, test_df: DataFrame) -> Dict[str, float]:
    predictions: DataFrame = model.transform(test_df)
    evaluator_rmse: RegressionEvaluator = RegressionEvaluator(
        labelCol="label", predictionCol="prediction", metricName="rmse"
    )
    evaluator_mae: RegressionEvaluator = RegressionEvaluator(
        labelCol="label", predictionCol="prediction", metricName="mae"
    )
    evaluator_r2: RegressionEvaluator = RegressionEvaluator(
        labelCol="label", predictionCol="prediction", metricName="r2"
    )
    rmse: float = evaluator_rmse.evaluate(predictions)
    mae: float = evaluator_mae.evaluate(predictions)
    r2: float = evaluator_r2.evaluate(predictions)
    metrics: Dict[str, float] = {"rmse": rmse, "mae": mae, "r2": r2}
    logger.info(f"Evaluation metrics: RMSE={rmse:.4f}, MAE={mae:.4f}, R2={r2:.4f}")
    return metrics


def generate_forecast(model: PipelineModel, full_df: DataFrame, feature_cols: List[str]) -> DataFrame:
    predictions: DataFrame = model.transform(full_df)
    result_df: DataFrame = predictions.select(
        "region", "disease_name", "year", "case_count", "prediction",
        (F.col("prediction") - F.col("case_count")).alias("prediction_error"),
        F.lit(datetime.utcnow().isoformat()).alias("forecast_timestamp"),
    )
    result_df = result_df.withColumn("prediction", F.when(F.col("prediction") < 0, 0).otherwise(F.col("prediction")))
    return result_df


def save_model(model: PipelineModel, output_path: str) -> str:
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        model.write().overwrite().save(output_path)
        logger.info(f"Model saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save model: {e}")
        raise
    return output_path


def save_forecast(df: DataFrame, output_path: str, mode: str = "overwrite") -> str:
    try:
        df.write.mode(mode).parquet(output_path)
        logger.info(f"Forecast results saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save forecast: {e}")
        raise
    return output_path


def run() -> Dict[str, Any]:
    logger.info("=== Spark Forecast Model Started ===")
    spark: SparkSession = create_spark_session()

    try:
        clean_df: Optional[DataFrame] = load_clean_data(spark, INPUT_DIR)
        if clean_df is None:
            logger.error("Cannot proceed without clean data")
            return {"status": "failed", "error": "no_clean_data"}

        ts_df: DataFrame = prepare_time_series(clean_df)
        ts_df = create_lag_features(ts_df, LAG_WINDOW_SIZES)
        feature_df, feature_cols = prepare_features(ts_df)

        train_range, test_years = compute_year_split(feature_df)
        train_df, test_df = split_data(feature_df, train_range, test_years)

        if train_df.count() == 0 or test_df.count() == 0:
            logger.error("Empty train or test set. Cannot train model.")
            return {"status": "failed", "error": "empty_train_test"}

        model: PipelineModel = train_model(train_df, feature_cols)

        metrics: Dict[str, float] = evaluate_model(model, test_df)

        forecast_df: DataFrame = generate_forecast(model, feature_df, feature_cols)

        save_model(model, MODEL_DIR)
        save_forecast(forecast_df, OUTPUT_DIR)

        result: Dict[str, Any] = {
            "status": "completed",
            "model_path": MODEL_DIR,
            "forecast_path": OUTPUT_DIR,
            "metrics": metrics,
            "train_rows": train_df.count(),
            "test_rows": test_df.count(),
            "forecast_rows": forecast_df.count(),
            "feature_count": len(feature_cols),
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info(f"=== Forecast model completed: {json.dumps(result, default=str)} ===")
        return result

    except Exception as e:
        logger.error(f"Forecast modeling failed: {e}")
        return {"status": "failed", "error": str(e)}

    finally:
        spark.stop()
        logger.info("Spark session stopped")


if __name__ == "__main__":
    result: Dict[str, Any] = run()
    print(json.dumps(result, indent=2, default=str))
    if result.get("status") != "completed":
        sys.exit(1)
