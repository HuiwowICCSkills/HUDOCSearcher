# HUDOCSearcher 部署指引

独立检索欧洲人权法院 HUDOC，并读取 `/eng?i=` 文档页。只访问 `hudoc.echr.coe.int`。

仓库：<https://github.com/HuiwowICCSkills/HUDOCSearcher>（公开）。

## 1. 环境

Python 3.10+，依赖 `requests`、`beautifulsoup4`、`pypdf`、`DrissionPage`；无头回退需要 Chrome/Chromium/Edge。

## 2. 安装

```powershell
git clone https://github.com/HuiwowICCSkills/HUDOCSearcher.git "$env:USERPROFILE\.codex\skills\HUDOCSearcher"
python -m pip install -r "$env:USERPROFILE\.codex\skills\HUDOCSearcher\requirements.txt"
```

## 3. 自检

```powershell
& "$env:USERPROFILE\.codex\skills\HUDOCSearcher\run.ps1" doctor
```

`doctor` 检查 DrissionPage 和无头浏览器，并探测 HUDOC API；直接 API 被 403 时，`headless_available=true` 仍可工作。

## 4. 使用

```powershell
$hudoc = "$env:USERPROFILE\.codex\skills\HUDOCSearcher\run.ps1"
& $hudoc search 'state immunity' --limit 10 --out './hudoc.json'
& $hudoc fetch 'https://hudoc.echr.coe.int/eng?i=001-140005' --out './doc.json' --text-out './doc.txt'
```

## 5. 排错

| 现象 | 处理 |
| --- | --- |
| 直接 API 403，但 `transport=headless-chrome-page-fetch` | 回退成功；看 `warnings` 中的直接失败原因 |
| `DrissionPage is required` | 安装 `requirements.txt` |
| 无头浏览器超时 | 检查 Chrome 路径，设置 `CHROME_PATH`；提高 `--timeout` |
| 文档页文本很长 | 包含导航/脚注/多语言版本；按 itemid 和段号核对 |

## 6. 边界

本 skill 只做 HUDOC/ECHR；不检索 ICJ、ICC 或联合国文件。HUDOC 搜索元数据不是判决全文，引用时读取 `/eng?i=` 页面并核对申请号、日期和文书类型。

## 实测效果（2026-11-09）

以下命令与结果来自本机 `~/.codex/skills/HUDOCSearcher` 的实网运行；检索日期 2026-11-09（Asia/Shanghai），输出为该次运行实际返回的 JSON 报告。

```powershell
$hudoc = "$env:USERPROFILE\.codex\skills\HUDOCSearcher\run.ps1"
& $hudoc search 'Al-Adsani' --limit 5
```

- 状态：`ok`；服务端报告 `total = 1057`（ECHR 集合命中数）；本次返回 5 条。
- 传输：`transport = headless-chrome-page-fetch`。直接调用 HUDOC API 首次返回 HTTP 403（`warnings` 原文：`direct HUDOC API failed; using headless Chrome: HTTP 403: https://hudoc.echr.coe.int/app/query/results?query=contentsitename%3AECHR+AND+%22Al-Adsani%22&select=itemid%2Cdocname%2Cappno%2Cdoctype%2Cjudgementdate%2Crespondent&sort=&start=0&length=5`），改由无头浏览器取回同一查询的结果页。
- `scope` 原文：`HUDOC search metadata for the ECHR collection`。
- 代表性结果：

| 题名 | 类型 / 日期 | 申请号 / 被诉国 | 链接 |
| --- | --- | --- | --- |
| AFFAIRE AL-ADSANI c. ROYAUME-UNI | HFJUD；21/11/2001 00:00:00 | 35763/97、GBR | https://hudoc.echr.coe.int/eng?i=001-64442 |
| Audience AL ADSANI et  FOGARTY c. Royaume-Uni 15.11.2000 | PR；— | — | https://hudoc.echr.coe.int/eng?i=003-68936-69404 |
| Hearing Al-Adsani & Fogarty v. United Kingdom 15.11.00 | PR；— | — | https://hudoc.echr.coe.int/eng?i=003-68104-68572 |
| AL-ADSANI v. THE UNITED KINGDOM | HEDEC；— | 35763/97、GBR | https://hudoc.echr.coe.int/eng?i=001-5185 |
| Al-Adsani c. Royaume-Uni [GC] | CLINF；— | 35763/97、GBR | https://hudoc.echr.coe.int/eng?i=002-6221 |

> 说明：以上是**检索元数据，不是判决全文**。每条 `result_type = retrieved_metadata`、`content_scope = HUDOC search metadata, not the judgment text`、`access = search metadata; document text must be fetched separately`。搜索结果里同一案件混有多种语言与不同阶段/类型的文书（法语判决 `HFJUD`、2000 年 11 月 15 日庭审的英/法文记录 `PR`、`HEDEC`、大法庭资料 `CLINF`），不能据题名合并成"一份判决"。`date` 字段本次只有第一条有值，其余为空，故留空不补；`total=1057` 是包含新闻稿、决定等全部 ECHR 文书类型的命中数，不是判决数。引用前须用 `fetch` 打开 `/eng?i=` 页面核对申请号、日期、文书类型与正文。
