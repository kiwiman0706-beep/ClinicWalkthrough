#!/usr/bin/env python3
"""完成イメージ（パース）を Gemini の画像モデルで作る。

    python3 -m http.server 8099 &                  # リポジトリのルートで
    python3 tools/make-refs.py refs/               # 下絵と色見本を書き出す
    python3 tools/gen-renders.py refs/ renders/    # 4カット生成

プロンプトの本文は docs/完成イメージ生成メモ.md と同じものをここに持っています。
片方だけ直すとズレるので、変えるときは両方そろえてください。

APIキーはこのスクリプトには書きません。クラウドセッションの環境に
`generativelanguage.googleapis.com` のネットワークシークレットを
**ヘッダー名 `x-goog-api-key`／プレフィックス空**で保存しておくと、
プロキシがリクエストに付けてくれます（`Authorization: Bearer` では通りません）。
手元で動かすときだけ、環境変数 GEMINI_API_KEY を見るようにしてあります。
"""
import base64, json, mimetypes, os, pathlib, sys, urllib.error, urllib.request

MODEL = 'gemini-3-pro-image'
SIZE = '2K'          # Web用。ロゴを後から合成するので解像度は高めに。'1K'/'2K'/'4K'
BASE = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'

SPEC = """Turn this 3D massing reference into a photorealistic architectural interior
visualization. Keep the camera, the geometry, the proportions and the layout of
the reference EXACTLY as they are - do not move walls, the counter or the
openings. Only replace the flat shading with real materials, lighting and detail.

Subject: the reception and waiting area on the ground floor of a brand-new,
not-yet-opened Japanese neurology and mental-health clinic. Calm, clean, warm
and reassuring; a place that should feel easy to walk into.

Materials, exactly these:
- Floor: matte light warm-grey stone-look vinyl sheet flooring, large format,
  very subtle mottling, colour #aeaaa6. Beyond the reception, through the
  openings, the floor turns to a warmer beige of the same family, #d9d2c5.
- Walls and ceiling: off-white vinyl wallcovering with a very fine texture, #e8e4e0.
- The wall behind the counter: soft mauve-grey vinyl wallcovering, #9f999f,
  with a faint vertical weave.
- The tall panels at the right and the band framing the openings: warm oak
  wood-grain panel, #a78972, straight grain, matte.
- Reception counter body: greige-brown wood-grain melamine, #84716c, horizontal grain.
- Reception counter top: pale stone-look melamine with soft veining, #eee1d4,
  25 mm square edge, slight overhang.
- Doors and door frames: flush greige-ash timber doors, #ae9183, with slim
  brushed-stainless vertical bar handles.
- Skirting: 60 mm soft skirting, near-white #e0e0df.

On the counter at its left end stands the automatic payment kiosk (MEDISMA
desktop model), exactly where the reference shows it: a low charcoal plinth
carrying two cash units - an off-white coin unit on the left with a dark top, a
recessed coin tray and a small return opening, and an off-white banknote unit on
the right with a dark top, a thin blue accent line at the bill slot and a receipt
outlet below. Behind them a tablet on a slim black stand faces the patient, its
white screen showing a few teal buttons, and beside it a small white card
terminal. Keep it compact and tidy; no text on the screen.

On the mauve-grey wall above and behind the counter, where the reference shows
it, hangs the clinic's sign: a brushed stainless plate held 25 mm off the wall on
four small spacers, with a soft warm halo of concealed light spilling onto the
wall around it. LEAVE THE PLATE FACE COMPLETELY BLANK - no mark, no symbol, no
lettering of any kind. The real logo is added afterwards.

Lighting: ceiling height 2700 mm, flat plasterboard ceiling, recessed round
downlights at 3500 K, plus a concealed cove light washing the wood band above
the counter. Soft daylight from the left. Gentle, even, no harsh shadows,
no strong colour cast.

Style: high-end architectural photography, full-frame camera at 1.5 m eye
height, 24 mm wide lens, straight verticals, f/8, natural depth. Photorealistic,
not a render; clean and uncluttered.

{cut}

No patients and no members of the public anywhere in the frame. Nothing
readable on any screen, no documents, charts or paperwork on the counter, no
clutter. Do not over-process: no heavy HDR, no exaggerated contrast.

Absolutely no text, no lettering, no signage, no logos, no watermarks, no
Japanese or English characters anywhere in the image."""

