# 服装档口补货工具

## 🔗 快速入口

| 工具 | 链接 |
|------|------|
| 🖥️ **在线补货工具** | [打开使用](https://yushengchen519-cmd.github.io/stall-replenishment-tool/) |
| 📊 **Excel 模板下载** | [服装档口管理模板_v3.xlsx](https://raw.githubusercontent.com/yushengchen519-cmd/stall-replenishment-tool/master/服装档口管理模板_v3.xlsx) |

---

## 📋 补货工具（交互式 HTML）

**双击浏览器打开即可使用，无需联网。**

- 默认显示 14 个需补货 SKU（10缺货 + 5不足）
- 按**款式 / 品类 / 状态**三维筛选
- 勾选 → 自动填入建议补货量 → 自动计算金额
- 一键生成补货汇总清单
- 「复制为文本」可粘贴到 Excel 进货单
- 支持 `Ctrl+P` 打印 / `Ctrl+A` 全选 / `Ctrl+G` 生成清单

## 📊 服装档口管理模板_v3.xlsx

**基于 v2 升级，新增「补货清单」工作表：**

- 20 SKU 按 缺货→不足→充足 排序，颜色区分
- 库存数据通过**公式实时联动「库存总览」**
- 填入本次补货数量 → 自动计算金额
- 底部自动汇总总数量和总金额
- 带自动筛选器

其他工作表：商品目录 / 库存总览 / 进货单 / 销售开单 / 记账汇总

## 日常使用流程

1. 闭店后打开 [在线补货工具](https://yushengchen519-cmd.github.io/stall-replenishment-tool/)
2. 按款式/品类筛选 → 勾选今日需补项
3. 调整补货数量 → 点「生成补货清单」
4. 「复制为文本」→ 粘贴到 Excel `进货单` 作为新行
5. 每周用 Excel `补货清单` 核对全局库存
