# HUDOCSearcher 部署指引

独立检索欧洲人权法院 HUDOC，并读取 `/eng?i=` 文档页。只访问 `hudoc.echr.coe.int`。

仓库：<https://github.com/GDUFSICCSkills/HUDOCSearcher>（私有）。

## 1. 环境

Python 3.10+，依赖 `requests`、`beautifulsoup4`、`pypdf`、`DrissionPage`；无头回退需要 Chrome/Chromium/Edge。

## 2. 安装

```powershell
git clone https://github.com/GDUFSICCSkills/HUDOCSearcher.git "$env:USERPROFILE\.codex\skills\HUDOCSearcher"
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
