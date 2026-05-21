"""Pydantic models for the API server."""

from pydantic import BaseModel, Field
from typing import Optional, Any


class TaskCreate(BaseModel):
    """Request body for creating a new task."""
    goal: str = Field(..., description="The task goal for BrowserBot")
    headless: bool = Field(default=True, description="Run browser in headless mode")
    max_steps: int = Field(default=30, ge=1, le=200, description="Maximum steps")
    session_id: Optional[str] = Field(default=None, description="Session ID for persistence")


class TaskResponse(BaseModel):
    """Response for task status."""
    id: str
    goal: str
    status: str  # pending, running, completed, failed
    created_at: str
    result: Optional[Any] = None
    error: Optional[str] = None


class TaskResult(BaseModel):
    """Detailed task result."""
    id: str
    goal: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    steps: int = 0
    screenshots: list[str] = []
    created_at: str
    completed_at: Optional[str] = None


class TaskListResponse(BaseModel):
    """List of tasks."""
    tasks: list[TaskResponse]
    total: int
