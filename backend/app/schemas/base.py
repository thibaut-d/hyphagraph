from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",   # 🔒 refuse les champs inconnus
        validate_assignment=True
    )


class Timestamped(Schema):
    created_at: datetime | None = None