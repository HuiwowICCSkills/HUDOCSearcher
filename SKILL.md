---
name: HUDOCSearcher
description: 独立检索欧洲人权法院 HUDOC 数据库，返回案件名、申请号、文书类型、裁判日期和 itemid；支持读取 HUDOC 文档页正文，并在 Cloudflare 拦截时使用无头 Chrome 页面内回退。
---

# HUDOCSearcher

> **`<skill-dir>`** = 本 SKILL.md 所在目录。核心脚本为 `<skill-dir>/scripts/hudoc_search.py`；Windows 用 `<skill-dir>/run.ps1`，macOS/Linux 用 `<skill-dir>/run.sh`。部署与排错见 [README.md](README.md)。

这个 skill 只做 `hudoc.echr.coe.int` 一个站点：

- `search`：调用 HUDOC JSON API，查询 `contentsitename:ECHR` 集合；
- `fetch`：按 `/eng?i=<itemid>` 文档页读取正文；
- `doctor`：检查 Python、DrissionPage 和无头浏览器路径，并探测 HUDOC API。

HUDOC 的 JSON API 和文档页经常被 Cloudflare 403/挑战页拦截。适配器先走直接 HTTP；失败时用 DrissionPage 启动无头 Chrome，在 HUDOC 页面上下文中重新执行同一 `fetch` 请求（保留 `Accept`、`Referer`、`X-Requested-With`），或渲染 `/eng?i=` 文档页。这个回退不需要 `gdufs-auth-session`，也不保存任何账号凭据。

## 命令

```powershell
# 检索 HUDOC
& '<skill-dir>/run.ps1' search 'state immunity' --limit 10 --out './hudoc-search.json'

# 高级检索：大法庭 + 第 6 条 + 重要性 1 + 日期范围
& '<skill-dir>/run.ps1' search 'fair trial' --document-collection GRANDCHAMBER --article 6 --importance 1 --date-from 2015-01-01 --date-to 2020-12-31 --limit 5

# 按被告国、文书类型和申请号收窄
& '<skill-dir>/run.ps1' search 'effective remedy' --respondent TUR --doctype HEJUD --appno '34356/06' --limit 5

# 读取一份判决/决定页面
& '<skill-dir>/run.ps1' fetch 'https://hudoc.echr.coe.int/eng?i=001-140005' --out './hudoc-doc.json' --text-out './hudoc-doc.txt'

# 部署自检
& '<skill-dir>/run.ps1' doctor
```

通用参数：`--out`、`--cache`、`--cache-ttl`、`--offline`、`--timeout`。`search` 另有 `--limit`（1..50）、`--offset`；`fetch` 另有 `--text-out`、`--max-mb`。

## 结果边界

- `search` 返回 HUDOC 检索元数据：`docname`、`appno`、`doctype`、`judgementdate`、`respondent`、`itemid`；不是判决正文。`total` 是 HUDOC 的 `resultcount`。
- 高级字段会写入报告的 `query_expression` 和 `filters`：`--document-collection` 可重复（多值之间 OR），其余条件与关键词之间全部 AND；`--date-from`/`--date-to` 映射到 `judgementdate:[… TO …]`。这些字段名来自 HUDOC 自身 Advanced Search 的查询语法，不是本技能另造的标准。
- `fetch` 只接受 `https://hudoc.echr.coe.int/` URL；文本可能包含导航、脚注和多种语言版本，引用前核对 itemid、申请号、日期和文书类型。
- 直接 API 被 403 时，报告 `transport=headless-chrome-page-fetch` 并在 `warnings` 保留直接失败原因；这表示回退成功，不是“没有资料”。
- HUDOC 可能不签发 `cf_clearance`；回退以 `HTTP 200 + 合法 JSON + resultcount/results` 或渲染后的有效 HTML 为成功判据，不能只凭 Cookie 判断。
- 搜索结果是 ECHR 集合，不等于所有欧洲人权公约相关材料；引用时区分判决、决定、新闻稿和摘要。

## 参考

- 2026-11-09 实测：HUDOC JSON 字段、Cloudflare 403、DrissionPage 页面内 fetch 与文档页读取：[references/hudoc-search.md](references/hudoc-search.md)
- 部署、环境与排错：[README.md](README.md)
