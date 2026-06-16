---
name: stall-replenishment-tool
description: "Maintain the clothing-stall replenishment HTML tool — warehouse-only inventory display with single embedded data source, GitHub Pages deployment via API (bypass GFW), HTML batch-editing."
version: 3.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [stall, replenishment, inventory, html-tool, github-pages, gfw]
    related_skills: [inv-engine, github-auth]
---

# Stall Replenishment Tool (v3.0)

The user (陈裕盛) runs a family clothing stall (内衣裤袜) in Singapore.

**GitHub Pages:** `https://yushengchen519-cmd.github.io/stall-replenishment-tool/`
**Repo:** `https://github.com/yushengchen519-cmd/stall-replenishment-tool`
**Local:** `C:\Users\28073\Desktop\补货工具\index.html`

## v3.0: Single Source of Truth Architecture

**The entire data pipeline is now a single embedded `inventory` array.** No SYNC_DATA, no applySyncData, no migration code, no external sync files. One array to rule them all.

### Architecture (final)

```
inventory = [
  {code, category, brand, name, size, color, location, wh, wh_safety},
  ...
];
```

`wh` and `wh_safety` are the **only** stock fields. No `current_stock`, `sold`, `safety`, `suggested`, `status`, `total_in` — all removed. The inventory array is the single source of truth, embedded directly in the HTML.

### Init flow (v3.0 — ZERO localStorage)

```
1. inventory defined with wh/wh_safety directly from DB (embedded by CLI)
2. render() — reads inventory array directly, no persistence layer
```

**No localStorage at all.** The user explicitly demanded removal of all caching. The embedded `inventory` array is the sole data source — each page load gets fresh data. Manual edits on the page don't persist across refreshes (by design — CLI is the write path).

### Pitfall: NEVER reintroduce localStorage

The old v2 architecture had `saveData()`/`loadData()`/`STORAGE_KEY`/`applySyncData()` — a web of caching that caused stale data bugs through multiple debugging sessions. The user explicitly said: "我不是让你把旧的内容都删掉吗？你把这些缓存之类的也都清掉吧". ALL localStorage code was removed. Do not add it back.

## What Was Removed (v2 → v3)

| Removed | Why |
|---------|-----|
| `var SYNC_DATA = [...]` | Now part of inventory array |
| `applySyncData()` function | No separate sync data to apply |
| `current_stock`, `sold`, `safety`, `suggested`, `status` fields | Old migration-format garbage |
| Migration code (shelf/wh computation) | wh is now directly embedded |
| `inventory_sync.js` file | No external sync — all embedded |
| `embed_sync.py` script | inv_cli.py does it directly via `embed_latest_into_html()` |
| `STORAGE_KEY`, `saveData()`, `loadData()` | **ALL localStorage removed** — user explicitly demanded zero caching |
| `exportDataTSV()` button | Function was removed, button was broken |

## Companion: inv-engine

CLI engine (`inv_cli.py`) processes WeChat voice instructions → SQLite → auto-embeds latest data into `index.html` → auto-uploads to GitHub.

After every CLI operation (补货/进货), `inv_cli.py` calls:
1. `embed_latest_into_html()` — reads DB, builds clean inventory array, replaces it in index.html
2. `upload_html_to_github()` — uploads updated index.html via GitHub API

See `skill:inv-engine` for CLI details.

## Deployment: GitHub API (bypass GFW)

**Branch: `master`**. Always verify with `gh api repos/<owner>/<repo> --jq '.default_branch'`.

### Upload via gh CLI (RECOMMENDED — handles large files)

```bash
cd /path/to/workdir
SHA=$(gh api repos/OWNER/REPO/contents/index.html --jq '.sha')
B64=$(base64 -w0 index.html)
echo "{\"message\":\"commit msg\",\"content\":\"$B64\",\"sha\":\"$SHA\",\"branch\":\"master\"}" > /tmp/gh_body.json
gh api --method PUT repos/OWNER/REPO/contents/index.html --input /tmp/gh_body.json
```

**Pitfall:** `gh api -f content="$B64"` fails with "Argument list too long" for files >~10KB. Always write to temp file with `--input`.

### Python fallback (inv_cli.py uses this)

```python
import subprocess, json, base64, urllib.request
token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
# ... standard API upload with retry
```

## HTML Modification Pattern

**ALWAYS use Python scripts for multi-line block replacements.** The `patch()` tool is for single-line or short targeted edits. When removing multi-line blocks (e.g., the DATA PERSISTENCE section with localStorage functions), `patch()` can misalign and produce:
- Duplicate functions
- Orphan code fragments
- Broken JavaScript syntax

```python
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()
html = html.replace('exact old block', 'exact new block')
with open(path, 'w', encoding='utf-8') as f:
    f.write(html)
```

**Pitfall from this session:** Using `patch()` to remove a 30-line block produced a corrupted file with duplicate `resetData()` and orphan `exportDataTSV` fragments. Required a Python rebuild script to recover. For any replacement spanning >5 lines, write a Python script.

## GitHub Pages Verification (POST-DEPLOY)

**CRITICAL: curl and CLI HTTP tools are BLOCKED from China to GitHub Pages.** Always use bb-browser.

