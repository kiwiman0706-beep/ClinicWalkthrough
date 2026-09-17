import pymupdf, json, sys
from PIL import Image, ImageDraw, ImageFont
U='/root/.claude/uploads/2a59a3b0-5e20-5251-8357-801db57cd5ef/'
K=0.0211667; X0=175.8; Y0=110.7; S=95.0; M=30.0
F='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def render(f, rows, out):
    d=pymupdf.open(U+f); pg=d[0]
    mat=pymupdf.Matrix(K*S,0,0,K*S,-X0*K*S+M,-Y0*K*S+M)
    clip=pymupdf.Rect(X0-M/(K*S)/1, Y0-M/(K*S), X0+11.2/K, Y0+12.9/K)
    pix=pg.get_pixmap(matrix=mat, clip=clip, colorspace=pymupdf.csRGB, alpha=False)
    im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples); dr=ImageDraw.Draw(im)
    fo=ImageFont.truetype(F,13)
    for x in range(0,12):
        u=M+x*S; dr.line([(u,0),(u,im.height)],fill=(255,190,190)); dr.text((u+2,2),str(x),fill=(220,0,0),font=fo)
    for z in range(0,13):
        v=M+z*S; dr.line([(0,v),(im.width,v)],fill=(190,190,255)); dr.text((2,v+2),str(z),fill=(0,0,220),font=fo)
    for i,r in enumerate(rows,1):
        u=M+r['x']*S; v=M+r['z']*S
        col=(220,30,30) if r['kind'].startswith('outlet') or r['kind']=='reeler' else (0,150,60)
        dr.ellipse([u-7,v-7,u+7,v+7],outline=col,width=2)
        dr.text((u+8,v-16),str(i),fill=col,font=fo)
    im.save(out); print(out, im.size)
if __name__=='__main__':
    for tag,f in [('1F','09560ea3-1F-____1.pdf'),('2F','951eceac-2F-____1.pdf')]:
        render(f, json.load(open(f'fx-{tag}.json')), f'fx-ov-{tag}.png')
