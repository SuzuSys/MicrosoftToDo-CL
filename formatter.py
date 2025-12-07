def parse_time_to_minutes(s: str) -> int:
    """
    "0:15" や "15" などの入力を分に変換する。
    """
    s = s.strip()
    if ":" in s:
        h_str, m_str = s.split(":", 1)
        h = int(h_str)
        m = int(m_str)
        return h * 60 + m
    else:
        # "15" など → 分として扱う
        return int(s)


def format_minutes(minutes: int) -> str:
    """
    分 → "H:MM" 形式の文字列に変換。
    例: 75 → "1:15"
    """
    h = minutes // 60
    m = minutes % 60
    return f"{h}:{m:02d}"
