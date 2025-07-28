from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FileType(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    PARQUET = "parquet"


class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    CATEGORICAL = "categorical"


class ColumnSchema(BaseModel):
    name: str
    data_type: DataType
    nullable: bool = True
    unique: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    default_value: Optional[Any] = None


class DataValidationConfig(BaseModel):
    file_type: FileType
    columns: List[ColumnSchema]
    required_columns: List[str]
    max_rows: Optional[int] = None
    max_columns: Optional[int] = None
    chunk_size: int = 10000


class CleaningRule(BaseModel):
    column_name: str
    rule_type: str
    parameters: Dict[str, Any]
    description: str


class DataTransformConfig(BaseModel):
    name: str
    description: str
    rules: List[CleaningRule]
    schedule: Optional[str] = None  # Cron expression for scheduling


class DataPreview(BaseModel):
    total_rows: int
    total_columns: int
    column_types: Dict[str, str]
    sample_data: List[Dict[str, Any]]
    missing_values: Dict[str, int]
    unique_values: Dict[str, int]
    statistics: Dict[str, Dict[str, float]] 