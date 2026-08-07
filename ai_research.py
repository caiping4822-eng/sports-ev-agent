from __future__ import annotations
import json, os, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from api_football import TEAM_MAP

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'
CST = timezone(timedelta(hours=8))
VERSION = 9

def load(p, d):
    try: return json.loads(p.read_text(encoding='utf8'))
    except: return d

def dump(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2), encoding='utf8')

def post(url, payload, headers):
    req = Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json', **headers}, method='POST')
    with urlopen(req, timeout=50) as r:
        return json.loads(r.read().decode('utf-8'))

def err(e):
    if isinstance(e, HTTPError):
        try: body = e.read().decode('utf8','replace')[:180].replace('\n',' ')
        except: body = ''
        return f'HTTP {e.code} {body}'
    return type(e).__name__

def norm(x): return re.sub(r'[^a-z0-9]','',x.lower())

def relevant(result, home_aliases, away_aliases):
    raw = result.get('title','') + ' ' + result.get('content','')
    if re.search(r"women|women's|女子|女足|\(\s*W\s*\)", raw, re.I): return False
    text = norm(raw)
    return any(norm(a) in text for a in home_aliases) and any(norm(a) in text for a in away_aliases)

def search(query):
    key = os.getenv('TAVILY_API_KEY','').strip()
    if not key: raise RuntimeError('TAVILY_API_KEY 未配置')
    return post('https://api.tavily.com/search', {'query':query, 'search_depth':'basic', 'max_results':5}, {'Authorization':'Bearer '+key})

def collect_three_lanes(home_aliases, away_aliases):
    home, away = home_aliases[0], away_aliases[0]
    lanes = [
        ('伤停与阵容', f'{home} {away} injury suspension lineup team news official'),
        ('联赛背景与战意依据', f'{home} {away} league standings table title race relegation qualification preview'),
        ('近期状态与赛程', f'{home} {away} recent form results schedule rest days head to head'),
    ]
    selected = []
    known = set()
    lane_failures = []
    for category, query in lanes:
        try:
            raw = search(query)
            kept = [x for x in raw.get('results',[]) if relevant(x, home_aliases, away_aliases)]
            if not kept: lane_failures.append(f"{category}：未取得双方相关来源")
            for item in kept:
                url = item.get('url','')
                if url and url not in known:
                    known.add(url)
                    selected.append({**item, 'category': category})
        except Exception as ex:
            lane_failures.append(f"{category}：{err(ex)}")
    return selected[:12], lane_failures

def deepseek_summarize(match, kickoff, results, lane_failures):
    key = os.getenv('DEEPSEEK_API_KEY','').strip()
    if not key: raise RuntimeError('DEEPSEEK_API_KEY 未配置')
    snips = '\n\n'.join(f"类别:{r['category']}\nURL:{r['url']}\nTITLE:{r['title']}\nTEXT:{r.get('content','')[:900]}" for r in results)
    prompt = f'''你是 DeepSeek 足球赛前事实核验助手。仅使用下面提供的搜索摘要，分析比赛：{match}，开赛时间：{kickoff}。
所有文本必须使用简体中文。严格返回 JSON，且必须包含以下字段：
{{"summary":"","competition_context":[],"motivation_evidence":[],"form_schedule":[],"confirmed":[],"uncertain":[],"risks":[]}}

规则：
1. competition_context 只写可验证的联赛/杯赛背景、积分排名、首回合比分。
2. motivation_evidence 只写可验证的战意依据（积分/赛制）。
3. form_schedule 只写摘要明确给出的近期战绩、休息天数。
4. confirmed 只写明确伤停/停赛/官方赛果。
5. 来源问题写入 risks。
6. summary 用2-4句概括事实边界。

三路检索未取得材料：{'; '.join(lane_failures) if lane_failures else '无'}

搜索摘要：
{snips}'''
    data = post('https://api.deepseek.com/chat/completions',
                {'model':'deepseek-chat','messages':[{'role':'user','content':prompt}],'temperature':0.0,'response_format':{'type':'json_object'}},
                {'Authorization':'Bearer '+key})
    result = json.loads(data['choices'][0]['message']['content'])
    for field in ('competition_context','motivation_evidence','form_schedule','confirmed','uncertain','risks'):
        if not isinstance(result.get(field), list): result[field] = []
    result['summary'] = str(result.get('summary',''))
    return result

