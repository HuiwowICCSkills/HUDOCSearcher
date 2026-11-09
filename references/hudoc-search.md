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
