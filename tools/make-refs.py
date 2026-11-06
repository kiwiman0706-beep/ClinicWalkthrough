#!/usr/bin/env python3
"""完成イメージ用の下絵（UIを消した3Dスクリーンショット）と色見本を書き出す。

    python3 -m http.server 8099 &            # リポジトリのルートで
    python3 tools/make-refs.py out/          # out/ に PNG を並べる

画像生成AIに「参照画像」として渡す前提なので、構図は図面の寸法どおりです。
プロンプトは docs/完成イメージ生成メモ.md を参照。
"""
import pathlib, sys
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

URL = 'http://127.0.0.1:8099/'
CHROME = '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome'
JP = '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf'
HIDE = ("()=>{for(const id of ['clinic-jump','clinic-hud','clinic-zoombar','clinic-pad'])"
        "{const e=document.getElementById(id); if(e)e.style.display='none';}}")
# 名前, 立ち位置[x,y,z], 見る先[x,y,z], 画角, ビューポート
SHOTS = [
    ('A-hero',      [5.70, 1.50, 12.15], [4.55, 1.30, 9.40], 92, (1600, 900)),
    ('B-diagonal',  [2.40, 1.50, 12.00], [4.80, 1.32, 9.45], 92, (1600, 900)),
    ('C-portrait',  [5.20, 1.50, 11.90], [4.40, 1.25, 9.40], 80, (1050, 1400)),
    ('D-entrance',  [1.90, 1.55, 12.15], [4.20, 1.38, 8.60], 98, (1600, 900)),
    ('E-staffside', [4.90, 1.50,  8.40], [5.60, 1.35, 11.60], 92, (1600, 900)),
]
# 図面照合メモ「1F 内装マテリアル」と同じ値
ROWS = [
    ('壁・天井', 'ビニールクロス 東リ WVP8255', '#e8e4e0'),
    ('待合の木目壁', '木目クロス WVP8041', '#a78972'),
    ('アクセント①AC（受付背面）', 'ビニールクロス WVP8069', '#9f999f'),
    ('アクセント②AC（診察室1）', '東リ WVP8257', '#aeb7a2'),
    ('アクセント③AC（診察室2）', '東リ WVP8256', '#cdc9be'),
    ('アクセント④AC（WC(P)）', '東リ WVP8492', '#afb1b6'),
    ('床（待合・WC(P)）', '東リ FS4274 マチュア', '#aeaaa6'),
    ('床（その他）', '東リ FS4276 マチュア', '#d9d2c5'),
    ('巾木', 'ソフト巾木 TH60 19', '#e0e0df'),
    ('カウンター木部・面台', 'アイカ JC-12031K', '#84716c'),
    ('カウンター天板（石目）', 'アイカ LJ-10234KN74', '#eee1d4'),
    ('建具・枠', 'グレージュアッシュ PA/DC型', '#ae9183'),
]
# カメラを自由に置くための足場。アプリのスクリプトは外から触れない閉じたスコープなので、
# index.html の中に一時ページとして差し込んでから読み込む（終わったら消す）。
HOOK = ("window.__rv=(e,t,f)=>{roomView=[e,t];walkPos=null;lookYaw=0;lookPitch=0;"
        "if(f)q('fov').value=f;render();};\n")
ANCHOR = 'function reset(){roomView=null;'
TMP = '.refs-tmp.html'


def make_tmp_page(root):
    """index.html にカメラ用のフックを足した一時ページを作る。"""
    src = (root / 'index.html').read_text(encoding='utf-8')
    if ANCHOR not in src:
        sys.exit('make-refs: index.html に reset() が見つかりません')
    (root / TMP).write_text(src.replace(ANCHOR, HOOK + ANCHOR, 1), encoding='utf-8')
    return root / TMP


def shots(out, root):
    tmp = make_tmp_page(root)
    try:
        _shots(out)
    finally:
        tmp.unlink(missing_ok=True)


def _shots(out):
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
        for name, eye, target, fov, (w, h) in SHOTS:
            ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2)
            pg = ctx.new_page()
            pg.goto(URL + TMP, wait_until='load'); pg.wait_for_timeout(2200)
            pg.eval_on_selector('#clinic-floor-tabs [data-view="1"]', 'e=>e.click()'); pg.wait_for_timeout(500)
            pg.eval_on_selector('#clinic-mode-tabs [data-mode="inside"]', 'e=>e.click()'); pg.wait_for_timeout(500)
            pg.evaluate('a=>window.__rv(a[0],a[1],a[2])', [eye, target, fov]); pg.wait_for_timeout(900)
            pg.evaluate(HIDE); pg.wait_for_timeout(200)
            pg.locator('#clinic-scene').screenshot(path=str(out / f'base-{name}.png'))
            print('wrote', out / f'base-{name}.png'); ctx.close()
        b.close()


def swatches(out):
    f1, f2, f3 = (ImageFont.truetype(JP, s) for s in (30, 22, 19))
    fh = ImageFont.truetype(JP, 42)
    W, RH, TOP = 1500, 96, 130
    im = Image.new('RGB', (W, TOP + RH * len(ROWS) + 40), '#ffffff')
    d = ImageDraw.Draw(im)
    d.text((44, 38), '大阪なんば脳神経こころクリニック 1F マテリアル', fill='#1d2321', font=fh)
    d.text((46, 92), '設計図書 2026-11-04「内部仕上表／マテリアル(1F)」より。'
                     '色はスウォッチの実測値（印刷物のため目安）。', fill='#5d6663', font=f3)
    for i, (name, code, hexv) in enumerate(ROWS):
        y = TOP + i * RH
        d.rectangle([44, y + 10, 204, y + RH - 10], fill=hexv, outline='#c6ccc9')
        d.text((232, y + 22), name, fill='#1d2321', font=f1)
        d.text((232, y + 60), code, fill='#5d6663', font=f3)
        d.text((1180, y + 34), hexv.upper(), fill='#1d2321', font=f2)
        if i:
            d.line([44, y + 2, W - 44, y + 2], fill='#e8ebea')
    im.save(out / '1F-materials.png')
    print('wrote', out / '1F-materials.png')


if __name__ == '__main__':
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'out')
    out.mkdir(parents=True, exist_ok=True)
    shots(out, pathlib.Path(__file__).resolve().parent.parent); swatches(out)
