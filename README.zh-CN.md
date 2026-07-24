# Devnors Data MCP Server

简体中文 | [English](README.md)

在 Codex、Claude Desktop、Cursor、WorkBuddy 等 MCP 客户端中使用 Devnors Data。

Devnors Data MCP 可以帮助你的 AI 助手发现可用能力、查看所需参数，并用你的
API Key 调用法律 / 企业 / 内容 / 快递等接口。

## 支持的客户端

只要你的 AI 客户端支持 MCP，就可以使用 Devnors Data MCP。常见客户端包括：

- Codex
- Claude Desktop
- Cursor
- WorkBuddy
- 其他支持 MCP 的 AI 助手

如果你使用 Codex，可以把 Devnors Data 添加为远程 MCP 服务，并使用下面的远程
HTTP 地址和 Authorization 请求头。

## 快速接入

### 远程 HTTP

推荐使用远程 HTTP 方式接入，无需本机安装 Python。

```json
{
  "mcpServers": {
    "devnors-data": {
      "url": "https://data.devnors.com/mcp",
      "headers": {
        "Authorization": "Bearer devnors_sk_live_xxx"
      }
    }
  }
}
```

请先在 [开发者控制台](https://data.devnors.com/console) 创建 API Key。

### 本地 stdio

也可以先 `pip install devnors-mcp`，再在本地运行：

```json
{
  "mcpServers": {
    "devnors-data": {
      "command": "python",
      "args": ["-m", "devnors_mcp.server"],
      "env": {
        "DEVNORS_API_KEY": "devnors_sk_live_xxx"
      }
    }
  }
}
```

Windows 上客户端 PATH 经常找不到 `devnors-mcp`，请优先使用上面的 `python -m`
写法，或把 `command` 写成 Python 绝对路径。

## Token

使用你的 Devnors Data API Key：

```text
Authorization: Bearer devnors_sk_live_xxx
```

本地 stdio 也可以使用：

```text
DEVNORS_API_KEY=devnors_sk_live_xxx
```

推荐使用 `Bearer …` 格式。

本地 stdio 可选私有化地址：

```text
DEVNORS_DATA_BASE_URL=https://data.devnors.com
```

## 使用示例

你可以直接对 MCP 客户端说：

```text
列出 Devnors Data 现在有哪些能力，以及各自需要什么参数。
```

更多示例：

```text
帮我查民间借贷利息相关的裁判文书。
```

```text
查一下合同解除相关的现行法条。
```

```text
用统一社会信用代码查这家公司的工商信息。
```

```text
核查这家公司是否被列入失信被执行人。
```

```text
看看今天抖音热搜。
```

```text
用快递公司编号和运单号查物流。
```

```text
接口返回 insufficient_balance，接下来该怎么做？
```

```text
接口返回 rate_limited，帮我安全重试。
```

AI 助手可以先调用 `list_capabilities`，说明必填参数，在你提供参数后调用对应工具，
并帮助解释常见错误码。

## 提供的工具

| 工具 | 说明 |
|---|---|
| `list_capabilities` | 自发现：domain/type、filters、字段、示例、错误码 |
| `legal_case_search` | 裁判文书 |
| `legal_law_search` | 法律法规条文 |
| `content_keyword_index` | 关键词流量指数 |
| `content_keyword_expand` | 关键词拓词 |
| `content_wechat_index` | 微信指数 |
| `content_hot_rank` | 微博 / 抖音热搜榜 |
| `enterprise_company_detail` | 企业工商数据 |
| `enterprise_annual_report` | 企业年报信息 |
| `enterprise_tax_invoice` | 税号开票信息 |
| `enterprise_shixin_check` | 失信核查 |
| `enterprise_zhixing_check` | 被执行人核查 |
| `cloud_express` | 快递物流查询 |
| `data_query` | 统一入口：任意 domain + type |

## 计费与错误

成功返回含 `units` 与 `request_id`。失败返回结构化字段，便于 Agent 自纠：

| `code` | 含义 | `retryable` |
|---|---|---|
| `unauthorized` | Key 无效 / 缺失 | 否 |
| `insufficient_balance` | 余额不足 | 否 |
| `rate_limited` | 触发限流 | 是 |
| `invalid_capability` | domain/type 无效 | 否 |
| `not_implemented` | 能力规划中 | 否 |
| `unavailable` / `upstream_error` | 服务暂不可用 | 是 |

可重试的 `429` / `5xx` 由底层 Python SDK 做有界退避；MCP 层不再叠加重试。

## 相关

- Python SDK：[devnors-data-python](https://github.com/DevnorsAI/devnors-data-python)
- 文档：[https://data.devnors.com/docs](https://data.devnors.com/docs)
- 产品站：[https://data.devnors.com](https://data.devnors.com)

## 许可证

MIT
