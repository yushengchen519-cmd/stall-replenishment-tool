"""
档口库存管理引擎 - AI 核心
解析微信文字消息 → 执行进货/补货/查询

v2.0: 只统计仓库库存，取消摊位概念
- 进货 = 厂商→仓库 (wh+)
- 补货 = 仓库→摊位 (wh-, 不跟踪摊位数量)

用法:
  python inv_engine.py "华为906 白 2XL 进20件 单价5块"
  python inv_engine.py "beyond Sim 灰 M 补5件"
  python inv_engine.py "查库存"
"""
import re
import sys
import sqlite3
import json
from datetime import datetime

DB_PATH = r"C:\Users\28073\Desktop\补货工具\inventory.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def find_sku(conn, query_text: str) -> list:
    """Find matching SKUs by brand/name/code/size/color fuzzy match."""
    c = conn.cursor()
    words = query_text.strip().split()
    
    # Try exact match on code first — but still apply size/color filters from remaining words
    code_match = None
    for w in words:
        if w.upper().startswith(('BR-', 'UN-', 'SK-', 'ST-')):
            code_match = w.upper()
            break
    if code_match:
        words = [w for w in words if not w.upper().startswith(('BR-', 'UN-', 'SK-', 'ST-'))]

    # Build search conditions
    conditions = []
    params = []
    
    # Brand match (brand name or code prefix)
    known_brands = {
        '华为': 'BR-006', 'beyond': 'UN-008', 'smile': 'UN-008', 'Sim': 'UN-008',
        'byford': 'UN-001', 'triumph': 'BR-001', 'wacoal': 'BR-004', 'renoma': 'UN-004',
        'goldlion': 'SK-001', 'gunze': 'ST-001', 'atsugi': 'ST-003',
        'puma': 'SK-003', 'happy socks': 'SK-005',
    }
    
    brand_codes = set()
    remaining_words = []
    sizes = {'S', 'M', 'L', 'XL', 'XXL', '2XL', '3XL', '4XL', 'M-L', 'L-LL', 'L-XL', '均码', 
             '34B', '34C', '36B', '36C'}
    colors = {'黑', '黑色', '白', '白色', '肉', '肤色', '粉', '粉色', '灰', '灰色', '深灰',
              '蓝', '蓝色', '花色', '红', '红色'}
    color_aliases = {
        '黑': ['黑', '黑色'], '黑色': ['黑', '黑色'],
        '白': ['白', '白色'], '白色': ['白', '白色'],
        '肉': ['肉', '肤色'], '肤色': ['肉', '肤色'],
        '粉': ['粉', '粉色'], '粉色': ['粉', '粉色'],
        '灰': ['灰', '灰色'], '灰色': ['灰', '灰色'],
        '深灰': ['深灰'], '蓝': ['蓝', '蓝色'], '蓝色': ['蓝', '蓝色'],
        '花色': ['花色'], '红': ['红', '红色'], '红色': ['红', '红色'],
    }
    
    for w in words:
        w_lower = w.lower()
        if w_upper := w.upper():
            if w_upper in sizes or w in sizes or w in colors:
                remaining_words.append(w)
                continue
        matched = False
        for brand_name, code in known_brands.items():
            if w_lower == brand_name or w_lower in brand_name or brand_name in w_lower:
                brand_codes.add(code)
                matched = True
                break
        if not matched:
            c.execute("SELECT DISTINCT code FROM inventory WHERE brand LIKE ? OR name LIKE ?", 
                      (f'%{w}%', f'%{w}%'))
            for r in c.fetchall():
                brand_codes.add(r['code'])
                matched = True
        if not matched:
            remaining_words.append(w)
    
    if code_match:
        conditions.append("code=?")
        params.append(code_match)
    elif brand_codes:
        placeholders = ','.join('?' * len(brand_codes))
        conditions.append(f"code IN ({placeholders})")
        params.extend(brand_codes)
    
    # Size match
    for w in remaining_words[:]:
        w_upper = w.upper()
        if w_upper in sizes or w in sizes:
            conditions.append("size=?")
            params.append(w if w in sizes else w_upper)
            remaining_words.remove(w)
    
    # Color match
    for w in remaining_words[:]:
        if w in colors:
            aliases = color_aliases.get(w, [w])
            placeholders_c = ','.join('?' * len(aliases))
            conditions.append(f"color IN ({placeholders_c})")
            params.extend(aliases)
            remaining_words.remove(w)
    
    query = "SELECT * FROM inventory"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    c.execute(query, params)
    rows = c.fetchall()
    results = [dict(r) for r in rows]
    
    if not results and remaining_words:
        for w in remaining_words:
            c.execute("SELECT * FROM inventory WHERE name LIKE ? OR code LIKE ?", 
                      (f'%{w}%', f'%{w}%'))
            rows = c.fetchall()
            if rows:
                results = [dict(r) for r in rows]
    
    return results


