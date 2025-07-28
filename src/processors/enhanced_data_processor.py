from pathlib import Path
from typing import List, Optional, Union

import dask.dataframe as dd
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from schemas import (
    CleaningRule,
    ColumnSchema,
    DataPreview,
    DataType,
    DataValidationConfig,
    FileType,
)
from utils import logger


class EnhancedDataProcessor:
    def __init__(self, chunk_size: int = 10000):
        self.chunk_size = chunk_size
        self.supported_formats = {
            ".csv": FileType.CSV,
            ".xlsx": FileType.EXCEL,
            ".xls": FileType.EXCEL,
            ".json": FileType.JSON,
            ".parquet": FileType.PARQUET,
        }

    def read_file(
        self, file_path: str, file_type: Optional[FileType] = None
    ) -> Union[pd.DataFrame, dd.DataFrame]:
        """Read file with support for multiple formats and chunking"""
        file_path = Path(file_path)
        if file_type is None:
            file_type = self.supported_formats.get(file_path.suffix.lower())
            if file_type is None:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")

        try:
            if file_type == FileType.CSV:
                return dd.read_csv(file_path, blocksize=self.chunk_size)
            elif file_type == FileType.EXCEL:
                return pd.read_excel(file_path)
            elif file_type == FileType.JSON:
                return dd.read_json(file_path, blocksize=self.chunk_size)
            elif file_type == FileType.PARQUET:
                return dd.read_parquet(file_path)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise

    def validate_data(
        self, df: Union[pd.DataFrame, dd.DataFrame], config: DataValidationConfig
    ) -> List[str]:
        """Validate data against schema"""
        errors = []

        # Convert dask DataFrame to pandas for validation
        if isinstance(df, dd.DataFrame):
            df = df.compute()

        # Check required columns
        missing_columns = set(config.required_columns) - set(df.columns)
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")

        # Validate each column
        for col_schema in config.columns:
            if col_schema.name not in df.columns:
                continue

            col = df[col_schema.name]

            # Check data type
            if col_schema.data_type == DataType.INTEGER:
                if not pd.api.types.is_integer_dtype(col):
                    errors.append(f"Column {col_schema.name} should be integer type")
            elif col_schema.data_type == DataType.FLOAT:
                if not pd.api.types.is_float_dtype(col):
                    errors.append(f"Column {col_schema.name} should be float type")
            elif col_schema.data_type == DataType.DATETIME:
                if not pd.api.types.is_datetime64_any_dtype(col):
                    errors.append(f"Column {col_schema.name} should be datetime type")

            # Check nullable
            if not col_schema.nullable and col.isnull().any():
                errors.append(
                    f"Column {col_schema.name} contains null values but is not nullable"
                )

            # Check unique
            if col_schema.unique and not col.is_unique:
                errors.append(
                    f"Column {col_schema.name} should be unique but contains duplicates"
                )

            # Check value ranges
            if col_schema.min_value is not None:
                if (col < col_schema.min_value).any():
                    errors.append(
                        f"Column {col_schema.name} contains values below minimum {col_schema.min_value}"
                    )
            if col_schema.max_value is not None:
                if (col > col_schema.max_value).any():
                    errors.append(
                        f"Column {col_schema.name} contains values above maximum {col_schema.max_value}"
                    )

            # Check allowed values
            if col_schema.allowed_values is not None:
                invalid_values = set(col.unique()) - set(col_schema.allowed_values)
                if invalid_values:
                    errors.append(
                        f"Column {col_schema.name} contains invalid values: {invalid_values}"
                    )

        return errors

    def generate_preview(self, df: Union[pd.DataFrame, dd.DataFrame]) -> DataPreview:
        """Generate data preview with statistics"""
        if isinstance(df, dd.DataFrame):
            df = df.compute()

        preview = DataPreview(
            total_rows=len(df),
            total_columns=len(df.columns),
            column_types={col: str(dtype) for col, dtype in df.dtypes.items()},
            sample_data=df.head(5).to_dict("records"),
            missing_values=df.isnull().sum().to_dict(),
            unique_values={col: df[col].nunique() for col in df.columns},
            statistics={},
        )

        # Generate statistics for numeric columns
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            stats = df[numeric_cols].describe()
            preview.statistics = {
                col: {
                    "mean": stats[col]["mean"],
                    "std": stats[col]["std"],
                    "min": stats[col]["min"],
                    "max": stats[col]["max"],
                }
                for col in numeric_cols
            }

        return preview

    def apply_cleaning_rules(
        self, df: Union[pd.DataFrame, dd.DataFrame], rules: List[CleaningRule]
    ) -> Union[pd.DataFrame, dd.DataFrame]:
        """Apply cleaning rules to the dataset"""
        if isinstance(df, dd.DataFrame):
            df = df.compute()

        for rule in rules:
            if rule.column_name not in df.columns:
                logger.warning(f"Column {rule.column_name} not found, skipping rule")
                continue

            if rule.rule_type == "fill_missing":
                df[rule.column_name] = df[rule.column_name].fillna(
                    rule.parameters.get("value")
                )
            elif rule.rule_type == "replace_values":
                df[rule.column_name] = df[rule.column_name].replace(
                    rule.parameters.get("mapping", {})
                )
            elif rule.rule_type == "drop_duplicates":
                df = df.drop_duplicates(subset=[rule.column_name])
            elif rule.rule_type == "convert_type":
                target_type = rule.parameters.get("type")
                if target_type == "datetime":
                    df[rule.column_name] = pd.to_datetime(df[rule.column_name])
                elif target_type == "numeric":
                    df[rule.column_name] = pd.to_numeric(
                        df[rule.column_name], errors="coerce"
                    )

        return df

    def save_file(
        self, df: Union[pd.DataFrame, dd.DataFrame], output_path: str, file_type: FileType
    ) -> str:
        """Save processed data to file"""
        output_path = Path(output_path)

        try:
            if file_type == FileType.CSV:
                if isinstance(df, dd.DataFrame):
                    df.to_csv(output_path, single_file=True)
                else:
                    df.to_csv(output_path, index=False)
            elif file_type == FileType.EXCEL:
                if isinstance(df, dd.DataFrame):
                    df.compute().to_excel(output_path, index=False)
                else:
                    df.to_excel(output_path, index=False)
            elif file_type == FileType.JSON:
                if isinstance(df, dd.DataFrame):
                    df.to_json(output_path, orient="records")
                else:
                    df.to_json(output_path, orient="records")
            elif file_type == FileType.PARQUET:
                if isinstance(df, dd.DataFrame):
                    df.to_parquet(output_path)
                else:
                    table = pa.Table.from_pandas(df)
                    pq.write_table(table, output_path)

            return str(output_path)
        except Exception as e:
            logger.error(f"Error saving file {output_path}: {str(e)}")
            raise 