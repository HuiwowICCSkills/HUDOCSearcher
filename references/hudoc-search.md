# HUDOC 检索实测记录（2026-11-09）

## JSON API

`https://hudoc.echr.coe.int/app/query/results`

参数：`query=contentsitename:ECHR AND "..."`、`select=itemid,docname,appno,doctype,judgementdate,respondent`、`sort=`、`start`、`length`。

直接 `requests` → HTTP 403 Cloudflare（`Just a moment...`）。

## 无头回退

`scripts/hudoc_headless.py` 使用 DrissionPage + Chrome：

1. 打开 `https://hudoc.echr.coe.int/eng`，等待挑战通过；
2. 在页面上下文执行 `fetch(apiUrl, headers: Accept/Referer/X-Requested-With)`；
3. 验证 `status=200` 且 JSON 包含 `resultcount` / `results`。

实测 `state immunity --limit 2` → `status=ok`、`total=193`、2 条，`transport=headless-chrome-page-fetch`，约 18 秒。

## 文档页

`fetch https://hudoc.echr.coe.int/eng?i=001-140005` → `status=ok`、`text_characters=194351`，使用无头渲染。

## 解析

- `results[].columns` 可能是 dict 或 list；取 `itemid`、`docname`、`appno`、`doctype`、`judgementdate`、`respondent`
- 文档 URL：`https://hudoc.echr.coe.int/eng?i=<itemid>`

## 边界

- HUDOC 可能不签发 `cf_clearance`；以 `HTTP 200 + 合法 JSON + resultcount/results` 为成功判据，不只依赖 Cookie。
- 搜索结果不是判决正文；文档页文本可能含导航、脚注和多语言版本。

## 高级检索字段（2026-11-12 浏览器核对）

HUDOC 的 Advanced Search 面板和 JSON API 使用同一套字段名。以下条件已在当前会话中逐个提交并返回 `resultcount` 验证：

| 字段 | 示例 | 实测结果数 |
| --- | --- | ---: |
| `documentcollectionid2` | `"GRANDCHAMBER"` | 5,728 |
| `documentcollectionid2` | `"JUDGMENTS"` | 103,726 |
| `respondent` | `"TUR"` | 27,574 |
| `article` | `3` | 118,541 |
| `importance` | `1` | 14,606 |
| `judgementdate` | `[2015-01-01 TO 2020-12-31]` | 18,874 |
| `violation` | `6` | 43,969 |
| `nonviolation` | `6` | 5,547 |
| `docname` | `"Jones"` | 55 |
| `appno` | `"34356/06"` | 28 |
| `doctype` | `"HEJUD"` / `"HEDEC"` | 29,417 / 33,661 |

组合方式：`contentsitename:ECHR AND "关键词" AND (documentcollectionid2:"GRANDCHAMBER" OR documentcollectionid2:"CHAMBER") AND article:"6" AND judgementdate:[2010-01-01 TO 2020-12-31]`。文档集合多值用 OR，其他条件用 AND。

界面上还有 `languageisocode`、`separateopinion`、`issue`、`bodyprocedure`、`bodyfacts`、`bodycomplaints`、`bodylaw`、`bodyreasons` 等字段；这些字段本次未纳入 CLI，需要时按同一语法直接扩展 `build_query()`，不要凭空猜字段名。
