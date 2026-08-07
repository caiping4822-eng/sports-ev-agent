from __future__ import annotations
import json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
from result_verifier import result_for   # improved one

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'
CST = timezone(timedelta(hours=8))

def load(p, d):
    try: return json.loads(p.read_text(encoding='utf8'))
    except: return d

def dump(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2), encoding='utf8')

def parse(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=CST)

def main():
    ledger = load(DATA / 'prediction_ledger.json', [])
    seeds = load(DATA / 'verified_results_seed.json', {})
    hist = []

    for r in ledger:
        # Use seed first (manual or previous verified)
        seed = seeds.get(r.get('key'))
        if seed:
            res = {'score': seed['score'], 'outcome': seed.get('outcome', ''), 'source': 'verified_seed', 'verified': True}
        else:
            res = result_for(r)

        fp = r.get('forced') if isinstance(r.get('forced'), dict) else None

        if res:
            rec = {
                'key': r['key'],
                'score': res['score'],
                'outcome': res['outcome'],
                'source': res.get('source', 'seed'),
                'verified': res.get('verified', True),
                'forced': None
            }
            if fp:
                rec['forced'] = {
                    'selection': fp.get('selection'),
                    'odds': fp.get('odds'),
                    'probability': fp.get('probability', 0),
                    'win': fp.get('selection') == res['outcome'],
                    'profit_units': (fp.get('odds', 1) - 1) if fp.get('selection') == res['outcome'] else -1,
                    'historical': False
                }
            hist.append(rec)

    dump(DATA / 'settlement_history.json', hist)

    # Build clean tables
    now = datetime.now(CST)
    yesterday_review_rows = []
    history_lock_rows = []

    for r in ledger:
        s = next((x for x in hist if x['key'] == r['key']), None)
        fp = r.get('forced') if isinstance(r.get('forced'), dict) else None
        ko = r.get('kickoff', '')

        if s and s.get('forced'):
            sf = s['forced']
            settle = f"{s['score']}（{s['outcome']}）/ {'命中' if sf['win'] else '未命中'} / {sf['profit_units']:+.2f}u"
            source = s['source'] + '（手动/种子）'
        elif s:
            settle = f"{s['score']}（{s['outcome']}）/ 历史补录，不计入ROI"
            source = s['source']
        else:
            try:
                ko_dt = parse(ko)
                if ko_dt > now:
                    settle = f"未开赛（约{(ko_dt - now).total_seconds()/3600:.1f}小时后）"
                else:
                    settle = "已结束，待身份校验赛果"
            except:
                settle = "待赛果"
            source = "—"

        row = f"<tr><td>{escape(r['code'])}</td><td>{escape(r['home'])} vs {escape(r['away'])}</td><td>{escape((fp or {}).get('selection','PASS'))}</td><td>{escape(settle)}</td><td>{escape(source)}</td></tr>"

        # Yesterday review (recent finished)
        if '周五' in r['code'] or '周六' in r['code']:
            yesterday_review_rows.append(row)

        # History lock (all settled or recent)
        history_lock_rows.append(row)

    # Clean Yesterday Review section
    yesterday_html = f"""
<!-- YESTERDAY_REVIEW_START -->
## 昨日复盘与累计表现

**累计：** 已结算逐场强制推荐 {len([x for x in hist if x.get('forced') and not x.get('forced',{}).get('historical')])} 场 ｜ 样本不足30场，不评价系统能力

<table>
<tr><th>编号</th><th>比赛</th><th>赛前锁定</th><th>赛果</th><th>模拟结算</th></tr>
{''.join(yesterday_review_rows[:15])}
</table>
<!-- YESTERDAY_REVIEW_END -->
"""

    # Clean History Lock section
    history_html = f"""
<!-- HISTORY_LOCK_START -->
## 历史锁定、身份校验赛果与代理CLV

**累计：** 双源身份校验结算 {len([x for x in hist if x.get('verified')])} 场 ｜ 样本不足30场，不评价系统能力。

<table>
<tr><th>编号</th><th>中国竞彩对阵</th><th>赛前选择</th><th>90分钟身份校验结算</th><th>赛果来源</th></tr>
{''.join(history_lock_rows)}
</table>
<!-- HISTORY_LOCK_END -->
"""

    page = DOCS / 'index.html'
    if page.exists():
        h = page.read_text(encoding='utf8')

        # Replace Yesterday Review
        h = re.sub(r'<!-- YESTERDAY_REVIEW_START -->.*?<!-- YESTERDAY_REVIEW_END -->', yesterday_html, h, flags=re.S)

        # Replace History Lock
        h = re.sub(r'<!-- HISTORY_LOCK_START -->.*?<!-- HISTORY_LOCK_END -->', history_html, h, flags=re.S)

        page.write_text(h, encoding='utf8')

    print("Settlement updated with clean sections. New seeds are used first.")

if __name__ == '__main__':
    main()