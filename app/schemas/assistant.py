"""Schemas for the AI chatbot + natural-language search."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AssistantQuery(BaseModel):
    question: str = Field(min_length=2, max_length=500)
