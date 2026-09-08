#!/usr/bin/env python3
"""Wrap the standalone clinic-walkthrough HTML export as the PWA's index.html.

The app itself is generated elsewhere (ChatGPT) and dropped in as one
self-contained HTML file. Rather than hand-editing every new export, run:

    python3 tools/apply-pwa-patch.py path/to/clinicwalkthrough.html

which re-applies the packaging changes and rewrites index.html:

  * a Content-Security-Policy that allows the manifest, icons and service
    worker to load from this origin (the export ships a CDN-oriented policy
    that blocks all three),
  * PWA head tags (manifest, theme colour, apple-touch-icon, standalone hints),
  * viewport-fit / safe-area padding and touch-sized controls for phones,
  * the service-worker registration and the "add to home screen" button.

Nothing inside the app's own markup or scripts is touched.
"""
import argparse
import pathlib
import re
import sys

HEAD_TAGS = '''
<meta name="description" content="クリニック図面の3Dウォークスルー。内装の色・床材の変更と家具配置の編集ができるオフライン対応アプリ。">
<meta name="theme-color" content="#c9b89e" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#181818" media="(prefers-color-scheme: dark)">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="クリニック3D">
<meta name="format-detection" content="telephone=no">
<link rel="manifest" href="./manifest.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="./icons/icon-192.png">
<link rel="icon" type="image/png" sizes="512x512" href="./icons/icon-512.png">
<link rel="apple-touch-icon" href="./icons/apple-touch-icon.png">'''

CSP = (
    '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' blob: data:; "
    "style-src 'self' 'unsafe-inline' blob: data:; "
    "img-src 'self' blob: data:; "
    "font-src 'self' blob: data:; "
    "media-src 'self' blob: data:; "
    "manifest-src 'self'; "
    "worker-src 'self' blob:; "
    "connect-src 'self' blob: data:; "
    "frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'\">"
)

VIEWPORT_OLD = '<meta name="viewport" content="width=device-width, initial-scale=1">'
VIEWPORT_NEW = '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'

CANVAS_OLD = 'width:100%;height:500px;touch-action:none'
CANVAS_NEW = 'width:100%;height:clamp(260px,56vh,520px);touch-action:none'

STYLE_ANCHOR = ('<style>body{max-width:1120px;margin:0 auto;padding:20px;}'
                '@media(max-width:480px){body{padding:10px;}}</style>')

# `html > body` matches the specificity of the export's own `html>body{padding:0}`,
# which would otherwise win and leave content flush against the screen edge.
PWA_STYLE = '''
<style id="clinic-pwa-style">
/* --- PWA / touch device adjustments (added when packaging as an installable app) --- */
html { -webkit-text-size-adjust: 100%; }
html > body {
  min-height: 100dvh;
  padding-left: max(20px, env(safe-area-inset-left));
  padding-right: max(20px, env(safe-area-inset-right));
  padding-top: max(20px, env(safe-area-inset-top));
  padding-bottom: max(20px, env(safe-area-inset-bottom));
  overscroll-behavior-y: contain;
}
@media (max-width: 480px) {
  html > body {
    padding-left: max(10px, env(safe-area-inset-left));
    padding-right: max(10px, env(safe-area-inset-right));
    padding-top: max(10px, env(safe-area-inset-top));
    padding-bottom: max(10px, env(safe-area-inset-bottom));
  }
}
/* Keep the walk/look buttons thumb-sized and stop iOS zooming in on form focus. */
@media (pointer: coarse) {
  .btn { min-height: 44px; }
  .form-control, .form-select { min-height: 44px; font-size: 16px; }
}
#clinic-walkthrough { touch-action: manipulation; }
#clinic-scene, #clinic-plan { touch-action: none; }

#clinic-install {
  position: fixed;
  right: max(12px, env(safe-area-inset-right));
  bottom: max(12px, env(safe-area-inset-bottom));
  z-index: 20;
}
</style>'''

BODY_TAIL = '''
<button class="btn" type="button" id="clinic-install" hidden>ホーム画面に追加</button>
<script id="clinic-pwa-boot">
(() => {
  // Service worker: makes the walkthrough launchable offline from the home screen.
  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js', { scope: './' }).then(reg => {
        // Pick up a new deploy on the next launch without a hard reload.
        reg.addEventListener('updatefound', () => {
          const sw = reg.installing;
          if (sw == null) return;
          sw.addEventListener('statechange', () => {
            if (sw.state === 'installed' && navigator.serviceWorker.controller != null) {
              const status = document.getElementById('clinic-status');
              if (status != null) status.textContent = '新しいバージョンがあります。アプリを開き直すと更新されます。';
            }
          });
        });
      }).catch(() => {});
    });
  }

  // Android/Chrome only; iOS installs via the share sheet, so the button stays hidden there.
  const button = document.getElementById('clinic-install');
  let deferred = null;
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    deferred = event;
    if (button != null) button.hidden = false;
  });
  button?.addEventListener('click', async () => {
    if (deferred == null) return;
    button.hidden = true;
    deferred.prompt();
    await deferred.userChoice;
    deferred = null;
  });
  window.addEventListener('appinstalled', () => { deferred = null; if (button != null) button.hidden = true; });
})();
</script>
</body>'''


def patch(src: str) -> str:
    if 'clinic-pwa-boot' in src:
        sys.exit('error: this file has already been patched; pass the raw export instead.')

    csp = re.search(r'<meta http-equiv="Content-Security-Policy".*?>', src, re.S)
    if csp is None:
        sys.exit('error: no Content-Security-Policy meta tag found.')
    src = src[:csp.start()] + CSP + src[csp.end():]

    for old, new, label in (
        (VIEWPORT_OLD, VIEWPORT_NEW, 'viewport meta tag'),
        (CANVAS_OLD, CANVAS_NEW, '3D canvas height'),
        (STYLE_ANCHOR, STYLE_ANCHOR + PWA_STYLE, 'page style block'),
        ('</title>', '</title>' + HEAD_TAGS, '</title>'),
        ('</body>', BODY_TAIL, '</body>'),
    ):
        if src.count(old) != 1:
            sys.exit(f'error: expected exactly one {label} ({old!r}).')
        src = src.replace(old, new, 1)
    return src


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', type=pathlib.Path, help='the standalone HTML export')
    ap.add_argument('-o', '--output', type=pathlib.Path,
                    default=pathlib.Path(__file__).resolve().parent.parent / 'index.html')
    args = ap.parse_args()

    args.output.write_text(patch(args.source.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'wrote {args.output}')


if __name__ == '__main__':
    main()