def parse_action(text: str) -> dict:
    """Parse user intent: 补货 vs 进货 vs 查询"""
    text = text.strip()
    result = {
        'action': 'query',
        'qty': 0,
        'cost_per_unit': None,
        'search_text': text,
    }
    
    进货_match = re.search(r'(?:进|进货|进新)\s*(\d+)\s*件?\s*(?:单价|成本|价)?\s*(\d+\.?\d*)?\s*(?:块|元|SGD)?', text)
    if 进货_match:
        result['action'] = 'restock'
        result['qty'] = int(进货_match.group(1))
        result['cost_per_unit'] = float(进货_match.group(2)) if 进货_match.group(2) else None
        result['search_text'] = re.sub(r'(?:进|进货|进新)\s*\d+\s*件?\s*(?:单价|成本|价)?\s*\d*\.?\d*\s*(?:块|元|SGD)?', '', text).strip()
    
    补货_match = re.search(r'(?:补|补货|拿)\s*(\d+)\s*件?\s*(?:到)?\s*(?:摊位|档口)?', text)
    if not 补货_match:
        补货_match = re.search(r'(?:摊位|档口)\s*(?:补|拿)\s*(\d+)\s*件?', text)
    if 补货_match:
        result['action'] = 'replenish'
        result['qty'] = int(补货_match.group(1))
        result['search_text'] = re.sub(r'(?:补|补货|拿|摊位|档口)\s*\d+\s*件?', '', text).strip()
    
    if re.search(r'查|库存|多少|还有|剩余|剩', text):
        result['action'] = 'query'
    
    return result


# ===== COMPACT FORMAT PARSER =====

