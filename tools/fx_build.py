import math, json, re
from fx_syms import syms
# nearest blue label wins, but only within 0.45 m
WEAK=(('LAN','lan'),('TEL','tel'),('HDMI','hdmi'),('TV','tv'),('NC','nc'),('INT','int'),('SEN','sen'))
def near(c, texts, r, pred):
    best=None; bd=r
    for t in texts:
        if not pred(t['t']): continue
        d=math.hypot(t['x']-c['x'], t['z']-c['z'])
        if d<bd: bd=d; best=t
    return best
def classify(c, texts):
    if c['d']<0.13:
        # a small circle is a weak-current point; take the nearest label that names one
        w=near(c,texts,0.7,lambda t:any(k in t.upper() for k,_ in WEAK))
        if w:
            for key,kind in WEAK:
                if key in w['t'].upper(): return kind, w['t']
        return 'weak', (w['t'] if w else '')
    # a big circle is a socket; only a socket label applies to it
    p=near(c,texts,0.40,lambda t:re.search(r'単E|ﾘｰﾗｰ|リーラー|防水|TVジャック|(^|[^A-Za-z])E([^A-Za-z]|$)',t.replace('　','')))
    lab=p['t'] if p else ''
    u=lab.replace('　','')
    if '単E' in u: return 'outletE1', lab
    if 'ﾘｰﾗｰ' in u or 'リーラー' in u: return 'reeler', lab
    if '防水' in u: return 'outletWP', lab
    if u.startswith('TV') or 'TVジャック' in u: return 'outletTV', lab
    if re.search(r'(^|[^a-zA-Z])E', u): return 'outletE', lab
    return 'outlet', lab
NAME={'outlet':'2口コンセント','outletE':'アース付2口コンセント','outletE1':'単独アース付コンセント',
 'outletTV':'TVジャック付コンセント','outletWP':'防水コンセント','reeler':'リーラーコンセント（天井用）',
 'lan':'LAN','tel':'電話ジャック','hdmi':'HDMI','tv':'TV','nc':'ナースコール','int':'インターホン','sen':'センサー','weak':'弱電'}
DEFH={'reeler':2.40,'lan':0.25,'tel':0.25,'hdmi':0.25,'tv':0.25,'nc':1.20,'int':1.30,'sen':2.30,'weak':0.25}
def build(f):
    s,t=syms(f)
    rows=[]
    for c in sorted(s,key=lambda c:(round(c['z'],1),c['x'])):
        k,lab=classify(c,t)
        rows.append(dict(kind=k,x=c['x'],z=c['z'],h=DEFH.get(k,0.25),label=lab))
    return rows
if __name__=='__main__':
    for tag,f in [('1F','09560ea3-1F-____1.pdf'),('2F','951eceac-2F-____1.pdf')]:
        rows=build(f)
        print('===',tag,len(rows))
        for i,r in enumerate(rows,1):
            print('  %2d %-12s (%5.2f,%5.2f) h=%.2f  «%s»'%(i,r['kind'],r['x'],r['z'],r['h'],r['label']))
        json.dump(rows,open(f'fx-{tag}.json','w'),ensure_ascii=False,indent=1)
