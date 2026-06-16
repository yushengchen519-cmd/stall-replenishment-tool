"""Step 1: Extract inventory from HTML → SQLite database (v2.0: warehouse only)"""
import re, json, sqlite3, os

html_path = r"C:\Users\28073\Desktop\补货工具\补货工具_交互版.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Extract inventory
m = re.search(r'var inventory = \[(.*?)\];', html, re.DOTALL)
items = json.loads(f"[{m.group(1)}]")
print(f"Extracted {len(items)} SKUs")

# Extract suppliers & costs
sm = re.search(r'var suppliers = \{(.*?)\};', html, re.DOTALL)
cm = re.search(r'var costs = \{(.*?)\};', html, re.DOTALL)
suppliers = json.loads('{' + sm.group(1) + '}') if sm else {}
costs = json.loads('{' + cm.group(1) + '}') if cm else {}

# Compute initial wh from current_stock (all stock in warehouse)
for item in items:
    total = item['current_stock']
    safety = item['safety']
    item['wh'] = max(0, total) + 3   # all stock in warehouse, +3 buffer
    item['wh_safety'] = safety

# Create DB
db_dir = r"C:\Users\28073\Desktop\补货工具"
db_path = os.path.join(db_dir, "inventory.db")
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.executescript('''
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL, category TEXT, brand TEXT, name TEXT NOT NULL,
    size TEXT NOT NULL, color TEXT NOT NULL, location TEXT,
    wh INTEGER DEFAULT 0, wh_safety INTEGER DEFAULT 0,
    supplier TEXT, cost REAL, UNIQUE(code, size, color)
);
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL, code TEXT NOT NULL, size TEXT NOT NULL,
    color TEXT NOT NULL, qty INTEGER NOT NULL,
    cost_per_unit REAL, total_cost REAL, source TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
''')

inserted = 0
for item in items:
    try:
        c.execute('''INSERT INTO inventory 
            (code,category,brand,name,size,color,location,wh,wh_safety,supplier,cost)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (item['code'], item['category'], item['brand'], item['name'],
             item['size'], item['color'], item['location'],
             item['wh'], item['wh_safety'],
             suppliers.get(item['code'], ''), costs.get(item['code'], 0)))
        inserted += 1
    except Exception as e:
        print(f"SKIP: {item['code']} {item['size']} {item['color']}: {e}")

conn.commit()
c.execute("SELECT COUNT(*), SUM(wh) FROM inventory")
row = c.fetchone()
print(f"DB OK: {row[0]} SKUs, total wh={row[1]}")

c.execute("SELECT DISTINCT brand, code FROM inventory ORDER BY brand")
for r in c.fetchall():
    print(f"  {r[0]} ({r[1]})")

conn.close()
print(f"\nCreated: {db_path}")
