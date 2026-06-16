# Column Definitions Quick Reference

## Complete colDefs array (render function)

```javascript
var colDefs = [
    {h:'☑',        a:1, m:0, d:0, r:function(it,ix){return '<input type="checkbox" class="checkbox" '+(isSelected(ix)?'checked':'')+' onchange="toggleSelect('+ix+',this)">';}},
    {h:'商品编号', a:1, m:0, d:0, r:function(it,ix){return it.code;}},
    {h:'品类',     a:0, m:1, d:1, r:function(it,ix){return it.category;}},
    {h:'品牌',     a:0, m:1, d:1, r:function(it,ix){return it.brand;}},
    {h:'款式名称', a:1, m:0, d:0, r:function(it,ix){return it.name;}},
    {h:'尺码',     a:1, m:0, d:0, r:function(it,ix){return it.size;}},
    {h:'颜色',     a:1, m:0, d:0, r:function(it,ix){return it.color;}},
    {h:'存放位置', a:0, m:1, d:1, r:function(it,ix){return it.location;}},
    {h:'当前库存', a:1, m:0, d:0, r:function(it,ix){
      var s = it.wh;
      var sf = it.wh_safety;
      return '<span style="font-weight:bold;color:'+(s<=0?'#ef4444':s<sf?'#f59e0b':'#10b981')+'">'+s+'</span>';
    }},
    {h:'安全库存', a:0, m:1, d:1, r:function(it,ix){return isDaily ? it.shelf_safety : it.wh_safety;}},
    {h:'状态',     a:0, m:1, d:1, r:function(it,ix){
      var s = isDaily ? it.shelf : it.wh;
      var sf = isDaily ? it.shelf_safety : it.wh_safety;
      var st = s <= 0 ? '缺货' : (s < sf ? '不足' : '充足');
      return '<span class="badge badge-'+(st==='缺货'?'danger':st==='不足'?'warning':'success')+'">'+st+'</span>';
    }},
    {h:'建议补货', a:0, m:1, d:1, r:function(it,ix){
      var s = isDaily ? it.shelf : it.wh;
      var sf = isDaily ? it.shelf_safety : it.wh_safety;
      var sug = Math.max(0, sf - s);
      return sug > 0 ? '<span style="color:#f59e0b">'+sug+'</span>' : '-';
    }},
    {h:isDaily?'补货':'进货', a:1, m:0, d:0, r:function(it,ix){
      var sels = isDaily ? selections : whSelections;
      var s = isDaily ? it.shelf : it.wh;
      var sf = isDaily ? it.shelf_safety : it.wh_safety;
      var sug = Math.max(0, sf - s);
      var sel = sels[ix] !== undefined;
      var qty = sel ? sels[ix] : 0;
      var disabled = isDaily ? '' : (sel||(s<sf)?'':'disabled');
      return '<input type="number" class="qty-input" value="'+qty+'" min="0" '+disabled+' oninput="updateQty('+ix+',this.value,this)" onclick="event.stopPropagation()">';
    }},
    {h:'供应商',   a:0, m:1, d:1, r:function(it,ix){return suppliers[it.code]||'-';}},
    {h:'成本单价', a:0, m:1, d:1, r:function(it,ix){var c=costs[it.code]||0;return '$'+c.toFixed(2);}},
    {h:'小计(SGD)',a:0, m:1, d:1, r:function(it,ix){
      var sels = isDaily ? selections : whSelections;
      var qty = sels[ix] || 0;
      return '<span class="subtotal-val" style="color:#10b981;font-weight:bold">$'+(qty*(costs[it.code]||0)).toFixed(2)+'</span>';
    }}
  ];
```

## updateThead() cols array (MUST match colDefs)

```javascript
var cols = [
    {h:'☑',        a:1, m:0, d:0},
    {h:'商品编号', a:1, m:0, d:0},
    {h:'品类',     a:0, m:1, d:1},
    {h:'品牌',     a:0, m:1, d:1},
    {h:'款式名称', a:1, m:0, d:0},
    {h:'尺码',     a:1, m:0, d:0},
    {h:'颜色',     a:1, m:0, d:0},
    {h:'存放位置', a:0, m:1, d:1},
    {h:'当前库存', a:1, m:0, d:0},
    {h:'安全库存', a:0, m:1, d:1},
    {h:'状态',     a:0, m:1, d:1},
    {h:'建议补货', a:0, m:1, d:1},
    {h:isDaily?'补货':'进货', a:1, m:0, d:0},
    {h:'供应商',   a:0, m:1, d:1},
    {h:'成本单价', a:0, m:1, d:1},
    {h:'小计(SGD)',a:0, m:1, d:1}
  ];
```

## Replenishment logic cheat sheet

| Action | Mode | Code | Side effect |
|--------|------|------|-------------|
| shelve ↑ | Daily | `item.shelf += qty` | `item.wh = max(0, wh - qty)` |
| warehouse ↑ | Warehouse | `item.wh += qty` | None |
| Qty cap | Daily | `if(qty > wh) qty = wh` | `inputEl.value = qty` |

## localStorage keys

| Key | Purpose |
|-----|---------|
| `stall_inventory_v1` | Full inventory snapshot (shelf, wh, safety) |
| `stall_inventory_v1_v2` | Flag: +3 warehouse bump applied |
