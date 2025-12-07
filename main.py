import datetime
import yaml

from client import Client
from formatter import parse_time_to_minutes, format_minutes
from models import (
    QuotedStr,
    Note,
    NoteSubtask,
    ExportSubtask,
    ExportTask,
    ExportData,
    Recurrence,
    RecurrencePattern,
    RecurrenceRange,
)


def input_yn(prompt: str, default_no: bool = True) -> bool:
    """
    Y/n の簡易入力。
    default_no=True のとき、何も入力しなければ False。
    """
    s = input(prompt).strip().lower()
    if not s:
        return not default_no
    return s.startswith("y")


# ----------------------------------------------------------------------
# 取得側: 未完了タスク + サブタスク を ExportData として返す
# ----------------------------------------------------------------------
def get_incomplete_tasks_with_subtasks(client: Client) -> ExportData:
    """
    Microsoft To Do のデフォルトリストから
    '未完了タスク + checklist の完了状態 + Note(YAML)' を集約して返す。
    Note は可能な限り Pydantic モデル Note / NoteSubtask でパースする。
    """
    tasks_raw = client.get_incomplete_tasks()

    export_tasks: list[ExportTask] = []

    for t in tasks_raw:
        task_id = t.id
        title = t.title

        # dueDateTime → "YYYY-MM-DD" だけ取り出す
        if t.dueDateTime and t.dueDateTime.dateTime:
            due = t.dueDateTime.dateTime[:10]
        else:
            due = None

        # Note（body.content）をそのまま文字列で取得
        note_raw = ""
        if t.body and t.body.content:
            note_raw = t.body.content

        note_value: Note | str | None = None

        if note_raw.strip():
            try:
                parsed_yaml = yaml.safe_load(note_raw)
            except yaml.YAMLError:
                # 壊れた YAML などはそのまま文字列として扱う
                note_value = note_raw
            else:
                if isinstance(parsed_yaml, dict):
                    # Pydantic モデルとして検証・正規化
                    try:
                        note_value = Note.model_validate(parsed_yaml)
                    except Exception:
                        # 期待した形でなければ / 途中で変な値があれば素の文字列として保持
                        note_value = note_raw
                else:
                    # dict 以外（スカラ値など）は素の文字列として扱う
                    note_value = note_raw

        # checklistItems を取得
        checklist_items = client.get_checklist_items(task_id)
        subtasks_export = [
            ExportSubtask(title=item.displayName, done=bool(item.isChecked))
            for item in checklist_items
        ]

        export_tasks.append(
            ExportTask(
                title=title,
                due=due,
                note=note_value,
                subtasks=subtasks_export,
                recurrence=t.recurrence,
            )
        )

    return ExportData(tasks=export_tasks)


def export_incomplete_tasks_yaml(client: Client) -> str:
    """
    get_incomplete_tasks_with_subtasks を呼び出し、
    ExportData → dict → YAML 文字列として返す。
    """
    data = get_incomplete_tasks_with_subtasks(client)

    # Pydantic モデル → Python dict
    payload = data.model_dump(mode="python")

    # QuotedStr は models 側で representer が登録済みなので
    # 補正前時間 / サブタスクの推定時間 が必ずダブルクオートで出る
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


# ----------------------------------------------------------------------
# 作成側: 対話的にタスク & Note(Pydantic) & checklist を作る
# ----------------------------------------------------------------------
def create_task_interactive(client: Client) -> None:
    # 1. タイトル
    title = input("タスクのタイトル: ").strip()
    if not title:
        print("タイトルは必須です。終了します。")
        return

    # 2. サブタスクを入力するか？
    use_subtasks = input_yn("サブタスクを入力しますか？ [y/N]: ", default_no=True)

    note_subtasks: list[NoteSubtask] = []
    total_minutes = 0

    # 3. サブタスク入力フロー
    if use_subtasks:
        while True:
            sub_name = input("サブタスクのタイトル: ").strip()
            if not sub_name:
                print("サブタスクのタイトルは必須です。")
                continue

            time_str = input('サブタスクの推定時間 (例 "0:05" または "5"): ').strip()
            try:
                minutes = parse_time_to_minutes(time_str)
            except ValueError:
                print("時間の形式が不正です。やり直してください。")
                continue

            remark = input("サブタスクの備考（空欄なら「なし」）: ").strip() or "なし"

            total_minutes += minutes
            # NoteSubtask に詰める。推定時間は QuotedStr に正規化される。
            note_subtasks.append(
                NoteSubtask(
                    name=sub_name,
                    推定時間=QuotedStr(format_minutes(minutes)),
                    備考=remark,
                )
            )

            cont = input_yn(
                "サブタスクを続けて入力しますか？ [Y/n]: ", default_no=False
            )
            if not cont:
                break

        if total_minutes == 0:
            print("警告: サブタスク合計時間が0分です。とりあえず 0:00 として扱います。")
        corrected_time_str = format_minutes(total_minutes)

    else:
        # 4. サブタスクなし → 補正前時間を直接入力
        while True:
            time_str = input(
                '補正前時間を入力してください (例 "0:15" または "15"): '
            ).strip()
            try:
                minutes = parse_time_to_minutes(time_str)
                break
            except ValueError:
                print("時間の形式が不正です。やり直してください。")
        corrected_time_str = format_minutes(minutes)
        note_subtasks = []

    # 5. 期限(日にち)
    while True:
        due_str = input(
            '期限日を "YYYY-MM-DD" 形式で入力してください (例 2025-12-31): '
        ).strip()
        try:
            due_date = datetime.datetime.strptime(due_str, "%Y-%m-%d").date()
            break
        except ValueError:
            print("日付の形式が不正です。もう一度入力してください。")

    # 6. タスク全体の備考
    task_note_remark = input("タスク全体の備考（空欄なら「なし」）: ").strip() or "なし"

    # 7. Note モデルを組み立てる
    note_model = Note(
        補正前時間=QuotedStr(corrected_time_str),
        サブタスク=note_subtasks,
        備考=task_note_remark,
    )

    # YAML 生成（日本語をそのまま出したいので allow_unicode=True）
    note_yaml = yaml.safe_dump(
        note_model.model_dump(mode="python"),
        allow_unicode=True,
        sort_keys=False,
    )

    print("\n--- 作成される Note (YAML) ---")
    print(note_yaml)
    print("-----------------------------\n")

    confirm = input_yn(
        "この内容で Microsoft To Do にタスクを作成しますか？ [Y/n]: ", default_no=False
    )
    if not confirm:
        print("キャンセルしました。")
        return

    # タスクを作成（client.py の Client を利用）
    todo = client.create_task(title=title, due_date=due_date, note_yaml=note_yaml)
    task_id = todo.id

    print(f"タスクを作成しました: {todo.title} (id={task_id})")

    # サブタスク → checklistItem として追加
    if note_subtasks:
        print("サブタスク（checklistItems）を追加します...")
        for st in note_subtasks:
            client.add_checklist_item(task_id, st.name)
            print(f"  - {st.name}")

    print("完了しました 🎉")


# ----------------------------------------------------------------------
# CLI 本体
# ----------------------------------------------------------------------
def run_cli() -> None:
    client = Client()

    while True:
        get_or_make = input_yn(
            "リストを取得しますか？ No の場合はタスクを作ります。[Y/n]: ",
            default_no=False,
        )
        if get_or_make:
            yaml_text = export_incomplete_tasks_yaml(client)
            print(yaml_text)
        else:
            create_task_interactive(client)

        cont = input_yn("続けますか？[y/N]: ", default_no=True)
        if not cont:
            break


if __name__ == "__main__":
    run_cli()
