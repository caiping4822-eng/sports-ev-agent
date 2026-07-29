"""Forced entertainment recommendation — deliberately separate from strict EV picks."""

def pick(events,bjzs):
    options=[]
    labels=['主胜','平','客胜']
    for e in events:
        target=next((m for m in e.get('markets',[]) if m.get('market')=='1X2'),None)
        avg=bjzs.get(e.get('analysis_match_id') or e.get('source_match_id'))
        if not target or not avg:continue
        raw=[1/x for x in avg['current']]; total=sum(raw); p=[x/total for x in raw]
        odds=[target['home_win'],target['draw'],target['away_win']]
        for i in range(3):
            if odds[i] >= 1.80:
                pc=max(0,p[i]-.02) # universal information/timing haircut
                options.append({'code':e['code'],'league':e['league'],'home':e['home'],'away':e['away'],
                    'selection':labels[i],'odds':odds[i],'fair_p':p[i],'conservative_p':pc,
                    'ev':pc*odds[i]-1,'rank_probability':pc})
    if not options:return None
    # Forced mode means "most likely among qualifying prices", not "best EV".
    return max(options,key=lambda x:(x['rank_probability'],x['ev']))