CN_NUM = {'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
ALL_COLORS = {'黑','黑色','白','白色','肉','肤色','粉','粉色','灰','灰色','深灰','蓝','蓝色','花色','红','红色'}
SIZES_BLOCK = {'S','M','L','XL','XXL','2XL','3XL','4XL','M-L','L-LL','L-XL','均码','34B','34C','36B','36C'}
SIZE_NORMALIZE = {'两':'2','二':'2','三':'3','四':'4'}
for prefix, digit in SIZE_NORMALIZE.items():
    for s in list(SIZES_BLOCK):
        if s[0].isdigit():
            SIZES_BLOCK.add(prefix + s[1:])
KNOWN_CODES = {'BR-001','BR-004','BR-006','UN-001','UN-004','UN-006','UN-008',
               'SK-001','SK-003','SK-004','SK-005','ST-001','ST-003'}
KNOWN_NAMES = {'906','Sim','smile','Smile'}


def to_num(s: str):
    if s in CN_NUM:
        return CN_NUM[s]
    try:
        return int(s)
    except ValueError:
        return None


def parse_compact(text: str) -> list | None:
    text = text.strip()
    if re.search(r'进|补|查|库存|多少|还有', text):
        return None
    
    for code in sorted(KNOWN_CODES, key=len, reverse=True):
        if text.upper().startswith(code.upper()):
            rest = text[len(code):]
            for sz in sorted(SIZES_BLOCK, key=len, reverse=True):
                if rest.upper().startswith(sz.upper()):
                    size = sz
                    colors_part = rest[len(sz):]
                    return _parse_colors(colors_part, code, size)
            return _parse_colors(rest, code, None)
    
    for name in sorted(KNOWN_NAMES, key=len, reverse=True):
        if text.lower().startswith(name.lower()):
            rest = text[len(name):].lstrip()
            rest_clean = rest.lstrip('.。，, ')
            for sz in sorted(SIZES_BLOCK, key=len, reverse=True):
                if rest_clean.upper().startswith(sz.upper()):
                    after_sz = rest_clean[len(sz):].lstrip('.。，, ')
                    normal_sz = sz
                    for cn, digit in SIZE_NORMALIZE.items():
                        if sz.startswith(cn):
                            normal_sz = digit + sz[len(cn):]
                            break
                    return _parse_colors(after_sz, name, normal_sz)
            return _parse_colors(rest_clean, name, None)
    
    for sz in sorted(SIZES_BLOCK, key=len, reverse=True):
        idx = text.upper().find(sz.upper())
        if idx > 0:
            code_text = text[:idx]
            colors_part = text[idx + len(sz):]
            normal_sz = sz
            for cn, digit in SIZE_NORMALIZE.items():
                if sz.startswith(cn):
                    normal_sz = digit + sz[len(cn):]
                    break
            return _parse_colors(colors_part, code_text, normal_sz)
    
    return None


def _parse_colors(colors_part: str, code_text: str, size: str | None) -> list | None:
    if not colors_part:
        return None
    
    tokens = []
    i = 0
    while i < len(colors_part):
        if colors_part[i].isspace():
            i += 1
            continue
        matched = False
        for clen in (2, 1):
            if i + clen <= len(colors_part):
                chunk = colors_part[i:i+clen]
                if chunk in ALL_COLORS:
                    tokens.append(('color', chunk))
                    i += clen
                    matched = True
                    break
                if clen == 1 and chunk in CN_NUM:
                    tokens.append(('num', CN_NUM[chunk]))
                    i += clen
                    matched = True
                    break
        if not matched:
            num_match = re.match(r'\d+', colors_part[i:])
            if num_match:
                tokens.append(('num', int(num_match.group())))
                i += len(num_match.group())
            else:
                i += 1
    
    if not tokens:
        return None
    
    pairs = []
    pending_colors = []
    for ttype, tval in tokens:
        if ttype == 'color':
            pending_colors.append(tval)
        elif ttype == 'num':
            if pending_colors:
                for c in pending_colors:
                    pairs.append({'code_text': code_text, 'size': size, 'color': c, 'qty': tval})
                pending_colors = []
    
    for c in pending_colors:
        pairs.append({'code_text': code_text, 'size': size, 'color': c, 'qty': 1})
    
    return pairs if pairs else None


# ===== OPERATIONS =====

def do_query(conn, search_text: str) -> str:
    """Handle query requests — v2.0: warehouse only"""
    if not search_text or search_text in ('查', '查库存', '库存'):
        c = conn.cursor()
        c.execute("""
            SELECT brand, name, 
                   SUM(wh) as total_wh
            FROM inventory 
            GROUP BY code 
            ORDER BY brand
        """)
        rows = c.fetchall()
        lines = ["📊 仓库库存总览：\n"]
        lines.append("| 品牌 | 款式 | 仓库 | 安全线 | 状态 |")
        lines.append("|------|------|------|--------|------|")
        for r in rows:
            # Get the safety line for this code
            c2 = conn.cursor()
            c2.execute("SELECT wh_safety FROM inventory WHERE code=(SELECT code FROM inventory WHERE brand=? AND name=? LIMIT 1)", 
                       (r['brand'], r['name']))
            sf = c2.fetchone()
            safety = sf['wh_safety'] if sf else 0
            status = '⚠️ 不足' if r['total_wh'] < safety else '✅ 充足'
            lines.append(f"| {r['brand']} | {r['name']} | {r['total_wh']} | {safety} | {status} |")
        return '\n'.join(lines)
    
    skus = find_sku(conn, search_text)
    if not skus:
        return f"❌ 找不到匹配的货品：「{search_text}」\n试试：品牌名+款式+尺码+颜色"
    
    if len(skus) == 1:
        s = skus[0]
        status = '⚠️ 需进货' if s['wh'] < s['wh_safety'] else '✅ 充足'
        return (
            f"📦 {s['brand']} {s['name']} | {s['size']} {s['color']}\n"
            f"   仓库: {s['wh']} 件 | 安全线: {s['wh_safety']} 件\n"
            f"   状态: {status}"
        )
    
    lines = [f"🔍 找到 {len(skus)} 个匹配：\n"]
    for s in skus:
        status = '⚠️' if s['wh'] < s['wh_safety'] else '✅'
        lines.append(f"  {status} {s['code']} {s['brand']} {s['name']} {s['size']} {s['color']}: 仓库{s['wh']}件(安全线{s['wh_safety']})")
    return '\n'.join(lines)


def do_replenish(conn, search_text: str, qty: int) -> str:
    """补货: 仓库→摊位 (只减少仓库，不跟踪摊位)"""
    skus = find_sku(conn, search_text)
    if not skus:
        return f"❌ 找不到匹配的货品：「{search_text}」"
    if len(skus) > 1:
        return f"❌ 匹配到多个货品，请更具体：\n" + '\n'.join(
            f"  {s['brand']} {s['name']} {s['size']} {s['color']}" for s in skus
        )
    
    s = skus[0]
    if qty > s['wh']:
        return (
            f"⚠️ 仓库库存不足！\n"
            f"   {s['brand']} {s['name']} {s['size']} {s['color']}\n"
            f"   仓库只有 {s['wh']} 件，请求补 {qty} 件\n"
            f"   最多可补: {s['wh']} 件"
        )
    
    c = conn.cursor()
    c.execute("UPDATE inventory SET wh=wh-? WHERE id=?", (qty, s['id']))
    c.execute("INSERT INTO transactions (type,code,size,color,qty,total_cost,source) VALUES ('replenish',?,?,?,?,0,?)",
              (s['code'], s['size'], s['color'], qty, f"replenish:{search_text}"))
    conn.commit()
    
    new_wh = s['wh'] - qty
    return (
        f"✅ 补货完成！\n"
        f"   {s['brand']} {s['name']} {s['size']} {s['color']}\n"
        f"   仓库 -{qty} → {new_wh} 件\n"
        f"   {'⚠️ 低于安全线！' if new_wh < s['wh_safety'] else ''}"
    )


def do_restock(conn, search_text: str, qty: int, cost_per_unit: float = None) -> str:
    """进货: 供应商→仓库"""
    skus = find_sku(conn, search_text)
    if not skus:
        return f"❌ 找不到匹配的货品：「{search_text}」"
    if len(skus) > 1:
        return f"❌ 匹配到多个货品，请更具体：\n" + '\n'.join(
            f"  {s['brand']} {s['name']} {s['size']} {s['color']}" for s in skus
        )
    
    s = skus[0]
    if cost_per_unit is None:
        cost_per_unit = s['cost'] or 0
    
    total_cost = qty * cost_per_unit
    
    c = conn.cursor()
    c.execute("UPDATE inventory SET wh=wh+? WHERE id=?", (qty, s['id']))
    c.execute("INSERT INTO transactions (type,code,size,color,qty,cost_per_unit,total_cost,source) VALUES ('restock',?,?,?,?,?,?,?)",
              (s['code'], s['size'], s['color'], qty, cost_per_unit, total_cost, f"restock:{search_text}"))
    conn.commit()
    
    cost_line = f"   单价: SGD {cost_per_unit:.2f}"
    return (
        f"✅ 进货完成！\n"
        f"   {s['brand']} {s['name']} {s['size']} {s['color']}\n"
        f"   仓库 +{qty} → {s['wh'] + qty} 件\n"
        f"   {cost_line}\n"
        f"   总成本: SGD {total_cost:.2f}"
    )


def process_message(text: str) -> str:
    """Main entry: parse text → execute → return message"""
    text = text.strip()
    if not text:
        return "说点什么吧，比如「华为906白2XL 进50件 单价5块」或「进 906 2XL 粉1 红1 黑2」"
    
    conn = get_db()
    try:
        # --- Try compact format first ---
        compact_action = None
        compact_text = text
        cost_per_unit = None
        
        m = re.match(r'(进|进货|进新|补|补货|拿)\s*', text)
        if m:
            prefix = m.group(1)
            compact_text = text[m.end():].strip()
            if prefix in ('进', '进货', '进新'):
                compact_action = 'restock'
                cost_m = re.search(r'(?:单价|成本|价)\s*(\d+\.?\d*)\s*(?:块|元|SGD)?\s*$', text)
                if cost_m:
                    cost_per_unit = float(cost_m.group(1))
            elif prefix in ('补', '补货', '拿'):
                compact_action = 'replenish'
        
        elif '进' in text:
            compact_action = 'restock'
        elif '补' in text:
            compact_action = 'replenish'
        
        pairs = parse_compact(compact_text)
        if pairs and not compact_action:
            compact_action = 'replenish'
        if pairs and compact_action:
            lines = [f"📋 批量{('进货' if compact_action == 'restock' else '补货')} {len(pairs)} 项：\n"]
            total_cost_all = 0
            for p in pairs:
                search = f"{p['code_text']} {' '.join(filter(None, [p['size'], p['color']]))}"
                if compact_action == 'restock':
                    result = do_restock(conn, search.strip(), p['qty'], cost_per_unit)
                    cost_match = re.search(r'总成本: SGD ([\d.]+)', result)
                    if cost_match:
                        total_cost_all += float(cost_match.group(1))
                else:
                    result = do_replenish(conn, search.strip(), p['qty'])
                lines.append(result)
                lines.append("")
            if compact_action == 'restock' and total_cost_all > 0:
                lines.append(f"💰 总成本: SGD {total_cost_all:.2f}")
            return '\n'.join(lines)
        
        # --- Standard format ---
        parsed = parse_action(text)
        if parsed['action'] == 'query':
            return do_query(conn, parsed['search_text'])
        elif parsed['action'] == 'replenish':
            return do_replenish(conn, parsed['search_text'], parsed['qty'])
        elif parsed['action'] == 'restock':
            return do_restock(conn, parsed['search_text'], parsed['qty'], parsed.get('cost_per_unit'))
        else:
            if '进' in text:
                return "⚠️ 无法识别进货指令。格式：品牌+款式+尺码+颜色+进N件+单价X块"
            elif '补' in text:
                return "⚠️ 无法识别补货指令。格式：品牌+款式+尺码+颜色+补N件"
            else:
                return do_query(conn, text)
    finally:
        conn.close()


if __name__ == '__main__':
    msg = sys.argv[1] if len(sys.argv) > 1 else ' '.join(sys.stdin.read().split())
    if msg:
        print(process_message(msg))
    else:
        print("Usage: python inv_engine.py '指令'")
