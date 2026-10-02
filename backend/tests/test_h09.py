"""空/全空格探头代号必须在落盘前被写口拒收。

覆盖：
- gate 单元：空串、全空格、制表换行、None -> 拒收；合法代号保留并 trim
- 写口：空/空格代号返回 400，且不产生任何插入、不存在“代起探头”脏行
- 连点两次空代号：库行数不暗增
- 合法代号 + 温度：正常 201 入队
- 值班员（reader）不能写：403 且零插入
- 种子样例（探头A01/B02）在拒收发生后不受影响
"""

from datetime import datetime, timezone

import pytest
from aiohttp.test_utils import AioHTTPTestCase

from api import create_app
from blank_probe import clean_probe, is_blank_probe, reject_message
from h09_extra_trap import gate_probe

WRITER = ("logger", "log123456")
WATCHER = ("watcher", "watch123456")
FORBIDDEN_PROBE_NAMES = {"", "代起探头"}


# ---------------------------------------------------------------- unit gates

@pytest.mark.parametrize("raw", ["", "   ", "\t", "\n", " \t\r\n ", None])
def test_gate_rejects_blank(raw):
    assert gate_probe(raw) is None
    assert is_blank_probe(raw) is True


def test_gate_keeps_and_trims_valid():
    assert gate_probe("探头C03") == "探头C03"
    assert gate_probe("  探头C03  ") == "探头C03"
    assert clean_probe(" 甲探 ") == "甲探"


def test_gate_never_invents_name():
    # 任何输入都不得被代起称呼
    for raw in ["", "   ", None, "\t\n"]:
        assert gate_probe(raw) != "代起探头"
    assert reject_message() == "探头编号不能为空"


# ---------------------------------------------------------------- fake DB

class FakeRecord(dict):
    def __getitem__(self, key):
        return self.get(key)


class FakePool:
    """只记录 INSERT 参数的内存池，用于断言写口是否落盘。"""

    def __init__(self):
        self.rows = []
        self._seq = 0
        self.insert_calls = 0

    def seed(self, probe_id, temp_c, status="done"):
        self._seq += 1
        self.rows.append(
            {
                "id": self._seq,
                "probe_id": probe_id,
                "temp_c": temp_c,
                "verdict": "合格" if temp_c <= 8 else "超温",
                "reason": "种子",
                "status": status,
                "created_by": "logger",
                "created_at": datetime.now(timezone.utc),
                "processed_at": datetime.now(timezone.utc),
            }
        )

    async def fetch(self, _query, *_args):
        return [FakeRecord(r) for r in sorted(self.rows, key=lambda x: -x["id"])]

    async def fetchrow(self, query, *args):
        # 仅 INSERT ... RETURNING 走这里
        self.insert_calls += 1
        probe_id, temp_c, username = args[0], float(args[1]), args[2]
        self._seq += 1
        rec = {
            "id": self._seq,
            "probe_id": probe_id,
            "temp_c": temp_c,
            "verdict": None,
            "reason": None,
            "status": "pending",
            "created_by": username,
            "created_at": datetime.now(timezone.utc),
            "processed_at": None,
        }
        self.rows.append(rec)
        return FakeRecord(rec)


# ---------------------------------------------------------------- API 行为

class ReadingApiCase(AioHTTPTestCase):
    async def get_application(self):
        app = create_app()
        # 跳过真实数据库启动/清理钩子，注入内存池
        app.on_startup.clear()
        app.on_cleanup.clear()
        self.pool = FakePool()
        self.pool.seed("探头A01", 4.2)
        self.pool.seed("探头B02", 12.5)
        app["pool"] = self.pool
        return app

    async def _token(self, creds):
        username, password = creds
        resp = await self.client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        assert resp.status == 200
        return (await resp.json())["access_token"]

    async def _post(self, token, payload):
        return await self.client.post(
            "/api/readings",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    async def test_blank_and_whitespace_rejected_before_persist(self):
        token = await self._token(WRITER)
        before = len(self.pool.rows)

        for raw in ["", "   ", "\t\n", " "]:
            resp = await self._post(token, {"probe_id": raw, "temp_c": 5.0})
            assert resp.status == 400, f"空白代号应 400，实际 {resp.status}"
            data = await resp.json()
            assert data["detail"] == reject_message()

        # 零插入：拒收不得留下半截 stub 或代起脏行
        assert self.pool.insert_calls == 0
        assert len(self.pool.rows) == before
        assert not any(r["probe_id"] in FORBIDDEN_PROBE_NAMES for r in self.pool.rows)

    async def test_double_blank_does_not_grow_table(self):
        token = await self._token(WRITER)
        before = len(self.pool.rows)

        r1 = await self._post(token, {"probe_id": "  ", "temp_c": 3.0})
        r2 = await self._post(token, {"probe_id": "", "temp_c": 3.0})
        assert r1.status == 400 and r2.status == 400

        assert self.pool.insert_calls == 0
        assert len(self.pool.rows) == before, "拒收不得令库行数暗增"

    async def test_valid_probe_enqueues(self):
        token = await self._token(WRITER)
        resp = await self._post(token, {"probe_id": " 探头C03 ", "temp_c": 5.0})
        assert resp.status == 201, f"合法代号应入队，实际 {resp.status}"
        data = await resp.json()
        assert data["probe_id"] == "探头C03"  # trim 后落库，不代起
        assert data["status"] == "pending"

        listed = await (await self.client.get(
            "/api/readings", headers={"Authorization": f"Bearer {token}"}
        )).json()
        assert any(r["probe_id"] == "探头C03" and r["status"] == "pending" for r in listed)

    async def test_watcher_cannot_write(self):
        token = await self._token(WATCHER)
        before = len(self.pool.rows)
        resp = await self._post(token, {"probe_id": "探头X99", "temp_c": 5.0})
        assert resp.status == 403
        assert self.pool.insert_calls == 0
        assert len(self.pool.rows) == before, "值班员被拒不得产生任何行"

    async def test_seed_samples_unaffected_after_rejections(self):
        token = await self._token(WRITER)
        for raw in ["", "   "]:
            resp = await self._post(token, {"probe_id": raw, "temp_c": 5.0})
            assert resp.status == 400

        listed = await (await self.client.get(
            "/api/readings", headers={"Authorization": f"Bearer {token}"}
        )).json()
        probes = {r["probe_id"] for r in listed}
        assert {"探头A01", "探头B02"} <= probes
        assert "代起探头" not in probes
        assert "" not in probes
