import pymupdf, math, collections
U='/root/.claude/uploads/2a59a3b0-5e20-5251-8357-801db57cd5ef/'
K=0.0211667; Y0=110.7
# 図面の原点（appX=0 にあたる通り芯のページ座標）はシートごとに違う。
# 1F 系は x=175.8、2F 系は x=305.8。縦方向は両方 y=110.7。
# 通り芯の間隔（118.1pt=2,500 / 392.1pt=8,300）で同定した。
ORIGIN_X={'1F':175.8,'2F':305.8}
def originX(f):
    return ORIGIN_X['2F'] if '2F' in f else ORIGIN_X['1F']
def syms(f):
    d=pymupdf.open(U+f); p=d[0]
    X0=originX(f)
    A=lambda x,y:((x-X0)*K,(y-Y0)*K)
    out=[]; texts=[]
    for dr in p.get_drawings():
        col=dr.get('color')
        if col is None or col[2]<0.7 or col[0]>0.3: continue
        cur=[it for it in dr['items'] if it[0]=='c']
        if not cur: continue
        r=dr['rect']; ax,az=A((r.x0+r.x1)/2,(r.y0+r.y1)/2)
        if not(-0.2<ax<11.1 and -0.2<az<12.9): continue
        out.append(dict(x=round(ax,3),z=round(az,3),d=round(max(r.x1-r.x0,r.y1-r.y0)*K,3),fill=dr.get('fill') is not None))
    for blk in p.get_text('dict')['blocks']:
        for ln in blk.get('lines',[]):
            for sp in ln['spans']:
                if sp['color']!=255: continue
                t=sp['text'].strip()
                if not t: continue
                bb=sp['bbox']; ax,az=A((bb[0]+bb[2])/2,(bb[1]+bb[3])/2)
                if -0.2<ax<11.1 and -0.2<az<12.9: texts.append(dict(t=t,x=round(ax,3),z=round(az,3)))
    # merge circles that are the same symbol drawn twice
    merged=[]
    for c in sorted(out,key=lambda c:(c['z'],c['x'])):
        hit=next((m for m in merged if abs(m['x']-c['x'])<0.02 and abs(m['z']-c['z'])<0.02 and abs(m['d']-c['d'])<0.02),None)
        if hit: continue
        merged.append(c)
    return merged, texts
if __name__=='__main__':
    for tag,f in [('1F','09560ea3-1F-____1.pdf'),('2F','951eceac-2F-____1.pdf')]:
        s,t=syms(f)
        print('===',tag,'symbols:',len(s))
        print('   diameters:',collections.Counter(c['d'] for c in s).most_common())
        for c in s: print('   (%6.2f,%6.2f) d=%.2f %s'%(c['x'],c['z'],c['d'],'fill' if c['fill'] else ''))