```bash
bb-browser open "https://yushengchen519-cmd.github.io/stall-replenishment-tool/?v=$(date +%s)"
sleep 3
# Check rendered rows
bb-browser eval "Array.from(document.querySelectorAll('tbody tr')).filter(function(tr){return tr.textContent.includes('906')}).map(function(tr){return Array.from(tr.cells).map(function(td){return td.textContent.trim()}).filter(function(t){return t}).join(' | ')})"
# Check for errors
bb-browser errors
bb-browser close
```

## Data Persistence

**None.** No localStorage, no cookies, no IndexedDB. The embedded `inventory` array IS the data. Each page load = fresh snapshot from DB. Reset = page reload.

All writes go through `inv_cli.py` → SQLite → `embed_latest_into_html()` → GitHub Pages.

## Terminology (user-enforced)

- **仓库** — warehouse stock (唯一追踪的库存)
- **补货** — warehouse decreases (moved to stall, stall not tracked)
- **进货** — warehouse increases (from supplier, costs tracked)
- **Sim/Smile** — brand "beyond" model "Sim" = "Smile"

## Inventory Alert (Cron)

Cron job runs `inventory_alert.py` daily at 8am:
- Scans all SKUs for `wh < wh_safety`
- Silent when all stocked
- Alerts with suggested restock quantities when low

## Excel 库存清单 (v3.0 新增)

`export_excel.py` 生成 `库存清单.xlsx`，3 个工作表:
- **库存明细** — 29 SKU 全字段 + 库存金额(=wh×cost)
- **品类汇总** — 按内衣/内裤/袜子/裤袜统计SKU数/总库存/低于安全线/库存总值
- **待补货清单** — `wh < wh_safety` 的SKU，按建议进货量降序

内置验证: SKU数=29, 明细总wh=汇总总wh, 品类合计=总wh

每次 CLI 操作后自动运行 `export_excel.py` → 上传 GitHub。

### 当前文件清单 (仅7个)

```
桌面\补货工具\
├── index.html          # 页面 (inventory数组内嵌)
├── inventory.db        # SQLite 29 SKU
├── 库存清单.xlsx        # Excel 3页
├── inv_cli.py          # CLI入口+验证+自动同步
├── inv_engine.py        # 核心解析引擎
├── export_excel.py      # Excel生成 (openpyxl)
└── build_db.py          # 从零建库脚本
```

所有其他文件已删除 (交互版.html, sync.js/json, fix_html.py, README.md, 工作汇报.html, 模板.xlsx, 使用指南.docx, ai-demo-video/)

### CLI 每次操作自动执行的完整流程

```python
# inv_cli.py 执行顺序:
1. snapshot_db()           # 操作前快照
2. process_message(msg)    # inv_engine 执行
3. snapshot_db()           # 操作后快照
4. verify_operation()      # 验证变更/总数/一致性 (🟢/🔴)
5. embed_latest_into_html() # DB→inventory数组→替换index.html
6. export_excel.py         # DB→库存清单.xlsx (subprocess)
7. upload_file_to_github('index.html')
8. upload_file_to_github('库存清单.xlsx')
```

### CLI 调用方式

```bash
cd "/c/Users/28073/Desktop/补货工具" && \
/c/Users/28073/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe \
  inv_cli.py "指令文本"
```

### 品牌/价格速查

| Code | 品牌 | 名称 | 尺码 | 颜色 | 单价(SGD) |
|------|------|------|------|------|:--:|
| BR-001 | Triumph | 无钢圈舒适文胸 | 34B,34C,36B | 黑色,肤色 | 10.50 |
| BR-004 | Wacoal | 聚拢调整型文胸 | 34B,36C | 黑色,肤色 | 14 |
| BR-006 | 华为 | 906 | 2XL | 白,粉,肉,黑 | 5 |
| UN-001 | Byford | 纯棉平角内裤(男) | M,L,XL | 灰色,黑色 | 4.50 |
| UN-004 | Renoma | 冰丝三角内裤(男) | M,L | 蓝色,黑色 | 3.20 |
| UN-006 | Triumph | 蕾丝三角内裤(女) | M,L | 粉色,肤色 | 3.80 |
| UN-008 | beyond | Sim/Smile | M,XL | 灰,肉,黑 | 6 |
| SK-001 | Goldlion | 商务棉袜3双装 | 均码 | 黑色,深灰 | 2.50 |
| SK-003 | Puma | 运动短袜(男) | 均码 | 白色 | 3 |
| SK-004 | Puma | 运动短袜(女) | 均码 | 白色 | 3 |
| SK-005 | Happy Socks | 彩色棉袜(女) | 均码 | 花色 | 3.50 |
| ST-001 | Gunze | 发热保暖连裤袜 | M-L,L-LL | 黑色,深灰 | 8 |
| ST-003 | Atsugi | 压力美腿连裤袜 | M-L | 肤色 | 10 |

### 指令歧义注意事项

- "34B黑色" vs "34C黑色" 冲突 → 用完整名称 "Triumph 无钢圈舒适文胸 34B 黑色 5件"
- "XL灰5肉5" 有时被解析为 M → 分开执行: "进 Sim XL 灰5肉5"
- Sim/Smile = UN-008 beyond
