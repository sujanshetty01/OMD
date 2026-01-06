from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ColumnTagBase(BaseModel):
    tag_fqn: str
    confidence: float
    source: str
    is_auto_applied: bool

class ColumnTagCreate(ColumnTagBase):
    pass

class ColumnTag(ColumnTagBase):
    id: str # UUID from OM
    column_id: Optional[str]

class DataColumnBase(BaseModel):
    name: str
    datatype: str
    sample_values: str # JSON string

class DataColumnCreate(DataColumnBase):
    pass

class DataColumn(DataColumnBase):
    id: Optional[str]
    dataset_id: Optional[str]
    tags: List[ColumnTag] = []

class DatasetBase(BaseModel):
    name: str

class DatasetCreate(DatasetBase):
    row_count: int

class Dataset(DatasetBase):
    id: str # UUID from OM
    created_at: Optional[datetime]
    row_count: int
    columns: List[DataColumn] = []
