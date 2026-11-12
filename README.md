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

## 实测效果（2026-11-12）

以下命令与结果来自本机 `~/.codex/skills/HUDOCSearcher` 的实网运行；检索日期 2026-11-12（Asia/Shanghai），输出为该次运行实际返回的 JSON 报告。

```powershell
$hudoc = "$env:USERPROFILE\.codex\skills\HUDOCSearcher\run.ps1"
& $hudoc search 'state immunity' --respondent GBR --date-from 2010-01-01 --date-to 2020-12-31 --limit 5
```

- 状态：`ok`；服务端报告 `total = 25`；本次返回 5 条。
- 高级过滤：`respondent:"GBR"` 与 `judgementdate:[2010-01-01 TO 2020-12-31]` 已进入 HUDOC 查询表达式；完整 `query_expression` 见 JSON。
- 传输：`headless-chrome-page-fetch`。直接调用 HUDOC API 仍可能返回 HTTP 403；回退成功只证明本次检索页可取，不等于 API 直连正常。
- 代表性结果：

| 题名 | 类型 / 日期 | 申请号 / 被诉国 | 链接 |
| --- | --- | --- | --- |
| CASE OF JONES AND OTHERS v. THE UNITED KINGDOM | HEJUD；14/01/2014 00:00:00 | 34356/06;40528/06 / GBR | https://hudoc.echr.coe.int/eng?i=001-140005 |
| CASE OF JONES AND OTHERS v. THE UNITED KINGDOM - [Romanian Translation] by the COE Human Rights Trust Fund | HJUDRUM；14/01/2014 00:00:00 | 34356/06;40528/06 / GBR | https://hudoc.echr.coe.int/eng?i=001-146364 |
| CASE OF JONES AND OTHERS v. THE UNITED KINGDOM - [Albanian Translation] by the COE Human Rights Trust Fund | HJUDALB；14/01/2014 00:00:00 | 34356/06;40528/06 / GBR | https://hudoc.echr.coe.int/eng?i=001-149086 |

> 说明：以上是**检索元数据，不是判决全文**。`total=25` 是该过滤条件下的 HUDOC 记录数，不是判决案件数；同一判决的不同语言版本会各占一条记录。引用前必须用 `fetch` 打开 `/eng?i=` 页面核对 itemid、申请号、日期、文书类型和正文。
