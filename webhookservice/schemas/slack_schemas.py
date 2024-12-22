from pydantic import BaseModel, Field
from typing import Optional


class SlackEventPayload(BaseModel):
    type: str
    event: Optional[dict] = None
    challenge: Optional[str] = None


class DeploymentParams(BaseModel):
    branch: str = Field(default="main")
    environment: str = Field(default="staging")
    channel: Optional[str] = Field(default="#chatops")
