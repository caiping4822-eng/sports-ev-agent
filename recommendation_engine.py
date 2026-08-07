from __future__ import annotations
import json, re
from pathlib import Path
from api_football import TEAM_MAP

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
LABELS = ['主胜','平','客胜']

def load(path, default):
    try: return json.loads(path.read_text(encoding='utf8'))
    except: return default

def devig(odds):
    inv = [1/x for x in odds]
    total = sum(inv)
    return [x/total for x in inv]

def clean(text): return re.sub(r'[\s\W_]+', '', str(text).lower(), flags=re.UNICODE)
def has_term(text, terms):
    text = clean(text)
    return any(clean(term) and clean(term) in text for term in terms)

def factual_absences(event, research):
    facts = research.get('confirmed', []) if isinstance(research, dict) else []
    home = [event['home'], *TEAM_MAP.get(event['home'], [])]
    away = [event['away'], *TEAM_MAP.get(event['away'], [])]
    adverse = re.compile(r'伤|缺阵|停赛|无法出场|injur|suspend|unavailable|out\b|absence', re.I)
    h = a = 0
    for fact in facts:
        if not adverse.search(str(fact)): continue
        if has_term(fact, home): h += 1
        if has_term(fact, away): a += 1
    return h, a

def usable(items):
    return any(str(x).strip() and str(x).strip() != '源未返回' for x in (items or []))

def build_decisions(events, bjzs):
    """新规则：仅作用于未来赛前锁定，不篡改历史台账"""
    external = load(DATA / 'latest_external_markets.json', {})
    api = load(DATA / 'api_context.json', {})
    fund = load(DATA / 'fundamentals_daily.json', {})
    ai = load(DATA / 'ai_research_daily.json', {})
    history = load(DATA / 'market_history.json', [])
    fby = {x.get('code'): x for x in fund.get('events', []) if isinstance(x, dict)}
    aby = {x.get('code'): x for x in ai.get('events', []) if isinstance(x, dict)}
    output = []

    for event in events:
        market = next((x for x in event.get('markets', []) if x.get('market') == '1X2'), None)
        average = bjzs.get(event.get('analysis_match_id') or event.get('source_match_id'))
        if not market or not average or not average.get('current'): continue

        odds = [float(market['home_win']), float(market['draw']), float(market['away_win'])]
        market_p = devig(average['current'])
        ar = aby.get(event['code'], {})
        research = ar.get('research', {}) if isinstance(ar, dict) else {}
        ap = api.get(event['code'], {})
        fp = fby.get(event['code'], {})
        er = external.get(event.get('source_match_id'), {})
        books = len(er.get('books', [])) if er.get('available') else 0

        # 数据可信度（仅用于未来锁定）
        score = 35
        if str(ap.get('status', '')).startswith('已匹配'): score += 10
        if fp and fp.get('home_stats', {}).get('form') not in ('源未返回', '-', ''): score += 15
        if ar.get('sources'): score += 10
        if usable(research.get('competition_context')): score += 4
        if usable(research.get('form_schedule')): score += 4
        if books >= 3: score += 17
        if len(history) >= 2: score += 5
        risks = research.get('risks', []) or []
        score = max(0, min(100, score - min(12, 3 * len(risks))))
        confidence = '高' if score >= 75 else '中' if score >= 55 else '低'

        home_bad, away_bad = factual_absences(event, research)
        # 新规则：仅小幅调整（0.4pp per fact，最大2pp）
        direction = max(-.02, min(.02, (away_bad - home_bad) * .004))
        risk_penalty = min(.012, .002 * len(risks))

        base = [max(0, p - .02) for p in market_p]
        final = [
            max(0, base[0] + direction - risk_penalty),
            max(0, base[1] - risk_penalty),
            max(0, base[2] - direction - risk_penalty)
        ]
        ev = [final[i] * odds[i] - 1 for i in range(3)]
        eligible = [i for i, o in enumerate(odds) if o >= 1.80]
        if not eligible: continue

        forced_i = max(eligible, key=lambda i: (final[i], ev[i]))
        strict_i = max(range(3), key=lambda i: ev[i])
        strict = books >= 3 and score >= 70 and ev[strict_i] >= .03

        # 全局强制娱乐：结合数据可信度排序（不影响历史）
        global_score = final[forced_i] * (.60 + .40 * score / 100)

        gaps = []
        if books < 3: gaps.append('外部同场机构不足3家')
        if not str(ap.get('status','')).startswith('已匹配'): gaps.append('API-Football未匹配')
        if not fp: gaps.append('赛季基本面未返回')
        if not ar.get('sources'): gaps.append('AI联网研究未完成')
        if len(history) < 2: gaps.append('盘口变化尚无第二次快照')

        output.append({
            'code': event['code'], 'match': f"{event['home']} vs {event['away']}", 'odds': odds,
            'market_p': market_p, 'base_p': base, 'conservative_p': final, 'ev': ev,
            'forced_i': forced_i, 'strict_i': strict_i, 'strict': strict,
            'confidence': score, 'conf_label': confidence, 'global_score': global_score,
            'home_adverse': home_bad, 'away_adverse': away_bad,
            'direction_adjustment': direction, 'risk_penalty': risk_penalty,
            'confirmed': research.get('confirmed', []) or [],
            'uncertain': research.get('uncertain', []) or [],
            'risks': risks,
            'context': research.get('competition_context', []) or [],
            'motivation': research.get('motivation_evidence', []) or [],
            'form_schedule': research.get('form_schedule', []) or [],
            'gaps': gaps
        })
    return output

def global_forced(decisions):
    """全局强制娱乐推荐：在逐场基础上结合数据可信度排序"""
    return max(decisions, key=lambda x: (x['global_score'], x['conservative_p'][x['forced_i']])) if decisions else None

def forced_payload(decision):
    i = decision['forced_i']
    return {
        'selection': LABELS[i], 'odds': decision['odds'][i],
        'probability': decision['conservative_p'][i],
        'market_probability': decision['market_p'][i],
        'base_probability': decision['base_p'][i],
        'ev': decision['ev'][i], 'stake_units': 1, 'type': 'per_match',
        'probability_source': '百家平均去水＋确认事实小幅调整＋来源风险惩罚',
        'home_adverse_facts': decision['home_adverse'],
        'away_adverse_facts': decision['away_adverse'],
        'direction_adjustment': decision['direction_adjustment'],
        'risk_penalty': decision['risk_penalty'],
        'data_confidence': decision['confidence'],
        'global_composite_score': decision['global_score']
    }