def build_ai_section(data):
    cards = []
    for item in data.get('events', []):
        meta = item.get('deepseek', {})
        success = bool(meta.get('success'))
        engine = 'DeepSeek 已调用（deepseek-chat）' if success else f"DeepSeek 未生成有效总结：{meta.get('error','未调用')}"
        sources_html = ' ｜ '.join(f'<a href="{escape(s["url"])}" target="_blank">[{escape(s.get("category","来源"))}]</a>' for s in item.get('sources', [])) or '无'
        research = item.get('research', {})
        cards.append(f"""
        <div class="research">
          <h3>{escape(item['code'])} {escape(item['match'])}</h3>
          <p><b>搜索质量：</b>{escape(item['status'])}</p>
          <p class="small"><b>总结引擎：</b>{escape(engine)}</p>
          <p><b>DeepSeek综合总结：</b>{escape(research.get('summary','数据不足'))}</p>
          <p><b>联赛/杯赛背景：</b>{escape('；'.join(research.get('competition_context',[])) or '源未返回')}</p>
          <p><b>可验证战意依据：</b>{escape('；'.join(research.get('motivation_evidence',[])) or '源未返回')}</p>
          <p><b>近期状态与赛程：</b>{escape('；'.join(research.get('form_schedule',[])) or '源未返回')}</p>
          <p><b>已确认伤停/事实：</b>{escape('；'.join(research.get('confirmed',[])) or '无')}</p>
          <p><b>待确认：</b>{escape('；'.join(research.get('uncertain',[])) or '无')}</p>
          <p><b>来源冲突与主要风险：</b>{escape('；'.join(research.get('risks',[])) or '无')}</p>
          <p class="small"><b>有效来源：</b>{sources_html}</p>
        </div>""")
    return '<!-- AI_START --><div class="card"><h2>AI 三路基本面研究</h2><p class="small">三路独立检索：伤停阵容 | 联赛背景/战意依据 | 近期状态/赛程。DeepSeek 中文结构化总结并展示调用状态。</p>' + ''.join(cards) + '</div><!-- AI_END -->'

def main():
    DATA.mkdir(exist_ok=True)
    today = datetime.now(CST).strftime('%Y-%m-%d')
    cache = load(DATA/'ai_research_daily.json', {})
    latest = load(DATA/'latest_zgzcw.json', {})
    events = latest.get('events', [])

    if cache.get('date') == today and cache.get('pipeline_version') == VERSION:
        data = cache
    else:
        out = []
        for event in events:
            home_aliases = TEAM_MAP.get(event['home'], [])
            away_aliases = TEAM_MAP.get(event['away'], [])
            if not home_aliases or not away_aliases:
                out.append({
                    'code': event['code'], 'match': f"{event['home']} vs {event['away']}",
                    'status': '球队别名未确认，AI搜索跳过', 'sources': [], 'valid': False,
                    'deepseek': {'success': False, 'provider': 'DeepSeek', 'model': 'deepseek-chat', 'error': '球队别名未确认，未调用'},
                    'research': {'summary': '不进入AI模型', 'competition_context': [], 'motivation_evidence': [], 'form_schedule': [], 'confirmed': [], 'uncertain': [], 'risks': ['球队映射不足']}
                })
                continue
            try:
                results, lane_failures = collect_three_lanes(home_aliases, away_aliases)
                research = deepseek_summarize(f"{home_aliases[0]} vs {away_aliases[0]}", event.get('kickoff','未知'), results, lane_failures)
                status = f'有效来源 {len(results)} 个（伤停/背景/赛程三路）'
                deepseek = {'success': True, 'provider': 'DeepSeek', 'model': 'deepseek-chat'}
                valid = True
            except Exception as ex:
                results = []
                reason = err(ex)
                research = {'summary': 'AI研究无效', 'competition_context': [], 'motivation_evidence': [], 'form_schedule': [], 'confirmed': [], 'uncertain': [], 'risks': ['搜索/总结未通过：'+reason]}
                status = 'AI研究无效'
                deepseek = {'success': False, 'provider': 'DeepSeek', 'model': 'deepseek-chat', 'error': reason}
                valid = False
            out.append({
                'code': event['code'], 'match': f"{event['home']} vs {event['away']}",
                'status': status, 'sources': [{'title':r.get('title',''),'url':r.get('url',''),'category':r.get('category','来源')} for r in results],
                'valid': valid, 'deepseek': deepseek, 'research': research
            })
        data = {'date': today, 'pipeline_version': VERSION, 'updated_at': datetime.now(CST).isoformat(), 'events': out}
        dump(DATA/'ai_research_daily.json', data)

    page = DOCS / 'index.html'
    if page.exists():
        html = page.read_text(encoding='utf8')
        html = re.sub(r'<!-- AI_START -->.*?<!-- AI_END -->', '', html, flags=re.S)
        section = build_ai_section(data)
        html = html.replace('</header><main>', '</header><main>' + section)
        page.write_text(html, encoding='utf8')
    print("AI research v9 (3-lane + DeepSeek status) completed.")

if __name__ == '__main__':
    main()