# 名前: (下絵, アスペクト, カットごとの追記)
CUTS = {
    'hero':  ('base-B-diagonal', '16:9',
              'No people. Wide hero composition with clear space at the upper left '
              'for a headline.'),
    'sign':  ('base-F-sign', '3:2',
              'No people. Tighter, longer lens: the backlit sign plate is the subject, '
              'filling a good part of the frame. The counter edge runs across the lower '
              'foreground, slightly out of focus.'),
    'port':  ('base-C-portrait', '4:5',
              'No people. Portrait crop, focus on the counter, the stone top and the '
              'payment kiosk.'),
    'wait':  ('base-A-hero', '16:9',
              'No people. Show the bench seating in the waiting area and the daylight.'),
    'entry': ('base-D-entrance', '16:9',
              'No people. The view a patient gets on walking in: the waiting area opening '
              'up toward the reception.'),
    'corr':  ('base-G-corridor', '4:5',
              'No people. The corridor toward the consulting rooms, doors closed, '
              'depth and calm.'),
    'exam':  ('base-H-exam', '16:9',
              'No people. A consulting room with the soft green accent wall, the desk '
              'and the examination couch. Tidy, nothing on the desk.'),
    'staff': ('base-B-diagonal', '16:9',
              'Two staff in plain light-grey scrubs behind the counter, mid-distance, '
              'seen at a slight angle, faces turned away or softly out of focus and not '
              'identifiable. Natural, candid, welcoming - not posed.'),
    'work':  ('base-E-staffside', '16:9',
              'One staff member in plain light-grey scrubs at the counter seen from '
              'behind over the shoulder, working; face not visible. The street glazing '
              'and daylight beyond. Candid, for a recruitment page.'),
}
EXT = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}


def part(path):
    mt = mimetypes.guess_type(path)[0] or 'image/png'
    return {'inline_data': {'mime_type': mt,
                            'data': base64.b64encode(pathlib.Path(path).read_bytes()).decode()}}


def generate(prompt, refs, aspect, out_stem):
    """1カット生成して書き出す。"""
    body = {'contents': [{'role': 'user',
                          'parts': [part(r) for r in refs] + [{'text': prompt}]}],
            'generationConfig': {'responseModalities': ['IMAGE'],
                                 'imageConfig': {'aspectRatio': aspect,
                                                 'imageSize': SIZE}}}
    headers = {'Content-Type': 'application/json'}
    key = os.environ.get('GEMINI_API_KEY')      # 手元で動かすとき用。クラウドでは不要。
    if key:
        headers['x-goog-api-key'] = key
    req = urllib.request.Request(BASE, data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f'  HTTP {e.code}: {e.read()[:400].decode("utf8", "replace")}')
        return False
    for p in (data.get('candidates') or [{}])[0].get('content', {}).get('parts', []):
        inline = p.get('inlineData') or p.get('inline_data')
        if not inline:
            continue
        mime = inline.get('mimeType') or inline.get('mime_type')
        path = f'{out_stem}.{EXT.get(mime, "bin")}'
        pathlib.Path(path).write_bytes(base64.b64decode(inline['data']))
        print('  wrote', path)
        return True
    print('  no image returned')
    return False


if __name__ == '__main__':
    refs = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'refs')
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else 'renders')
    only = sys.argv[3:] or list(CUTS)
    out.mkdir(parents=True, exist_ok=True)
    swatches = refs / '1F-materials.png'
    for name in only:
        base, aspect, cut = CUTS[name]
        print(name)
        generate(SPEC.format(cut=cut),
                 [str(refs / f'{base}.png'), str(swatches)], aspect, str(out / name))
