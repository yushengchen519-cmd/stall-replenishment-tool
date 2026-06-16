# Self-Contained HTML Generation Pattern

## Problem

When deploying an interactive HTML tool to GitHub Pages, external JS dependencies (like `inventory_sync.js`) can work but add risk:
- Browser cache of redirect pages
- Script load timing
- First-visit localStorage emptiness

## Solution

Embed the full SQLite database state directly into the HTML's `var inventory = [...]` array. Keep the external sync script as an optional overlay.

## Script Template

```python
import sqlite3, json, re

DB_PATH = r"C:\Users\28073\Desktop\补货工具\inventory.db"
HTML_PATH = r"C:\Users\28073\Desktop\补货工具\补货工具_交互版.html"

# 1. Read all data from SQLite
db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
rows = db.execute("""
    SELECT code, category, brand, name, size, color, location, wh, wh_safety, supplier, cost
    FROM inventory ORDER BY brand, name, size, color
""").fetchall()
db.close()

# 2. Generate inventory array
items = []
for r in rows:
    items.append(json.dumps({
        "code": r["code"], "category": r["category"], "brand": r["brand"],
        "name": r["name"], "size": r["size"], "color": r["color"],
        "location": r["location"] or "", "wh": r["wh"], "wh_safety": r["wh_safety"],
        "supplier": r["supplier"] or "", "cost": r["cost"] or 0
    }, ensure_ascii=False))

new_inventory = "var inventory = [\n  " + ",\n  ".join(items) + "\n];"

# 3. Replace in HTML
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

old_start = html.find("var inventory = [")
end_marker = html.find("// ===== DATA PERSISTENCE", old_start)
old_block = html[old_start:end_marker]
html = html.replace(old_block, new_inventory + "\n\n")

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)
```

## Data Flow

```
SQLite DB → inv_cli.py → inventory_sync.js (SYNC_DATA)
                        → self_contain.py → index.html (embedded inventory)
                                    ↓
                        GitHub Pages serves index.html
                                    ↓
                        loadFromSyncFile():
                          1. SYNC_DATA? → override wh/wh_safety
                          2. localStorage? → restore session edits
                          3. embedded data → fallback default
```

## Key Load Function

```javascript
function loadFromSyncFile(callback) {
  if (typeof SYNC_DATA !== 'undefined' && SYNC_DATA.length > 0) {
    applySyncData(SYNC_DATA);  // override with latest CLI updates
    saveData();                // persist to localStorage
    if (callback) callback(true);
  } else {
    var hasLocal = loadData(); // use localStorage session edits
    if (callback) callback(hasLocal);
  }
}
```

Priority: SYNC_DATA > localStorage > embedded defaults
