"""Devnors Data MCP Server（标准 Anthropic MCP，stdio）。

把统一数据网关 ``POST /v1/data/query`` 暴露为 MCP 工具，供 Claude / Cursor 等一行接入。
鉴权用 API Key（环境变量 ``DEVNORS_API_KEY``；可选 ``DEVNORS_DATA_BASE_URL`` 覆盖地址）。

减法：工具全部转调 SDK ``AsyncDevnorsData``，不重复实现 HTTP/契约；能力表不在此重抄，
Agent 用 ``list_capabilities`` 运行时自发现（单一真源 = 服务端 /capabilities.json）。
重试也**继承 SDK**（429/5xx 有界退避），MCP 层不再自行重试，避免与 SDK 叠乘。

运行::

    DEVNORS_API_KEY=devnors_sk_live_xxx python -m devnors_mcp.server
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from devnors_data import AsyncDevnorsData, DevnorsDataError

mcp = FastMCP("devnors-data")

_DEFAULT_BASE = "https://data.devnors.com"


def _base_url() -> str:
    return os.getenv("DEVNORS_DATA_BASE_URL", _DEFAULT_BASE).rstrip("/")


def _client() -> AsyncDevnorsData:
    return AsyncDevnorsData(api_key=os.getenv("DEVNORS_API_KEY", ""), base_url=_base_url())


def _fmt(res: dict) -> dict[str, Any]:
    """精简返回给模型：命中 + 计量 + request_id（报障/对账），剔除冗余包装。"""
    return {
        "total_hits": res.get("total_hits"),
        "units": res.get("units"),
        "request_id": res.get("request_id"),
        "hits": res.get("hits", []),
    }


def _err(e: DevnorsDataError) -> dict[str, Any]:
    """结构化错误：透出 code/retryable/next_action/request_id，让 Agent 自纠而非死循环。"""
    return {
        "error": str(e),
        "code": e.code,
        "retryable": getattr(e, "retryable", False),
        "next_action": getattr(e, "next_action", ""),
        "request_id": getattr(e, "request_id", ""),
    }


@mcp.tool()
async def legal_case_search(query: str, top_k: int = 5) -> dict[str, Any]:
    """检索中国裁判文书（官方公开，出处可回溯）。

    - query：自然语言检索词（如「民间借贷 利息」）。
    - top_k：返回条数 1-200，默认 5。
    - 返回 hits[] 常含：case_no(案号)、court_name(法院)、cause_of_action(案由)、
      case_type(案件类型)、judgment_date、judgment_result、summary、applied_laws、score。
    - 计费：按次调用扣 units；余额不足→code=insufficient_balance、限流→code=rate_limited(可退避重试)。
    - 更多过滤维度（case_type/court_level/province/年份等）与完整字段见 list_capabilities。
    """
    try:
        return _fmt(await _client().legal_cases(query, top_k=top_k))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def legal_law_search(query: str, top_k: int = 5) -> dict[str, Any]:
    """检索中国现行法律法规条文（回源官方语料 + 语义召回）。

    - query：自然语言检索词（如「合同解除 违约金」）。top_k 1-200，默认 5。
    - 返回 hits[] 常含：law_name(所属法律)、article_no(条号)、content(正文)、law_level(位阶)、source_url。
    - 可用 data_query 传 filters：law_name / law_level / jurisdiction_scope（见 list_capabilities）。
    - 计费与错误码同 legal_case_search。
    """
    try:
        return _fmt(await _client().legal_laws(query, top_k=top_k))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def content_keyword_index(query: str, top_k: int = 5,
                                filters: dict | None = None) -> dict[str, Any]:
    """查询关键词流量指数（含 SEM bidword_*；第三方商业数据，非百度/抖音官方指数）。

    - query：关键词；也可用 filters.keywords 批量（| 分隔，最多 50）。
    - 返回 hits[]：keyword、index、mobile_index、douyin_index、bidword_pcpv/wisepv/kwc/price 等。
    - 服务未开通→unavailable；计费同 data_query。
    """
    try:
        return _fmt(await _client().query(
            "content", "keyword_index", query, top_k=top_k, filters=filters,
        ))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def content_keyword_expand(query: str, top_k: int = 5,
                                 filters: dict | None = None) -> dict[str, Any]:
    """关键词拓词：下拉联想 + 海量长尾。

    - query：种子词。
    - filters.mode：suggest / longtail / both（默认 both）；
      filters.platform：联想平台 baidu/douyin/xiaohongshu 等。
    - 返回 hits[]：keyword、kind(suggest|longtail)、index、bidword_* 等。
    """
    try:
        return _fmt(await _client().query(
            "content", "keyword_expand", query, top_k=top_k, filters=filters,
        ))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def content_wechat_index(query: str, top_k: int = 5) -> dict[str, Any]:
    """查询微信指数热度信号（第三方聚合，非腾讯官方接口）。

    - query：关键词（必填）。
    - 返回 hits[]：keyword、index(若已拍平)、raw、disclaimer。
    """
    try:
        return _fmt(await _client().query(
            "content", "wechat_index", query, top_k=top_k,
        ))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def content_hot_rank(platform: str = "weibo", top_k: int = 50,
                           query: str = "") -> dict[str, Any]:
    """微博 / 抖音热搜榜快照（第三方聚合信号，非平台官方开放接口）。

    - platform：weibo 或 douyin（必填语义，默认 weibo）。
    - query：可选；抖音侧可作附加关键词。
    - 返回 hits[]：rank、title、hot、platform、disclaimer。
    """
    try:
        return _fmt(await _client().query(
            "content", "hot_rank", query,
            top_k=top_k, filters={"platform": platform},
        ))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def enterprise_company_detail(
    keyword: str,
    top_k: int = 5,
    filters: dict | None = None,
) -> dict[str, Any]:
    """企业工商数据（filters.keyword → 工商照面信息，字段对齐上游 Return）。

    keyword 必填（企业名称或统一社会信用代码）。结果入库缓存 30 天，缓存命中不计费。
    """
    f: dict[str, Any] = dict(filters or {})
    f["keyword"] = keyword
    try:
        return _fmt(await _client().query(
            "enterprise", "company_detail", "",
            top_k=top_k, filters=f,
        ))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def enterprise_annual_report(
    keyNo: str,
    year: str | None = None,
    top_k: int = 5,
    filters: dict | None = None,
) -> dict[str, Any]:
    """企业年报信息（filters.keyNo / year → 已发布年报，默认最新约 3 年）。

    keyNo 必填：企业名称或统一社会信用代码（上游参数名 keyNo）。
    year 可选：如 2025。hits 字段名对齐年报开放接口 Return。
    """
    f: dict[str, Any] = dict(filters or {})
    f["keyNo"] = keyNo
    if year is not None:
        f["year"] = year
    try:
        return _fmt(await _client().query(
            "enterprise", "annual_report", "",
            top_k=top_k, filters=f,
        ))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def enterprise_tax_invoice(
    keyWord: str,
    top_k: int = 5,
    filters: dict | None = None,
) -> dict[str, Any]:
    """税号开票信息（filters.keyWord → 纳税人识别号/开户行等，字段对齐上游 Return）。

    keyWord 必填：公司名称（上游参数名 keyWord）。结果入库缓存半年（命中仍计费）。
    """
    f: dict[str, Any] = dict(filters or {})
    f["keyWord"] = keyWord
    try:
        return _fmt(await _client().query(
            "enterprise", "tax_invoice", "",
            top_k=top_k, filters=f,
        ))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def enterprise_shixin_check(
    searchKey: str,
    top_k: int = 5,
    filters: dict | None = None,
) -> dict[str, Any]:
    """失信核查（filters.searchKey → VerifyResult + Data 明细，字段对齐上游 Return）。

    searchKey 必填：查询关键字（如企业名称；上游参数名 searchKey）。
    无失信记录时仍返回 VerifyResult=0 与空 Data。
    """
    f: dict[str, Any] = dict(filters or {})
    f["searchKey"] = searchKey
    try:
        return _fmt(await _client().query(
            "enterprise", "shixin_check", "",
            top_k=top_k, filters=f,
        ))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def enterprise_zhixing_check(
    searchKey: str,
    top_k: int = 5,
    filters: dict | None = None,
) -> dict[str, Any]:
    """被执行人核查（filters.searchKey → VerifyResult + Data 明细，字段对齐上游 Return）。

    searchKey 必填：查询关键字（如企业名称；上游参数名 searchKey）。
    无被执行记录时仍返回 VerifyResult=0 与空 Data。
    """
    f: dict[str, Any] = dict(filters or {})
    f["searchKey"] = searchKey
    try:
        return _fmt(await _client().query(
            "enterprise", "zhixing_check", "",
            top_k=top_k, filters=f,
        ))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def cloud_express(
    no: str,
    com: str,
    top_k: int = 5,
    senderPhone: int | None = None,
    receiverPhone: int | None = None,
) -> dict[str, Any]:
    """快递物流查询（参数对齐上游：com / no / senderPhone / receiverPhone）。

    - no：运单号；com：快递公司编号（如 yd/sf/sto/zto）。
    - 顺丰/中通/跨越须提供 senderPhone 或 receiverPhone 其一（手机后四位）。
    """
    filters: dict[str, Any] = {"com": com, "no": no}
    if senderPhone is not None:
        filters["senderPhone"] = senderPhone
    if receiverPhone is not None:
        filters["receiverPhone"] = receiverPhone
    try:
        return _fmt(await _client().query(
            "cloud", "express", no, top_k=top_k, filters=filters,
        ))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def cloud_express_com(top_k: int = 50) -> dict[str, Any]:
    """快递公司编号对照表（无业务参数）。

    hits 仅含 com（公司名）与 no（公司编号）；cloud_express 的 com 填本接口的 no。
    返回全表，受 top_k 截断。
    """
    try:
        return _fmt(await _client().query("cloud", "express_com", "", top_k=top_k))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def data_query(domain: str, type: str, query: str = "", top_k: int = 5,
                     filters: dict | None = None) -> dict[str, Any]:
    """统一数据查询网关（一个 Key 调所有数据）。

    - domain + type 组合（已上线 live）：
      legal/*、content/*、enterprise/company_detail、enterprise/annual_report、
      enterprise/tax_invoice、enterprise/shixin_check、enterprise/zhixing_check、
      cloud/express、cloud/express_com；规划中：research。
    - query：自然语言检索词；top_k 1-200(默认 5)；filters：按能力的结构化过滤（含 offset 翻页）。
    - 未知 domain/type→code=invalid_capability；planned 域→code=not_implemented(见 list_capabilities)。
    - 完整 domain/type/filters/字段/示例的机器可读真源：用 list_capabilities 运行时自发现。
    """
    try:
        return _fmt(await _client().query(domain, type, query, top_k=top_k, filters=filters))
    except DevnorsDataError as e:
        return _err(e)


@mcp.tool()
async def list_capabilities() -> dict[str, Any]:
    """自发现：拉取服务端 /capabilities.json，返回可调的 domain/type、filters、字段、示例、
    错误码、鉴权与计费口径。Agent 应先调本工具了解「能调什么、怎么调、出错怎么办」，
    再决定后续调用（能力表单一真源在服务端，不在本 MCP 里硬抄）。"""
    url = f"{_base_url()}/capabilities.json"
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(url)
            r.raise_for_status()
            return r.json()
    except Exception as e:  # noqa: BLE001
        return {"error": f"拉取能力清单失败: {e}", "url": url}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
