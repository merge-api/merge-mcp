from pydantic import BaseModel
from typing import Dict, Any

class CommonModelScope(BaseModel):
    model_name: str
    is_read_enabled: bool
    is_write_enabled: bool


class RequestMeta(BaseModel):
    method: str
    path: str
    query_params: Dict[str, Any] = {}
    body_params: Dict[str, Any] = {}