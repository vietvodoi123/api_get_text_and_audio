from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uuid
from tasks import process_task
from typing import Optional

app = FastAPI()

# Bộ nhớ lưu trạng thái các task (in-memory, có thể thay bằng database nếu cần)
tasks_store = {}


class CreateTaskRequest(BaseModel):
    story_id: str
    base_url: str  # Ví dụ: "https://truyenyy.xyz/truyen/thu-vien-khoa-hoc-ky-thuat-dich/chuong-{x}"
    css_selector_title: str  # Ví dụ: ".chap-title"
    css_selector_content: str  # Ví dụ: "#inner_chap_content_1"
    total_chapters: int
    webhook_url: Optional[str] = None  # 🟢 Webhook có thể có hoặc không


@app.post("/create-task")
async def create_task(req: CreateTaskRequest, background_tasks: BackgroundTasks):
    # Tính số nhóm: mỗi nhóm 10 chương
    groups = []
    for i in range(0, req.total_chapters, 10):
        start = i + 1
        end = min(req.total_chapters, i + 10)
        groups.append((start, end))

    created_tasks = []
    # Tạo task cho mỗi nhóm
    for start, end in groups:
        task_id = str(uuid.uuid4())
        tasks_store[task_id] = {
            "status": "pending",
            "story_id":req.story_id,
            "audio_urls": [],
            "chapters": {"from": start, "to": end},
            "webhook_url": req.webhook_url,  # 🟢 Lưu webhook nếu có
        }
        # Thêm xử lý task vào background task
        background_tasks.add_task(process_task, task_id, req, start, end, tasks_store)
        created_tasks.append({
            "task_id": task_id,
            "story_id":req.story_id,
            "chapters": {"from": start, "to": end},
            "status": "pending",
            "webhook_url": req.webhook_url

        })
    return created_tasks


@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Không tìm thấy task")
    return tasks_store[task_id]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
