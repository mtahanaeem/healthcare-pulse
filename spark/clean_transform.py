"""
PySpark Data Cleaning and Transformation
=========================================
Ingests raw scraped CSV data (WHO, OWID, CDC), performs duplicate removal,
type casting, median imputation via approxQuantile, and writes the
cleaned output to a staging Spark table.

Output: staging_spark_clean (Parquet)
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from pyspark.sql import DataFrame, SparkSession, functions as F
from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("spark_clean_transform")

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR: str = os.path.join(BASE_DIR, "data")
OUTPUT_DIR: str = os.path.join(DATA_DIR, "processed", "staging_spark_clean")

CSV_FILES: Dict[str, str] = {
    "who": os.path.join(DATA_DIR, "raw", "who_data.csv"),
    "owid": os.path.join(DATA_DIR, "raw", "owid_data.csv"),
    "cdc": os.path.join(DATA_DIR, "raw", "cdc_data.csv"),
    "covid": os.path.join(DATA_DIR, "raw", "covid_data.csv"),
}


def create_spark_session(app_name: str = "HealthcareDataClean") -> SparkSession:
    spark: SparkSession = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
    )
    logger.info(f"Spark session created: {app_name}")
    return spark


def read_csv_with_schema(spark: SparkSession, file_path: str, schema: Optional[StructType] = None) -> Optional[DataFrame]:
    if not os.path.exists(file_path):
        logger.warning(f"CSV file not found: {file_path}")
        return None
    try:
        reader = spark.read.option("header", "true").option("inferSchema", "true").option("quote", '"').option("escape", '"').option("multiLine", "true")
        if schema:
            reader = reader.schema(schema)
        df: DataFrame = reader.csv(file_path)
        logger.info(f"Read {df.count()} rows from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Failed to read CSV {file_path}: {e}")
        return None


WHO_CODE_TO_NAME: Dict[str, str] = {
    "TB_notif_num": "Tuberculosis",
    "MALARIA_PF_INDIG": "Malaria",
    "NCD_DIABETES_PREVALENCE_CRUDE": "Diabetes Mellitus",
    "HEPATITIS_HBV_INFECTIONS_NEW_NUM": "Hepatitis B",
    "HEPATITIS_HCV_INFECTIONS_NEW_NUM": "Hepatitis C",
}

WHO_CODE_TO_CATEGORY: Dict[str, str] = {
    "TB_notif_num": "Communicable",
    "MALARIA_PF_INDIG": "Communicable",
    "NCD_DIABETES_PREVALENCE_CRUDE": "Non-communicable",
    "HEPATITIS_HBV_INFECTIONS_NEW_NUM": "Communicable",
    "HEPATITIS_HCV_INFECTIONS_NEW_NUM": "Communicable",
}

def normalize_who_data(df: DataFrame) -> DataFrame:
    mapping_expr = F.create_map([F.lit(x) for pair in WHO_CODE_TO_NAME.items() for x in pair])
    cat_expr = F.create_map([F.lit(x) for pair in WHO_CODE_TO_CATEGORY.items() for x in pair])
    return (
        df.withColumnRenamed("indicator_code", "disease_code")
        .withColumn("disease_name",
            F.coalesce(mapping_expr.getItem(F.col("disease_code")), F.col("indicator_name")))
        .withColumn("disease_category",
            F.coalesce(cat_expr.getItem(F.col("disease_code")), F.lit(None).cast(StringType())))
        .withColumnRenamed("spatial_dim", "region")
        .withColumnRenamed("time_dim", "year")
        .withColumnRenamed("numeric_value", "case_count")
        .withColumn("year", F.col("year").cast(IntegerType()))
        .withColumn("case_count", F.col("case_count").cast(DoubleType()))
        .withColumn("source", F.lit("WHO"))
        .withColumn("cases_per_100k", F.lit(None).cast(DoubleType()))
        .select("disease_code", "disease_name", "disease_category", "region", "year", "case_count", "source", "cases_per_100k")
    )


OWID_NAME_TO_DISEASE: Dict[str, str] = {
    "cardiovascular_disease_death_rate": "Cardiovascular Disease",
    "diabetes_prevalence": "Diabetes",
    "cancer_death_rate": "Malignant Neoplasms",
    "hiv_death_rate": "HIV/AIDS",
    "maternal_mortality": "Maternal Mortality",
    "child_mortality": "Child Mortality",
}

OWID_NAME_TO_CATEGORY: Dict[str, str] = {
    "cardiovascular_disease_death_rate": "Non-communicable",
    "diabetes_prevalence": "Non-communicable",
    "cancer_death_rate": "Non-communicable",
    "hiv_death_rate": "Communicable",
    "maternal_mortality": "Other",
    "child_mortality": "Other",
}

def normalize_owid_data(df: DataFrame) -> DataFrame:
    skip_cols: set = {"Entity", "Code", "Year", "_disease_name", "_scraped_at"}
    value_cols: List[str] = [c for c in df.columns if c not in skip_cols]
    value_col: str = value_cols[0] if value_cols else df.columns[-1]
    mapping_expr = F.create_map([F.lit(x) for pair in OWID_NAME_TO_DISEASE.items() for x in pair])
    cat_expr = F.create_map([F.lit(x) for pair in OWID_NAME_TO_CATEGORY.items() for x in pair])
    return (
        df.withColumnRenamed("Entity", "region")
        .withColumnRenamed("_disease_name", "disease_name")
        .withColumnRenamed("Year", "year")
        .withColumn("_disease_raw", F.col("disease_name"))
        .withColumn("disease_code", F.lit(None).cast(StringType()))
        .withColumn("year", F.col("year").cast(IntegerType()))
        .withColumn("case_count", F.col(value_col).cast(DoubleType()))
        .withColumn("source", F.lit("OWID"))
        .withColumn("disease_name",
            F.coalesce(mapping_expr.getItem(F.col("_disease_raw")), F.col("_disease_raw")))
        .withColumn("disease_category",
            F.coalesce(cat_expr.getItem(F.col("_disease_raw")), F.lit(None).cast(StringType())))
        .withColumn("cases_per_100k", F.lit(None).cast(DoubleType()))
        .select("disease_code", "disease_name", "disease_category", "region", "year", "case_count", "source", "cases_per_100k")
    )


def normalize_cdc_data(df: DataFrame) -> DataFrame:
    numeric_cols: List[str] = [c for c in df.columns if any(kw in c.lower() for kw in ["value", "rate", "count", "num", "prevalence", "incidence"])]
    value_col: str = numeric_cols[0] if numeric_cols else "_extracted_at"
    return (
        df.withColumn("disease_code", F.lit(None).cast(StringType()))
        .withColumn("disease_name", F.col("_dataset_name"))
        .withColumn("region", F.lit(None).cast(StringType()))
        .withColumn("year", F.lit(datetime.utcnow().year).cast(IntegerType()))
        .withColumn("case_count", F.col(value_col).cast(DoubleType()))
        .withColumn("source", F.lit("CDC"))
        .withColumn("disease_category", F.lit(None).cast(StringType()))
        .withColumn("cases_per_100k", F.lit(None).cast(DoubleType()))
        .select("disease_code", "disease_name", "disease_category", "region", "year", "case_count", "source", "cases_per_100k")
    )


def normalize_covid_data(df: DataFrame) -> DataFrame:
    return (
        df.withColumnRenamed("year", "year_col")
        .withColumn("year", F.col("year_col").cast(IntegerType()))
        .withColumn("case_count", F.col("case_count").cast(DoubleType()))
        .withColumn("cases_per_100k", F.lit(None).cast(DoubleType()))
        .withColumn("disease_category", F.lit("Communicable"))
        .withColumn("source", F.lit("OWID"))
        .select("disease_code", "disease_name", "disease_category", "region", "year", "case_count", "source", "cases_per_100k")
    )

def remove_duplicates(df: DataFrame, subset: Optional[List[str]] = None) -> DataFrame:
    if subset is None:
        subset = ["disease_code", "disease_name", "region", "year"]
    before: int = df.count()
    df_dedup: DataFrame = df.dropDuplicates(subset=subset)
    after: int = df_dedup.count()
    removed: int = before - after
    if removed > 0:
        logger.info(f"Removed {removed} duplicate rows ({before} -> {after})")
    return df_dedup


def cast_types(df: DataFrame) -> DataFrame:
    for col_name, col_type in df.dtypes:
        if col_type == "string" and col_name in ["year", "case_count", "cases_per_100k"]:
            df = df.withColumn(col_name, F.col(col_name).cast(DoubleType()))
    if "year" in df.columns:
        df = df.withColumn("year", F.col("year").cast(IntegerType()))
    for col_name in ["case_count", "cases_per_100k"]:
        if col_name in df.columns:
            df = df.withColumn(col_name, F.col(col_name).cast(DoubleType()))
    return df


def median_imputation(spark: SparkSession, df: DataFrame, target_col: str, group_cols: Optional[List[str]] = None) -> DataFrame:
    if target_col not in df.columns:
        logger.warning(f"Column {target_col} not found for imputation")
        return df
    null_count: int = df.filter(F.col(target_col).isNull()).count()
    if null_count == 0:
        logger.info(f"No null values found in {target_col}, skipping imputation")
        return df
    if group_cols:
        for group_col in group_cols:
            if group_col not in df.columns:
                continue
            df.createOrReplaceTempView("imputation_df")
            medians_df: DataFrame = spark.sql(f"""
                SELECT {group_col} AS impute_group,
                       percentile_approx({target_col}, 0.5, 100) AS median_val
                FROM imputation_df
                WHERE {target_col} IS NOT NULL
                GROUP BY {group_col}
            """)
            df = df.join(F.broadcast(medians_df), F.col(group_col) == F.col("impute_group"), "left") \
                .withColumn(
                    target_col,
                    F.when(F.col(target_col).isNull(), F.col("median_val")).otherwise(F.col(target_col))
                ) \
                .drop("median_val", "impute_group")
            logger.info(f"Imputed {null_count} nulls in {target_col} using group medians by {group_col}")
            return df
    global_median: Optional[float] = df.approxQuantile(target_col, [0.5], 0.01)[0]
    if global_median is not None:
        df = df.fillna({target_col: global_median})
        logger.info(f"Imputed {null_count} nulls in {target_col} with global median {global_median}")
    return df


def standardize_regions(df: DataFrame, spark: Optional[SparkSession] = None) -> DataFrame:
    if "region" not in df.columns:
        return df
    region_mapping: List[tuple] = [
        ("usa", "United States"),
        ("united states of america", "United States"),
        ("uk", "United Kingdom"),
        ("u.k.", "United Kingdom"),
        ("uae", "United Arab Emirates"),
        ("u.a.e.", "United Arab Emirates"),
        ("russia", "Russian Federation"),
        ("south korea", "Republic of Korea"),
        ("tanzania", "United Republic of Tanzania"),
        ("venezuela", "Venezuela (Bolivarian Republic of)"),
        ("viet nam", "Vietnam"),
        ("iran", "Iran (Islamic Republic of)"),
        ("syria", "Syrian Arab Republic"),
        ("laos", "Lao People's Democratic Republic"),
        ("north korea", "Democratic People's Republic of Korea"),
        ("moldova", "Republic of Moldova"),
        ("congo", "Democratic Republic of the Congo"),
        ("côte d'ivoire", "Cote d'Ivoire"),
        ("cote d'ivoire", "Cote d'Ivoire"),
        ("czech republic", "Czechia"),
        ("east timor", "Timor-Leste"),
        ("china", "China"),
        ("india", "India"),
        ("pakistan", "Pakistan"),
        ("bangladesh", "Bangladesh"),
        ("japan", "Japan"),
        ("south korea", "Republic of Korea"),
        ("indonesia", "Indonesia"),
        ("philippines", "Philippines"),
        ("vietnam", "Vietnam"),
        ("thailand", "Thailand"),
        ("myanmar", "Myanmar"),
        ("malaysia", "Malaysia"),
        ("brazil", "Brazil"),
        ("mexico", "Mexico"),
        ("argentina", "Argentina"),
        ("colombia", "Colombia"),
        ("peru", "Peru"),
        ("chile", "Chile"),
        ("ecuador", "Ecuador"),
        ("germany", "Germany"),
        ("france", "France"),
        ("italy", "Italy"),
        ("spain", "Spain"),
        ("netherlands", "Netherlands"),
        ("belgium", "Belgium"),
        ("switzerland", "Switzerland"),
        ("sweden", "Sweden"),
        ("norway", "Norway"),
        ("denmark", "Denmark"),
        ("finland", "Finland"),
        ("poland", "Poland"),
        ("austria", "Austria"),
        ("turkey", "Turkey"),
        ("saudi arabia", "Saudi Arabia"),
        ("egypt", "Egypt"),
        ("nigeria", "Nigeria"),
        ("kenya", "Kenya"),
        ("south africa", "South Africa"),
        ("ethiopia", "Ethiopia"),
        ("ghana", "Ghana"),
        ("morocco", "Morocco"),
        ("algeria", "Algeria"),
        ("angola", "Angola"),
        ("australia", "Australia"),
        ("new zealand", "New Zealand"),
        ("canada", "Canada"),
        ("afghanistan", "Afghanistan"),
        ("albania", "Albania"),
        ("algeria", "Algeria"),
        ("angola", "Angola"),
        ("argentina", "Argentina"),
        ("armenia", "Armenia"),
        ("azerbaijan", "Azerbaijan"),
        ("bahrain", "Bahrain"),
        ("bangladesh", "Bangladesh"),
        ("belarus", "Belarus"),
        ("benin", "Benin"),
        ("bolivia", "Bolivia"),
        ("bosnia and herzegovina", "Bosnia and Herzegovina"),
        ("botswana", "Botswana"),
        ("brunei", "Brunei Darussalam"),
        ("bulgaria", "Bulgaria"),
        ("burkina faso", "Burkina Faso"),
        ("burundi", "Burundi"),
        ("cambodia", "Cambodia"),
        ("cameroon", "Cameroon"),
        ("central african republic", "Central African Republic"),
        ("chad", "Chad"),
        ("colombia", "Colombia"),
        ("comoros", "Comoros"),
        ("congo", "Congo"),
        ("costa rica", "Costa Rica"),
        ("croatia", "Croatia"),
        ("cuba", "Cuba"),
        ("cyprus", "Cyprus"),
        ("czech republic", "Czechia"),
        ("democratic republic of congo", "Democratic Republic of the Congo"),
        ("djibouti", "Djibouti"),
        ("dominican republic", "Dominican Republic"),
        ("ecuador", "Ecuador"),
        ("el salvador", "El Salvador"),
        ("equatorial guinea", "Equatorial Guinea"),
        ("eritrea", "Eritrea"),
        ("eswatini", "Eswatini"),
        ("ethiopia", "Ethiopia"),
        ("fiji", "Fiji"),
        ("gabon", "Gabon"),
        ("gambia", "Gambia"),
        ("georgia", "Georgia"),
        ("ghana", "Ghana"),
        ("greece", "Greece"),
        ("guatemala", "Guatemala"),
        ("guinea", "Guinea"),
        ("guinea-bissau", "Guinea-Bissau"),
        ("guyana", "Guyana"),
        ("haiti", "Haiti"),
        ("honduras", "Honduras"),
        ("hungary", "Hungary"),
        ("iceland", "Iceland"),
        ("iraq", "Iraq"),
        ("ireland", "Ireland"),
        ("israel", "Israel"),
        ("jamaica", "Jamaica"),
        ("jordan", "Jordan"),
        ("kazakhstan", "Kazakhstan"),
        ("kenya", "Kenya"),
        ("kuwait", "Kuwait"),
        ("kyrgyzstan", "Kyrgyzstan"),
        ("laos", "Lao People's Democratic Republic"),
        ("latvia", "Latvia"),
        ("lebanon", "Lebanon"),
        ("lesotho", "Lesotho"),
        ("liberia", "Liberia"),
        ("libya", "Libya"),
        ("lithuania", "Lithuania"),
        ("luxembourg", "Luxembourg"),
        ("madagascar", "Madagascar"),
        ("malawi", "Malawi"),
        ("malaysia", "Malaysia"),
        ("maldives", "Maldives"),
        ("mali", "Mali"),
        ("malta", "Malta"),
        ("mauritania", "Mauritania"),
        ("mauritius", "Mauritius"),
        ("moldova", "Republic of Moldova"),
        ("mongolia", "Mongolia"),
        ("montenegro", "Montenegro"),
        ("morocco", "Morocco"),
        ("mozambique", "Mozambique"),
        ("myanmar", "Myanmar"),
        ("namibia", "Namibia"),
        ("nepal", "Nepal"),
        ("nicaragua", "Nicaragua"),
        ("niger", "Niger"),
        ("nigeria", "Nigeria"),
        ("north korea", "Democratic People's Republic of Korea"),
        ("north macedonia", "North Macedonia"),
        ("oman", "Oman"),
        ("pakistan", "Pakistan"),
        ("panama", "Panama"),
        ("papua new guinea", "Papua New Guinea"),
        ("paraguay", "Paraguay"),
        ("peru", "Peru"),
        ("philippines", "Philippines"),
        ("poland", "Poland"),
        ("portugal", "Portugal"),
        ("qatar", "Qatar"),
        ("romania", "Romania"),
        ("russia", "Russian Federation"),
        ("rwanda", "Rwanda"),
        ("saudi arabia", "Saudi Arabia"),
        ("senegal", "Senegal"),
        ("serbia", "Serbia"),
        ("sierra leone", "Sierra Leone"),
        ("singapore", "Singapore"),
        ("slovakia", "Slovakia"),
        ("slovenia", "Slovenia"),
        ("solomon islands", "Solomon Islands"),
        ("somalia", "Somalia"),
        ("south korea", "Republic of Korea"),
        ("south sudan", "South Sudan"),
        ("sri lanka", "Sri Lanka"),
        ("sudan", "Sudan"),
        ("suriname", "Suriname"),
        ("sweden", "Sweden"),
        ("switzerland", "Switzerland"),
        ("syria", "Syrian Arab Republic"),
        ("tajikistan", "Tajikistan"),
        ("tanzania", "United Republic of Tanzania"),
        ("thailand", "Thailand"),
        ("timor-leste", "Timor-Leste"),
        ("togo", "Togo"),
        ("trinidad and tobago", "Trinidad and Tobago"),
        ("tunisia", "Tunisia"),
        ("turkey", "Turkey"),
        ("turkmenistan", "Turkmenistan"),
        ("uganda", "Uganda"),
        ("ukraine", "Ukraine"),
        ("united arab emirates", "United Arab Emirates"),
        ("united kingdom", "United Kingdom"),
        ("united states", "United States"),
        ("uruguay", "Uruguay"),
        ("uzbekistan", "Uzbekistan"),
        ("vanuatu", "Vanuatu"),
        ("venezuela", "Venezuela (Bolivarian Republic of)"),
        ("vietnam", "Vietnam"),
        ("yemen", "Yemen"),
        ("zambia", "Zambia"),
        ("zimbabwe", "Zimbabwe"),
    ]
    if spark:
        mapping_df: DataFrame = spark.createDataFrame(region_mapping, ["alias", "canonical"])
        df = df.withColumn("region_lower", F.trim(F.lower(F.col("region"))))
        df = df.join(F.broadcast(mapping_df), df["region_lower"] == mapping_df["alias"], "left")
        df = df.withColumn("region", F.coalesce(F.col("canonical"), F.when(F.col("region") == "", F.lit(None)).otherwise(F.col("region"))))
        df = df.drop("region_lower", "alias", "canonical")
    df = df.withColumn("region", F.trim(F.col("region")))
    df = df.withColumn("region", F.when(F.col("region") == "", F.lit(None)).otherwise(F.col("region")))
    return df


def add_metadata_columns(df: DataFrame) -> DataFrame:
    return (
        df.withColumn("etl_timestamp", F.lit(datetime.utcnow().isoformat()))
        .withColumn("etl_batch_id", F.lit(f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"))
        .withColumn("is_valid", F.lit(True))
    )


def write_parquet(df: DataFrame, output_path: str, mode: str = "overwrite") -> str:
    try:
        df.write.mode(mode).parquet(output_path)
        logger.info(f"Wrote {df.count()} rows to {output_path} in {mode} mode")
    except Exception as e:
        logger.error(f"Failed to write Parquet to {output_path}: {e}")
        raise
    return output_path


def run() -> str:
    logger.info("=== Spark Clean Transform Started ===")
    spark: SparkSession = create_spark_session()
    dataframes: List[DataFrame] = []

    try:
        who_df: Optional[DataFrame] = read_csv_with_schema(spark, CSV_FILES["who"])
        if who_df is not None:
            who_norm: DataFrame = normalize_who_data(who_df)
            dataframes.append(who_norm)
            logger.info(f"WHO data: {who_norm.count()} rows")

        owid_df: Optional[DataFrame] = read_csv_with_schema(spark, CSV_FILES["owid"])
        if owid_df is not None:
            owid_norm: DataFrame = normalize_owid_data(owid_df)
            dataframes.append(owid_norm)
            logger.info(f"OWID data: {owid_norm.count()} rows")

        cdc_df: Optional[DataFrame] = read_csv_with_schema(spark, CSV_FILES["cdc"])
        if cdc_df is not None:
            cdc_norm: DataFrame = normalize_cdc_data(cdc_df)
            dataframes.append(cdc_norm)
            logger.info(f"CDC data: {cdc_norm.count()} rows")

        if not dataframes:
            logger.error("No data read from any source. Aborting.")
            spark.stop()
            return ""

        combined: DataFrame = dataframes[0]
        for df in dataframes[1:]:
            combined = combined.unionByName(df, allowMissingColumns=True)

        logger.info(f"Combined dataset: {combined.count()} total rows")

        combined = cast_types(combined)
        combined = remove_duplicates(combined)
        combined = standardize_regions(combined, spark)

        for col_name in ["case_count", "cases_per_100k"]:
            if col_name in combined.columns:
                combined = median_imputation(spark, combined, col_name, group_cols=["region"])

        combined = add_metadata_columns(combined)

        combined = combined.coalesce(1)
        logger.info(f"Final row count: {combined.count()}")

        result_path: str = write_parquet(combined, OUTPUT_DIR)
        logger.info(f"=== Spark Clean Transform Completed — Output: {result_path} ===")
        return result_path

    except Exception as e:
        logger.error(f"Spark clean transform failed: {e}")
        raise
    finally:
        spark.stop()
        logger.info("Spark session stopped")


if __name__ == "__main__":
    result: str = run()
    if result:
        print(f"Clean transform completed. Output: {result}")
    else:
        print("Clean transform completed with no output.")
        sys.exit(1)
