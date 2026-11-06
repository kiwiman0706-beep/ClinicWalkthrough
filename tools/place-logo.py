"""生成画像のサインプレートに、本物のロゴを透視変換して合成する。

画像生成に文字やロゴを描かせると必ず崩れるので、プレートは無地で出させて、
あとから本物を貼る。ロゴは SVG をブラウザで透過PNGに起こしてから使う。

    python3 tools/place-logo.py <生成画像> <ロゴPNG(透過)> <出力> \\
        "x0,y0;x1,y1;x2,y2;x3,y3" [余白比 0.15] [不透明度 0.96] [縦オフセット 0]

4点はプレートの角を 左上→右上→右下→左下 の順で、生成画像のピクセル座標で指定します。
生成するたびにプレートの位置は変わるので、画像を見て測り直してください。
"""
import sys
from PIL import Image

def coeffs(src, dst):
    # dst(出力)の4点 -> src(入力)の4点 への射影変換係数
    import numpy as np
    A=[]; B=[]
    for (x,y),(u,v) in zip(dst,src):
        A.append([x,y,1,0,0,0,-u*x,-u*y]); B.append(u)
        A.append([0,0,0,x,y,1,-v*x,-v*y]); B.append(v)
    return np.linalg.solve(np.array(A,dtype=float), np.array(B,dtype=float)).tolist()

def place(base_path, logo_path, quad, out, margin=.14, opacity=.96, dy=0.0):
    base=Image.open(base_path).convert('RGBA')
    logo=Image.open(logo_path).convert('RGBA')
    (x0,y0),(x1,y1),(x2,y2),(x3,y3)=quad            # TL,TR,BR,BL
    # プレート内に余白を取り、ロゴの縦横比に合わせた矩形を作る
    def lerp(a,b,t): return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)
    def at(u,v):
        top=lerp((x0,y0),(x1,y1),u); bot=lerp((x3,y3),(x2,y2),u)
        return lerp(top,bot,v)
    pw=((x1-x0)**2+(y1-y0)**2)**.5
    ph=((x3-x0)**2+(y3-y0)**2)**.5
    ar=logo.width/logo.height
    fw=1-2*margin; fh=fw*pw/ar/ph                    # 幅合わせ
    if fh>1-2*margin: fh=1-2*margin; fw=fh*ph*ar/pw
    u0,u1=(1-fw)/2,(1+fw)/2
    v0,v1=(1-fh)/2+dy,(1+fh)/2+dy
    dst=[at(u0,v0),at(u1,v0),at(u1,v1),at(u0,v1)]
    src=[(0,0),(logo.width,0),(logo.width,logo.height),(0,logo.height)]
    warped=logo.transform(base.size, Image.PERSPECTIVE,
                          coeffs(src,dst), Image.BICUBIC)
    if opacity<1:
        al=warped.split()[3].point(lambda p:int(p*opacity)); warped.putalpha(al)
    base.alpha_composite(warped)
    base.convert('RGB').save(out, quality=95)
    print('wrote', out)

if __name__=='__main__':
    base, logo, out = sys.argv[1], sys.argv[2], sys.argv[3]
    q=[tuple(float(n) for n in p.split(',')) for p in sys.argv[4].split(';')]
    place(base, logo, q, out, *(float(a) for a in sys.argv[5:]))
