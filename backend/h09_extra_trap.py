"""写口闸门：探头代号先清洗，空串/全空格一律拒收。

gate_probe 返回 None 表示拒收，调用方必须在任何数据库写入之前短路；
返回非空字符串才是可落库的合法代号。任何情况下都不得代起称呼，
拒收路径也不得先行插入半截空行。
"""

from blank_probe import clean_probe, is_blank_probe


def gate_probe(probe_id) -> str | None:
    """清洗代号；空或全空格返回 None 表示拒收。"""
    if is_blank_probe(probe_id):
        return None
    return clean_probe(probe_id)
