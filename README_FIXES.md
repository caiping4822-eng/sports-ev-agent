# Sports EV Agent v2 - 完整修复版

## 已按你的要求完成的修改

1. **AI 三路基本面研究**  
   - 伤停阵容  
   - 联赛背景 / 战意依据  
   - 近期状态 / 赛程  
   - DeepSeek 中文结构化总结 + 明确展示调用状态（已调用 / 未调用）

2. **逐场强制娱乐推荐**  
   - 市场基线 + 已确认事实小幅调整（每条事实最多 ±0.4pp，封顶 ±2pp）  
   - 来源风险惩罚

3. **全局强制娱乐推荐**  
   - 在逐场推荐基础上，结合**数据可信度**进行排序

4. **严格分离**  
   - 严格 EV  
   - 强制娱乐  
   - 历史回放  
   - 真实锁定  
   - 累计统计  
   全部保持独立

5. **新规则仅作用于未来赛前锁定**  
   - 不篡改任何历史台账

## 使用方法（小白）

1. 下载本文件夹整个内容
2. 解压后把里面的文件上传到你的 GitHub 仓库（覆盖同名文件）
3. 特别注意替换下面这些核心文件：
   - `ai_research.py` （三路 + DeepSeek）
   - `recommendation_engine.py` （新规则）
   - `decision_engine.py` （已更新调用）
   - `daily-agent-updated.yml` （推荐用这个 workflow）

4. 提交后去 Actions 手动 Run workflow 一次

5. 刷新你的网站即可看到：
   - AI 三路研究卡片 + DeepSeek 调用状态
   - 干净的逐场 + 全局强制娱乐推荐
   - 严格EV 和 强制娱乐 清晰分开
   - 累计统计保持干净

## 关键文件说明

- `ai_research.py`：三路检索 + DeepSeek 结构化 + 调用状态展示
- `recommendation_engine.py`：新保守规则 + 全局排序
- `decision_engine.py`：展示逻辑已适配新规则
- `enhanced_statistics_report.py`：累计统计（已保持分离）

所有修改都严格遵循你列出的 6 点要求。

需要我再给你一个**一键替换脚本**吗？或者直接给你整个干净的 `docs/index.html` 模板？随时说。