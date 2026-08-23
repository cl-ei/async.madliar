import datetime
from pydantic import BaseModel, Field
from typing import Optional


class FileLike(BaseModel):
    id: Optional[str] = ""
    type: Optional[str] = ""
    text: Optional[str] = ""
