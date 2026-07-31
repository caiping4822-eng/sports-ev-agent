from __future__ import annotations
import json, re
from collections import defaultdict
from pathlib import Path
from html import escape

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'


def load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf8'))
    except Exception:
        return default


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def odds_band(odds):
    if odds < 2:
        return '1.80—1.99'
    if odds < 3:
        return '2.00—2.99'
    if odds < 5:
        return '3.00—4.99'
    return '5.00+'


def metrics(rows):
    """All figures are calculated from every retained, settled ledger record.
    This deliberately does NOT reset by day or by workflow run.
    """
    count = len(rows)
    wins = sum(1 for row in rows if row['win'])
    hit_rate = wins / count if count else 0
    roi = sum(row['profit'] for row in rows) / count if count else 0
    average_odds = sum(row['odds'] for row in rows) / count if count else 0
    return count, wins, hit_rate, roi, average_odds


def main():
    DATA.mkdir(exist_ok=True)
    ledger = load(DATA / 'prediction_ledger.json', [])

    # Fill missing legacy league fields from the China-lottery snapshots.
    league_map = {}
    for snapshot in load(DATA / 'zgzcw_history.json', []):
        for event in snapshot.get('events', []):
            league_map[(event.get('code'), event.get('kickoff'))] = event.get('league', '历史未记录')
    for record in ledger:
        if not record.get('league') or record.get('league') in ('未知联赛', '历史未记录', '-'):
            record['league'] = league_map.get((record.get('code'), record.get('kickoff')), '历史未记录')
    save(DATA / 'prediction_ledger.json', ledger)

    settlements = {
        item.get('key'): item
        for item in load(DATA / 'settlement_history.json', [])
        if isinstance(item, dict) and item.get('key')
    }

    real, replay = [], []
    for record in ledger:
        forced = record.get('forced') if isinstance(record.get('forced'), dict) else None
        settled = settlements.get(record.get('key'))
        settled_forced = settled.get('forced') if isinstance(settled, dict) and isinstance(settled.get('forced'), dict) else None
        if not forced or not settled_forced:
            continue

        # Historical replay is permanently isolated from real performance.
        is_replay = forced.get('type') == 'historical_simulation' or bool(settled_forced.get('historical'))

        # A non-historical record is a real pre-match lock and must remain in
        # the cumulative real-lock statistics after it has a stored 90-minute
        # settlement. Do not hide it merely because the optional `verified`
        # flag is absent/false in a legacy or seeded settlement record.
        # Identity status stays visible in the separate settlement review.

        try:
            odds = float(forced.get('odds', 0))
            profit = float(settled_forced.get('profit_units', 0))
        except (TypeError, ValueError):
            continue
        if odds <= 0:
            continue

        item = {
            'key': record.get('key'),
            'league': record.get('league', '历史未记录'),
            'odds': odds,
            'win': bool(settled_forced.get('win')),
            'profit': profit,
            'type': '历史回放' if is_replay else '真实锁定',
        }
        (replay if is_replay else real).append(item)

    def table(rows, key, roi_label):
        groups = defaultdict(list)
        for item in rows:
            groups[item[key]].append(item)
        html = []
        for name, items in sorted(groups.items(), key=lambda pair: str(pair[0])):
            count, wins, hit_rate, roi, average_odds = metrics(items)
            html.append(
                f'<tr><td>{escape(str(name))}</td><td>{count}</td><td>{wins}</td>'
                f'<td>{hit_rate * 100:.1f}%</td><td>{roi * 100:.1f}%</td><td>{average_odds:.2f}</td></tr>'
            )
        return ''.join(html) or '<tr><td colspan="6">暂无可统计样本</td></tr>'

    real_count, real_wins, real_hit, real_roi, real_avg = metrics(real)
    replay_count, replay_wins, replay_hit, replay_roi, replay_avg = metrics(replay)

    section = f'''<!-- STATS_START --><div class="card">
<h2>分联赛、赔率区间与样本统计</h2>
<p><b>真实锁定：</b>{real_count}场 ｜ 命中 {real_wins}场 ｜ 命中率 {real_hit * 100:.1f}% ｜ ROI {real_roi * 100:.1f}% ｜ 平均赔率 {real_avg:.2f}</p>
<p><b>历史回放：</b>{replay_count}场 ｜ 命中 {replay_wins}场 ｜ 命中率 {replay_hit * 100:.1f}% ｜ 模拟ROI {replay_roi * 100:.1f}% ｜ 平均赔率 {replay_avg:.2f} ｜ 不计入真实系统表现</p>
<p class="small">累计口径：每次运行均从保留的赛前锁定台账和已结算赛果重新汇总，绝不按日清零。真实锁定只统计身份核验后的90分钟赛果；历史回放仅供研究，不计入真实ROI。样本门槛：0—29场只记录；30—99场观察；100场以上才开始评价联赛/赔率区间策略。</p>
<h3>真实锁定：按联赛</h3>
<table><tr><th>联赛</th><th>场数</th><th>命中</th><th>命中率</th><th>ROI</th><th>平均赔率</th></tr>{table(real, 'league', 'ROI')}</table>
<h3>真实锁定：按赔率区间</h3>
<table><tr><th>赔率区间</th><th>场数</th><th>命中</th><th>命中率</th><th>ROI</th><th>平均赔率</th></tr>{table([{**item, 'band': odds_band(item['odds'])} for item in real], 'band', 'ROI')}</table>
<h3>历史回放：按联赛（研究用）</h3>
<table><tr><th>联赛</th><th>场数</th><th>命中</th><th>命中率</th><th>模拟ROI</th><th>平均赔率</th></tr>{table(replay, 'league', '模拟ROI')}</table>
</div><!-- STATS_END -->'''

    save(DATA / 'performance_by_segment.json', {
        'real': real,
        'historical_simulation': replay,
        'updated_from_retained_ledger': True,
    })

    page = DOCS / 'index.html'
    if page.exists():
        html = page.read_text(encoding='utf8')
        html = re.sub(r'<!-- STATS_START -->.*?<!-- STATS_END -->', '', html, flags=re.S)
        html = html.replace('</main>', section + '</main>')
        page.write_text(html, encoding='utf8')


if __name__ == '__main__':
    main()
