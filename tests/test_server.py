"""MCP server 契约测试（plan 三·根因层守护）。

需要 `mcp` 与 `devnors_data` 可导入（CI 走 pip install -e ./sdk ./mcp_server）。
用 fake SDK client / httpx MockTransport 隔离网络。
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

pytest.importorskip("mcp")

from devnors_data import DevnorsDataError  # noqa: E402
from devnors_mcp import server as s  # noqa: E402


class FakeClient:
    """记录调用参数的假 SDK client。"""

    def __init__(self, result=None, error: Exception | None = None):
        self.calls: list = []
        self._result = result or {"total_hits": 1, "units": 2,
                                  "request_id": "rid", "hits": [{"a": 1}]}
        self._error = error

    async def legal_cases(self, query, *, top_k=5, filters=None):
        self.calls.append(("legal_cases", query, top_k, filters))
        if self._error:
            raise self._error
        return self._result

    async def legal_laws(self, query, *, top_k=5, filters=None):
        self.calls.append(("legal_laws", query, top_k, filters))
        if self._error:
            raise self._error
        return self._result

    async def query(self, domain, type, query="", *, top_k=5, filters=None):
        self.calls.append((domain, type, query, top_k, filters))
        if self._error:
            raise self._error
        return self._result


def _use(monkeypatch, fake: FakeClient):
    monkeypatch.setattr(s, "_client", lambda: fake)
    return fake


# ── 纯函数 ───────────────────────────────────────────────────────────────
def test_fmt_prunes_to_contract():
    out = s._fmt({"total_hits": 3, "units": 5, "request_id": "r",
                  "hits": [1, 2], "domain": "legal", "noise": "x"})
    assert out == {"total_hits": 3, "units": 5, "request_id": "r", "hits": [1, 2]}


def test_err_surfaces_structured_fields():
    e = DevnorsDataError("余额不足", status=402, code="insufficient_balance",
                         request_id="rid", retryable=False, next_action="去充值")
    out = s._err(e)
    assert out["code"] == "insufficient_balance"
    assert out["retryable"] is False
    assert out["request_id"] == "rid"
    assert out["recharge_url"].endswith("/console/recharge")
    assert "充值" in out["next_action"]
    assert out["recharge_url"] in out["next_action"]
    assert out["recharge_url"] in out["error"]


def test_err_non_balance_unchanged():
    e = DevnorsDataError("限流", status=429, code="rate_limited",
                         request_id="rid", retryable=True, next_action="退避")
    out = s._err(e)
    assert out == {"error": "限流", "code": "rate_limited",
                   "retryable": True, "next_action": "退避", "request_id": "rid"}


def test_base_url_env_override(monkeypatch):
    monkeypatch.setenv("DEVNORS_DATA_BASE_URL", "http://local:8080/")
    assert s._base_url() == "http://local:8080"
    monkeypatch.delenv("DEVNORS_DATA_BASE_URL", raising=False)
    assert s._base_url() == "https://data.devnors.com"


# ── tool 默认值 / 透传 / 委派 ─────────────────────────────────────────────
def test_legal_case_search_default_top_k(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    out = asyncio.run(s.legal_case_search("借贷"))
    assert out["total_hits"] == 1 and out["request_id"] == "rid"
    assert fake.calls == [("legal_cases", "借贷", 5, None)]   # 默认 top_k=5


def test_data_query_passes_filters_and_defaults(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.data_query("legal", "case", "q", filters={"case_type": "民事"}))
    assert fake.calls == [("legal", "case", "q", 5, {"case_type": "民事"})]


def test_content_keyword_index_delegates(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.content_keyword_index("劳动仲裁", top_k=3))
    assert fake.calls == [("content", "keyword_index", "劳动仲裁", 3, None)]


def test_content_suggest_list_passes_platform(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.content_suggest_list(
        "劳动仲裁", filters={"platform": "baidu"},
    ))
    assert fake.calls == [(
        "content", "suggest_list", "劳动仲裁", 5,
        {"platform": "baidu"},
    )]


def test_content_keyword_word_passes_filters(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.content_keyword_word(
        "劳动仲裁", top_k=100, filters={"offset": 0, "sort_fields": 4},
    ))
    assert fake.calls == [(
        "content", "keyword_word", "劳动仲裁", 100,
        {"offset": 0, "sort_fields": 4},
    )]


def test_content_bidword_passes_filters(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.content_bidword(
        "jd.com", top_k=20, filters={"offset": 0, "isc": 0},
    ))
    assert fake.calls == [(
        "content", "bidword", "jd.com", 20,
        {"offset": 0, "isc": 0},
    )]


def test_no_content_hot_rank_tool():
    assert not hasattr(s, "content_hot_rank")


def test_research_paper_search_delegates(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.research_paper_search("Attention Is All You Need", top_k=3))
    assert fake.calls == [
        ("research", "paper_search", "Attention Is All You Need", 3, None)
    ]


def test_research_patent_search_passes_filters(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.research_patent_search("Si02", filters={"offset": 0}))
    assert fake.calls == [
        ("research", "patent_search", "Si02", 20, {"offset": 0})
    ]


def test_research_journal_search_delegates(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.research_journal_search("tkde"))
    assert fake.calls == [("research", "journal_search", "tkde", 10, None)]


def test_research_paper_detail_delegates(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.research_paper_detail("p1", top_k=1))
    assert fake.calls == [("research", "paper_detail", "p1", 1, None)]


def test_research_patent_detail_passes_filters(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.research_patent_detail("", filters={"id": "pat1"}))
    assert fake.calls == [("research", "patent_detail", "", 1, {"id": "pat1"})]


def test_research_journal_detail_delegates(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.research_journal_detail("v1"))
    assert fake.calls == [("research", "journal_detail", "v1", 1, None)]


def test_research_scholar_search_delegates(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.research_scholar_search("Andrew Ng", top_k=3))
    assert fake.calls == [("research", "scholar_search", "Andrew Ng", 3, None)]


def test_research_scholar_detail_passes_filters(monkeypatch):
    fake = _use(monkeypatch, FakeClient())
    asyncio.run(s.research_scholar_detail("", filters={"id": "p1"}))
    assert fake.calls == [("research", "scholar_detail", "", 1, {"id": "p1"})]


def test_tool_error_returns_structured(monkeypatch):
    err = DevnorsDataError("限流", status=429, code="rate_limited",
                           request_id="r2", retryable=True, next_action="退避重试")
    _use(monkeypatch, FakeClient(error=err))
    out = asyncio.run(s.data_query("legal", "case", "q"))
    assert out["code"] == "rate_limited" and out["retryable"] is True
    assert out["request_id"] == "r2"


# ── list_capabilities 自发现 ─────────────────────────────────────────────
def _mock_async_client(monkeypatch, handler):
    real_async = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(s.httpx, "AsyncClient",
                        lambda **kw: real_async(transport=transport, **kw))


def test_list_capabilities_success(monkeypatch):
    payload = {
        "service": "Devnors",
        "capabilities": [
            {"domain": "legal", "type": "case", "status": "live"},
            {"domain": "enterprise", "type": "company_detail", "status": "deprecated"},
        ],
    }
    _mock_async_client(monkeypatch, lambda req: httpx.Response(200, json=payload))
    out = asyncio.run(s.list_capabilities())
    assert out["service"] == "Devnors"
    assert out["capabilities"] == [{"domain": "legal", "type": "case", "status": "live"}]


def test_list_capabilities_failure(monkeypatch):
    _mock_async_client(monkeypatch, lambda req: httpx.Response(500, text="boom"))
    out = asyncio.run(s.list_capabilities())
    assert "error" in out and out["url"].endswith("/capabilities.json")
