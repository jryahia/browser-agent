"""FastAPI routes for BrowserBot API server."""

import asyncio
import threading
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks

from .models import TaskCreate, TaskResponse, TaskResult, TaskListResponse
from .tasks import TaskManager
from ..engine.agent import BrowserAgent
from ..llm.client import LLMClient

router = APIRouter()
task_manager = TaskManager()


def _run_task_async(task_id: str, goal: str, headless: bool, max_steps: int, session_id: Optional[str]):
    """Run a task in a background thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run():
        llm = LLMClient()
        agent = BrowserAgent(
            llm_client=llm,
            max_steps=max_steps,
            headless=headless,
            session_id=session_id,
        )
        result = await agent.run(goal)
        return result

    try:
        task_manager.mark_running(task_id)
        result = loop.run_until_complete(_run())

        if result.get("success"):
            task_manager.mark_completed(
                task_id,
                result=result.get("result"),
                steps=result.get("steps", 0),
            )
        else:
            task_manager.mark_failed(
                task_id,
                error=result.get("error", "Unknown error"),
                steps=result.get("steps", 0),
            )
    except Exception as e:
        task_manager.mark_failed(task_id, error=str(e))
    finally:
        loop.close()


@router.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks):
    """Submit a new browser task."""
    task_info = task_manager.create_task(
        goal=task.goal,
        headless=task.headless,
        max_steps=task.max_steps,
        session_id=task.session_id,
    )

    # Start task in background thread
    thread = threading.Thread(
        target=_run_task_async,
        args=(task_info["id"], task.goal, task.headless, task.max_steps, task.session_id),
        daemon=True,
    )
    thread.start()

    return TaskResponse(
        id=task_info["id"],
        goal=task.goal,
        status="pending",
        created_at=task_info["created_at"],
    )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(limit: int = 50, offset: int = 0):
    """List all tasks."""
    tasks = task_manager.list_tasks(limit=limit, offset=offset)
    total = task_manager.get_total_count()

    return TaskListResponse(
        tasks=[
            TaskResponse(
                id=t["id"],
                goal=t["goal"],
                status=t["status"],
                created_at=t["created_at"],
                result=t.get("result"),
                error=t.get("error"),
            )
            for t in tasks
        ],
        total=total,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get task status."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        id=task["id"],
        goal=task["goal"],
        status=task["status"],
        created_at=task["created_at"],
        result=task.get("result"),
        error=task.get("error"),
    )


@router.get("/tasks/{task_id}/result", response_model=TaskResult)
async def get_task_result(task_id: str):
    """Get detailed task result with screenshots."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResult(
        id=task["id"],
        goal=task["goal"],
        status=task["status"],
        result=task.get("result"),
        error=task.get("error"),
        steps=task.get("steps", 0),
        screenshots=task.get("screenshots", []),
        created_at=task["created_at"],
        completed_at=task.get("completed_at"),
    )


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
