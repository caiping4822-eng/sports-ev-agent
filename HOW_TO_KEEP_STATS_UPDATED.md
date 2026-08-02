# 每日自动更新 + 累计统计完整方案

## 核心问题
原系统依赖中国竞彩结果页（经常被墙）和 API-Football 球队映射，导致很多已结束比赛无法自动结算 → 统计板块不更新。

## 解决方案（已为你准备好）

### 1. 替换核心脚本（推荐）

把以下文件**直接替换**仓库里的同名文件：

- `result_verifier.py` → 使用 `improved_result_verifier.py`
- `statistics_report.py` → 使用 `enhanced_statistics_report.py`
- 新增两个辅助脚本（强烈建议添加）：
  - `add_verified_result.py`
  - `force_add_today_results.py`

### 2. 更新 GitHub Actions workflow（推荐）

把 `.github/workflows/daily-agent.yml` 里的最后几行改成：

```yaml
      run: |
        python agent.py
        python fundamentals_daily.py
        python ai_research.py
        python decision_engine.py
        python fixture_registry.py
        python lock_and_review.py
        python settlement_manager.py
        python enhanced_statistics_report.py     # ← 改成增强版
        python ui_compact.py
```

### 3. 日常维护（最重要）

当自动结算失败时，用下面两种方式手动补录：

#### 方法A：单场快速补录（推荐）
```bash
python add_verified_result.py "周五001|2026-07-31 17:00" "0:3" "客胜" --sources "sofascore,espn"
```

#### 方法B：批量补录（适合一天多场比赛）
编辑 `force_add_today_results.py` 里的 `TODAY_RESULTS` 列表，然后运行：
```bash
python force_add_today_results.py
```

补录后执行：
```bash
python settlement_manager.py
python enhanced_statistics_report.py
git add data/ docs/
git commit -m "手动结算 + 累计统计更新"
git push
```

---

## 新统计功能说明

增强版 `enhanced_statistics_report.py` 会自动生成：

- **真实锁定**（只算赛前锁定 + 已结算）
  - 总场数 / 命中 / 命中率 / ROI / 平均赔率
- **按联赛** 详细表格
- **按赔率区间** 详细表格
- **历史回放**（单独统计，不影响真实ROI）
- **永不清零累计**（每次都从全量 ledger 重新计算）

所有数据保存在：
- `data/performance_stats.json`
- `data/verified_results_seed.json`（手动种子）
- `data/settlement_history.json`

---

## 完整推荐替换列表

| 原文件                        | 替换为 / 新增                  | 说明                     |
|-------------------------------|--------------------------------|--------------------------|
| result_verifier.py            | improved_result_verifier.py    | 更强的结果获取           |
| statistics_report.py          | enhanced_statistics_report.py  | 漂亮的累计分联赛统计     |
| -                             | add_verified_result.py         | 单场手动补录             |
| -                             | force_add_today_results.py     | 批量手动补录             |
| .github/workflows/daily-agent.yml | （修改 run 命令）            | 调用增强统计脚本         |

---

## 长期稳定建议

1. 每天比赛结束后 1-2 小时检查页面。
2. 如果统计没更新 → 立刻用 `add_verified_result.py` 补 1-2 场关键比赛。
3. 每周手动运行一次 `force_add_today_results.py` 并 push。
4. 可以考虑在 workflow 里加一个 "手动触发 + 强制结算" 的 job。

需要我帮你生成**完整的替换后 workflow 文件**或**打包成一个 patch**，随时说一声。

这个方案已经可以保证：
- 每天自动跑
- 统计永不清零
- 有联赛维度
- 有赔率区间维度
- 即使自动失败也能手动快速恢复

把上面的脚本放进仓库后，你就可以长期稳定运行了！