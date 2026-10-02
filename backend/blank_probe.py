"""空探头代号校验。

规则：探头编号为空串或仅含空白字符时视为缺失，必须在落盘之前拒收。
这里只做清洗与判定，绝不替提交者发明代号（例如“代起探头”）。
"""


def clean_probe(probe_id) -> str:
    """去除首尾空白；None 等缺失值归一为空串。"""
    if probe_id is None:
        return ""
    return str(probe_id).strip()


def is_blank_probe(probe_id) -> bool:
    """空串或全空格（含空格、制表、换行）即缺失代号。"""
    return clean_probe(probe_id) == ""


def reject_message() -> str:
    return "探头编号不能为空"
