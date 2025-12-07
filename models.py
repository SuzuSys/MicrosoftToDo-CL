from typing import List, Optional
from pydantic import BaseModel, field_validator, ConfigDict
import yaml
import formatter


class TodoBody(BaseModel):
    contentType: str = "text"
    content: str


class DueDateTime(BaseModel):
    # ここは Graph API 仕様に合わせて「文字列 ISO8601」にしておくと楽
    dateTime: str
    timeZone: str = "Asia/Tokyo"


class TodoTask(BaseModel):
    id: str
    title: str
    status: str
    dueDateTime: Optional[DueDateTime] = None
    body: Optional[TodoBody] = None


class TodoTaskListResponse(BaseModel):
    value: List[TodoTask]


class ChecklistItem(BaseModel):
    id: str
    displayName: str
    isChecked: bool


class ChecklistItemListResponse(BaseModel):
    value: List[ChecklistItem]


class CreateTaskPayload(BaseModel):
    title: str
    dueDateTime: DueDateTime
    body: TodoBody


class QuotedStr(str):
    """常にダブルクォート付きでYAML出力したい文字列用"""

    pass


def quoted_str_representer(dumper, data):
    return dumper.represent_scalar(
        "tag:yaml.org,2002:str",
        data,
        style='"',  # ← ダブルクォート強制
    )


yaml.add_representer(QuotedStr, quoted_str_representer, Dumper=yaml.SafeDumper)


class NoteSubtask(BaseModel):
    # QuotedStr を使うので、任意型(arbitrary types)を許可
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    推定時間: QuotedStr
    備考: Optional[str] = None  # ← 追加（サブタスクごとの備考）

    @field_validator("推定時間", mode="before")
    @classmethod
    def normalize_time(cls, v):
        """
        YAML から読み込んだ "0:6", "6", "0:06" などを
        すべて "0:06" のような形に正規化しつつ QuotedStr にする。
        """
        if isinstance(v, QuotedStr):
            return v
        if isinstance(v, str):
            mins = formatter.parse_time_to_minutes(v)
            return QuotedStr(formatter.format_minutes(mins))
        # 想定外の型ならそのまま str にしてしまう
        return QuotedStr(str(v))


class Note(BaseModel):
    # こちらも QuotedStr を使うので許可
    model_config = ConfigDict(arbitrary_types_allowed=True)

    補正前時間: QuotedStr
    サブタスク: List[NoteSubtask] = []
    備考: Optional[str] = None

    @field_validator("補正前時間", mode="before")
    @classmethod
    def normalize_time(cls, v):
        if isinstance(v, QuotedStr):
            return v
        if isinstance(v, str):
            mins = formatter.parse_time_to_minutes(v)
            return QuotedStr(formatter.format_minutes(mins))
        return QuotedStr(str(v))


class ExportSubtask(BaseModel):
    title: str
    done: bool


class ExportTask(BaseModel):
    title: str
    due: Optional[str]  # "2025-12-07" など
    note: Optional[Note | str] = None
    subtasks: List[ExportSubtask]


class ExportData(BaseModel):
    tasks: List[ExportTask]
