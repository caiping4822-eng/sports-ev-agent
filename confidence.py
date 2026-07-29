def assess(event,bjzs,external,notes,goalodds,movement):
    target=next((m for m in event.get('markets',[]) if m.get('market')=='1X2'),None)
    b=bjzs.get(event.get('analysis_match_id') or event.get('source_match_id'))
    ext=external.get(event.get('source_match_id'),{})
    note=notes.get('events',{}).get(event.get('analysis_match_id','')) or notes.get('by_code',{}).get(event['code'])
    score=0; flags={}
    flags['china']='已读取' if target else '未读取'; score+=20 if target else 0
    flags['average']='已读取' if b else '未读取'; score+=15 if b else 0
    n=len(ext.get('books',[])) if ext.get('available') else 0
    flags['external']=f'{n} 家' if n else '0 家'
    score += 25 if n>=6 else 20 if n>=3 else 8 if n>=1 else 0
    flags['fundamental']='已核验' if note else '待确认'; score+=15 if note else 0
    flags['injury']='已核验（临场复核）' if note else '待确认'; score+=10 if note else 0
    flags['movement']='首次快照' if movement.startswith('首次') else ('可能滞后' if '可能滞后' in movement else '已同步/待观察')
    score+=5 if not movement.startswith('首次') else 0
    flags['model']='已生成' if event.get('source_match_id') in goalodds else '未生成'; score+=10 if flags['model']=='已生成' else 0
    level='高' if score>=75 else '中' if score>=50 else '低'
    kelly=0.0
    if target and n>=3:
        ps=ext.get('median_fair',[]); odds=[target['home_win'],target['draw'],target['away_win']]
        if len(ps)==3:
            vals=[max(0,(max(0,p-.02)*o-1)/(o-1))*0.25 for p,o in zip(ps,odds)]
            kelly=min(max(vals),.01)
    return {'score':score,'level':level,'kelly':kelly,'flags':flags,'forced_cap':.0025}
