# 篮球足球 EV 智能助手

这是一个运行在 GitHub 云端的中文赛事监控与 EV 审计 Agent。

## 新手部署：只做一次

1. 将本项目内的全部文件上传到 GitHub 仓库根目录；特别注意必须上传 `.github` 文件夹。
2. GitHub 仓库打开 **Settings → Pages**。
3. 在 **Build and deployment** 选择：`Deploy from a branch`。
4. Branch 选：`main`，文件夹选：`/docs`，点击 **Save**。
5. 打开 **Actions** 标签，点左侧 `Daily Sports EV Agent`，点 `Run workflow → Run workflow`。
6. 等约 1 分钟。网页地址为：`https://你的用户名.github.io/sports-ev-agent/`。

## 配置 The Odds API（可选但推荐）

不要把 API Key 写进任何文件，不要上传 Key 到仓库。

1. 打开仓库 **Settings → Secrets and variables → Actions**。
2. 点击 **New repository secret**。
3. Name 填：`ODDS_API_KEY`。
4. Secret 填你从 The Odds API 获得的 Key，点击 Add secret。
5. 打开 Actions 手动运行一次工作流，或者等待下一次定时运行。

## 自动运行时间（北京时间）

- 09:00 初筛
- 14:00 更新
- 08:00–22:00 每两小时赛前复核

## 重要限制

没有合法的中国竞彩目标赔率、Pinnacle/PS3838 或 Betfair Exchange 数据前，Agent 默认 PASS，不会伪造正 EV 推荐。
