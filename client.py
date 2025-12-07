import cache
import requests
import datetime
from models import (
    TodoTask,
    TodoTaskListResponse,
    ChecklistItem,
    ChecklistItemListResponse,
    TodoBody,
    DueDateTime,
    CreateTaskPayload,
)


class Client:
    def __init__(self):
        self.graph_base = "https://graph.microsoft.com/v1.0"
        self.access_token = cache.get_access_token()
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        self.default_list_id = self._get_default_list_id()

    def _get_default_list_id(self) -> str:
        url = f"{self.graph_base}/me/todo/lists/Tasks"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        data = resp.json()
        return data["id"]

    def create_task(
        self, title: str, due_date: datetime.date, note_yaml: str
    ) -> TodoTask:
        url = f"{self.graph_base}/me/todo/lists/{self.default_list_id}/tasks"
        due_str = due_date.strftime("%Y-%m-%dT00:00:00")
        payload = CreateTaskPayload(
            title=title,
            dueDateTime=DueDateTime(dateTime=due_str),
            body=TodoBody(content=note_yaml),
        )
        resp = requests.post(url, headers=self.headers, json=payload.model_dump())
        resp.raise_for_status()
        return TodoTask.model_validate(resp.json())

    def add_checklist_item(self, task_id: str, display_name: str) -> ChecklistItem:
        url = (
            f"{self.graph_base}/me/todo/lists/"
            f"{self.default_list_id}/tasks/{task_id}/checklistItems"
        )
        body = {
            "displayName": display_name,
            "isChecked": False,
        }
        resp = requests.post(url, headers=self.headers, json=body)
        resp.raise_for_status()
        return ChecklistItem.model_validate(resp.json())

    def get_incomplete_tasks(self) -> list[TodoTask]:
        # 未完了タスクのみ取得（status ne 'completed'）
        url = (
            f"{self.graph_base}/me/todo/lists/"
            f"{self.default_list_id}/tasks"
            f"?$filter=status ne 'completed'"
        )
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()

        # 一旦ラッパーモデルに入れてから .value を返す
        tasks = TodoTaskListResponse.model_validate(resp.json())
        return tasks.value

    def get_checklist_items(self, task_id: str) -> list[ChecklistItem]:
        cl_url = (
            f"{self.graph_base}/me/todo/lists/"
            f"{self.default_list_id}/tasks/{task_id}/checklistItems"
        )
        cl_resp = requests.get(cl_url, headers=self.headers)
        cl_resp.raise_for_status()

        items = ChecklistItemListResponse.model_validate(cl_resp.json())
        return items.value
