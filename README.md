# Devnors Data MCP Server

[简体中文](README.zh-CN.md) | English

Use Devnors Data in MCP clients such as Codex, Claude Desktop, Cursor, WorkBuddy,
and other AI assistant tools.

Devnors Data MCP helps your assistant discover available capabilities, inspect
required parameters, and call legal / enterprise / content / research / express
APIs with your Devnors Data API Key.

## Supported Clients

You can use Devnors Data MCP with any MCP-compatible client that supports remote
HTTP or local stdio servers, including:

- Codex
- Claude Desktop
- Cursor
- WorkBuddy
- Other MCP-compatible AI assistants

For Codex, add Devnors Data as a remote MCP server and use the Remote HTTP URL
and Authorization header below.

## Quick Start

### Remote HTTP

Remote HTTP is the recommended way to use Devnors Data MCP. No local Python
install is required.

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

Create an API Key in the
[developer console](https://data.devnors.com/console).

### Local stdio

You can also run the MCP server locally after `pip install devnors-mcp`.

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

On Windows, client PATH often cannot find `devnors-mcp`. Prefer the `python -m`
form above, or set `command` to an absolute Python path.

## Token

Use your Devnors Data API Key in one of these ways:

```text
Authorization: Bearer devnors_sk_live_xxx
```

or, for local stdio:

```text
DEVNORS_API_KEY=devnors_sk_live_xxx
```

`Bearer …` is the recommended Authorization format.

Optional private / self-hosted base URL for local stdio:

```text
DEVNORS_DATA_BASE_URL=https://data.devnors.com
```

## Things You Can Ask

Ask your MCP client naturally:

```text
List available Devnors Data capabilities and required filters.
```

More examples:

```text
Search Chinese legal judgment documents for private lending interest disputes.
```

```text
Look up current PRC law articles about contract termination.
```

```text
Get company registration details for this credit code.
```

```text
Check whether this company is on the dishonest judgment debtor list.
```

```text
Suggest related keywords for "lawyer" on Baidu.
```

```text
Track this express parcel with company code and tracking number.
```

```text
Search academic papers titled Attention Is All You Need.
```

```text
Find scholars named Andrew Ng and open the top profile detail.
```

```text
The API returned insufficient_balance. What should I do next?
```

```text
The API returned rate_limited. Help me retry safely.
```

The assistant can call `list_capabilities` first, explain required parameters,
invoke the selected tool after you provide values, and help interpret common
error codes.

## Tools

| Tool | Description |
|---|---|
| `list_capabilities` | Discover live domain/type, filters, fields, examples, errors |
| `legal_case_search` | Legal judgment documents |
| `legal_law_search` | Current law articles |
| `content_keyword_index` | Keyword traffic index (incl. SEM) |
| `content_suggest_list` | Suggest / autocomplete keywords (multi-platform) |
| `content_keyword_word` | Long-tail keyword mining |
| `content_bidword` | Website bidword mining |
| `content_wechat_index_v2` | WeChat Index v2 (time series; billed per keyword) |
| `enterprise_company_detail_v2` | Company registration details |
| `enterprise_annual_report_list` | Annual report list |
| `enterprise_annual_report_detail` | Annual report detail |
| `enterprise_account_open` | Bank account opening info |
| `enterprise_company_tag` | Company tags |
| `enterprise_same_legal_company` | Companies with the same legal representative |
| `enterprise_key_person` | Key persons |
| `enterprise_shareholder` | Shareholders |
| `enterprise_branch_org` | Branch organizations |
| `enterprise_industrial_commercial_change` | Industrial & commercial changes |
| `enterprise_taxpayer_basic` | Taxpayer basic info |
| `enterprise_tax_credit_level` | Tax credit level |
| `enterprise_tax_illegal` | Tax illegal records |
| `enterprise_tax_illegal_major` | Major tax illegal list |
| `enterprise_tax_illegal_major_detail` | Major tax illegal detail |
| `enterprise_operation_except` | Operation exception records |
| `enterprise_admin_punishment` | Administrative punishments |
| `enterprise_judgment_list` | Judgment document list |
| `enterprise_court_notice_list` | Court notice list |
| `enterprise_court_trial_list` | Court trial notice list |
| `enterprise_cases_info_list` | Case filing info list |
| `enterprise_termination_case_list` | Termination case list |
| `enterprise_serious_illegal` | Serious illegal records |
| `enterprise_exec_person` | Enforcement debtor |
| `enterprise_breach_of_trust` | Dishonest judgment debtor |
| `enterprise_listed_company` | Listed company info |
| `enterprise_listed_company_neeq` | Listed company info (NEEQ) |
| `cloud_express` | Express tracking |
| `cloud_express_com` | Express company code table |
| `cloud_web_search` | Web search |
| `cloud_invoice_ocr` | Invoice OCR |
| `research_paper_search` | Academic paper search |
| `research_patent_search` | Patent search |
| `research_journal_search` | Journal / conference search |
| `research_paper_detail` | Paper detail |
| `research_patent_detail` | Patent detail |
| `research_journal_detail` | Journal / conference detail |
| `research_scholar_search` | Scholar search |
| `research_scholar_detail` | Scholar detail |
| `data_query` | Unified entry for any domain + type |

## Billing and Errors

Successful calls return `units` and `request_id`. Failures return structured
fields so the agent can self-correct:

| `code` | Meaning | `retryable` |
|---|---|---|
| `unauthorized` | Missing / invalid key | no |
| `insufficient_balance` | Need top-up at https://data.devnors.com/console/recharge | no |
| `rate_limited` | Rate limited | yes |
| `invalid_capability` | Bad domain/type | no |
| `not_implemented` | Planned capability | no |
| `unavailable` / `upstream_error` | Temporary failure | yes |

Retryable `429` / `5xx` errors are retried by the underlying Python SDK with
bounded backoff. The MCP layer does not stack extra retries.

## Related

- Python SDK: [devnors-data-python](https://github.com/DevnorsAI/devnors-data-python)
- Docs: [https://data.devnors.com/docs](https://data.devnors.com/docs)
- Product site: [https://data.devnors.com](https://data.devnors.com)

## License

MIT
