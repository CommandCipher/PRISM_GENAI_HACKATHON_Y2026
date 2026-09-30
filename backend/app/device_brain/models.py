from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal["auto", "manual", "critical"]

class StepGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    steps: list[str] = Field(min_length=1)
    validationDeeplink: dict[str, Any] | None = None

class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actionName: str
    description: str
    category: Category
    stepGroups: list[StepGroup] = Field(min_length=1)
    actionableDeeplink: str | None = None

    @field_validator("description")
    @classmethod
    def description_format(cls, v: str) -> str:
        v = " ".join(v.split())
        words = v.split()
        if not v.startswith("It will"):
            raise ValueError('description must start with "It will"')
        if not 5 <= len(words) <= 7:
            raise ValueError("description must contain 5-7 words")
        return v

class Goal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str
    title: str
    score: float = Field(ge=0, le=1)
    actions: list[Action]
    query_variations: list[str] = Field(min_length=8, max_length=10)
