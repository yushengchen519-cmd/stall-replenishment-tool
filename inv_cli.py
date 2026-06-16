#!/usr/bin/env python3
"""
Inv engine CLI wrapper for Hermes.
Takes message from stdin or argv, returns response to stdout.
Auto-syncs to inventory_sync.js for HTML page.
Built-in verification: before/after snapshot comparison.
"""
import sys
import os
import sqlite3
import json

SYNC_JS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory_sync.js')
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')

def snapshot_db():
    """Take a snapshot: key=(code,size,color) → {wh, wh_safety}"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT code, size, color, wh, wh_safety FROM inventory ORDER BY code, size, color').fetchall()
    conn.close()
    return {(r['code'], r['size'], r['color']): {'wh': r['wh'], 'wh_safety': r['wh_safety']} for r in rows}

def write_sync_file():
    """Write inventory_sync.js from current DB state for HTML page sync."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute('SELECT code, size, color, wh, wh_safety FROM inventory ORDER BY code, size, color').fetchall()
        data = [{'code':r['code'],'size':r['size'],'color':r['color'],
                 'wh':r['wh'],'wh_safety':r['wh_safety']} for r in rows]
        conn.close()
        js = 'var SYNC_DATA = ' + json.dumps(data, ensure_ascii=False) + ';'
        with open(SYNC_JS_PATH, 'w', encoding='utf-8') as f:
            f.write(js)
    except Exception:
        pass

def verify_operation(before, after, result_text):
    """
    Compare before/after DB snapshots.
    Verify: correct items changed, others untouched, totals consistent.
    """
    lines = []
    changed = []
    unchanged = []
    
    all_keys = set(before.keys()) | set(after.keys())
    only_before = [k for k in all_keys if k not in after]
    only_after = [k for k in all_keys if k not in before]
    
    for key in all_keys:
        if key in before and key in after:
            b, a = before[key], after[key]
            if b['wh'] != a['wh']:
                changed.append({
                    'key': key,
                    'before': b,
                    'after': a,
                    'delta': a['wh'] - b['wh']
                })
            else:
                unchanged.append(key)
    
    lines.append("\n🔍 === 验证报告 ===")
    
    is_modify = ('📋 批量' in result_text or '补货完成' in result_text or '进货完成' in result_text)
    is_query = not is_modify
    
    if is_query:
        if changed or only_before or only_after:
            lines.append("❌ 查询操作不应修改数据，但检测到变更！")
            for c in changed:
                lines.append(f"   ⚠️ {c['key']}: wh {c['before']['wh']}→{c['after']['wh']}")
        else:
            lines.append("✅ 查询操作：数据未变更，通过")
        return '\n'.join(lines)
    
    # Modifying operation
    if not changed:
        lines.append("⚠️ 操作返回成功，但未检测到仓库库存变更。可能重复执行。")
        return '\n'.join(lines)
    
    all_good = True
    lines.append(f"📝 变更项 ({len(changed)} 条)：")
    for c in changed:
        code, size, color = c['key']
        arrow = '↑' if c['delta'] > 0 else '↓'
        lines.append(f"   {code} {size} {color}: 仓库 {c['before']['wh']}→{c['after']['wh']} ({arrow}{abs(c['delta'])})")
        if c['after']['wh'] < 0:
            lines.append(f"      ❌ 仓库库存为负！")
            all_good = False
    
    lines.append(f"✅ 未变更项 ({len(unchanged)} 条)：未受影响")
    
    if only_before:
        lines.append(f"❌ 消失项 ({len(only_before)} 条)：{only_before}")
        all_good = False
    if only_after:
        lines.append(f"❌ 新增项 ({len(only_after)} 条)：{only_after}")
        all_good = False
    
    if len(before) == len(after):
        lines.append(f"✅ SKU 总数一致：{len(after)} 条")
    else:
        lines.append(f"❌ 总数不一致！操作前 {len(before)} 条，操作后 {len(after)} 条")
        all_good = False
    
    # Total wh sum check
    total_before = sum(v['wh'] for v in before.values())
    total_after = sum(v['wh'] for v in after.values())
    delta = total_after - total_before
    
    if '进货' in result_text or ('进' in result_text[:2] and '补' not in result_text[:4]):
        if delta > 0:
            lines.append(f"✅ 总库存增加 {delta} 件 → {total_after} 件，符合进货预期")
        else:
            lines.append(f"⚠️ 进货操作但总库存未增加 (delta={delta})")
    elif '补货' in result_text:
        if delta < 0:
            lines.append(f"✅ 总库存减少 {abs(delta)} 件 → {total_after} 件，符合补货预期")
        elif delta == 0 and changed:
            lines.append(f"⚠️ 补货操作但总库存未变，可能部分SKU失败")
        else:
            lines.append(f"✅ 总库存: {total_after} 件")
    else:
        lines.append(f"📊 总库存变化: {delta:+d} → {total_after} 件")
    
    if all_good:
        lines.append("\n🟢 验证通过")
    else:
        lines.append("\n🔴 验证未通过！请检查上方 ❌ 项")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from inv_engine import process_message
    
    msg = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read().strip()
    if msg:
        # 操作前快照
        before = snapshot_db()
        
        # 执行操作
        result = process_message(msg)
        print(result)
        
        # 操作后快照
        after = snapshot_db()
        
        # 验证
        verification = verify_operation(before, after, result)
        print(verification)
        
        # Auto-sync to HTML
        if '✅' in result or '📋' in result:
            write_sync_file()
    else:
        print("请发送仓库管理指令，例如：\n  华为906 白 2XL 进20件 单价5块\n  beyond Sim 灰 M 补5件\n  查库存")
