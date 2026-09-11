#!/usr/bin/env python3
"""Package the walkthrough engine, the sample building and the guides as a zip.

The app in src/clinicwalkthrough.html is this clinic's model, but everything
between the //<<BUILDING>> and //<</BUILDING>> markers is the only part that is
about *this* building. This script swaps that block for kit/building-sample.js,
rewrites the handful of building-specific bits of markup from
kit/sample-meta.json, and lays the result out as a self-contained kit:

    python3 tools/build-kit.py                 -> dist/walkthrough-kit.zip

Nothing about the real clinic - drawings, room names, dimensions - goes into
the zip.
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
KIT = ROOT / 'kit'
START, END = '//<<BUILDING>>', '//<</BUILDING>>'
# Copied in verbatim: the PWA shell plus the two scripts the workflow needs.
CARRY = [
    ('manifest.webmanifest', 'app/manifest.webmanifest'),
    ('sw.js', 'app/sw.js'),
    ('.nojekyll', 'app/.nojekyll'),
    ('tools/apply-pwa-patch.py', 'tools/apply-pwa-patch.py'),
    ('tools/apply-settings.py', 'tools/apply-settings.py'),
]
DOCS = ['README.md', 'PROMPT.md', 'GUIDE.md', 'LICENSE.txt']


def swap_building(source, building):
    """Replace the building block, keeping the engine either side of it."""
    i, j = source.find(START), source.find(END)
    if i < 0 or j < 0:
        sys.exit('build-kit: could not find the //<<BUILDING>> markers in the source')
    j = source.index('\n', j) + 1
    return source[:i] + building.strip() + '\n' + source[j:]


def swap_markup(html, meta):
    """Retitle the app and rebuild the floor tabs for the sample's floor list."""
    html = re.sub(r'<title>.*?</title>', '<title>' + meta['app_title'] + '</title>', html, count=1)
    options = ''.join(
        f'<option value="{f["value"]}"{" selected" if i == 0 else ""}>{f["option"]}</option>'
        for i, f in enumerate(meta['floor_tabs']))
    html = re.sub(r'(<select id="clinic-view"[^>]*>).*?(</select>)',
                  lambda m: m.group(1) + options + m.group(2), html, count=1, flags=re.S)
    tabs = '\n'.join(
        f'      <button type="button" role="tab" class="clinic-seg-btn" data-view="{f["value"]}"'
        f' aria-selected="{"true" if i == 0 else "false"}">{f["label"]}</button>'
        for i, f in enumerate(meta['floor_tabs']))
    html = re.sub(r'(<div class="clinic-seg" id="clinic-floor-tabs"[^>]*>\n).*?(\n    </div>)',
                  lambda m: m.group(1) + tabs + m.group(2), html, count=1, flags=re.S)
    html = re.sub(r'(<p class="text-small">)[^<]*(</p>)',
                  lambda m: m.group(1) + meta['footnote'] + m.group(2), html, count=1)
    html = re.sub(r'(<p class="text-small" id="clinic-build">)[^<]*(</p>)',
                  lambda m: m.group(1) + meta['build_line'] + m.group(2), html, count=1)
    return html


def build(out_zip):
    meta = json.loads((KIT / 'sample-meta.json').read_text(encoding='utf-8'))
    source = (ROOT / 'src' / 'clinicwalkthrough.html').read_text(encoding='utf-8')
    building = (KIT / 'building-sample.js').read_text(encoding='utf-8')
    app = swap_markup(swap_building(source, building), meta)
    # Nothing from the real building may survive the swap.
    leaked = [w for w in ('MRI室', '吹抜け', '心療内科', 'エックス線', '旧1F', 'なんば', '脳神経') if w in app]
    if leaked:
        sys.exit('build-kit: the real building leaked into the kit: ' + ', '.join(leaked))

    with tempfile.TemporaryDirectory() as tmp:
        stage = pathlib.Path(tmp) / 'walkthrough-kit'
        (stage / 'app' / 'src').mkdir(parents=True)
        (stage / 'tools').mkdir()
        (stage / 'sample').mkdir()
        src_path = stage / 'app' / 'src' / 'walkthrough.html'
        src_path.write_text(app, encoding='utf-8')
        subprocess.run([sys.executable, str(ROOT / 'tools' / 'apply-pwa-patch.py'),
                        str(src_path), '-o', str(stage / 'app' / 'index.html')],
                       check=True, stdout=subprocess.DEVNULL)
        index = stage / 'app' / 'index.html'
        index.write_text(re.sub(r'(<meta name="description" content=")[^"]*(">)',
                                lambda m: m.group(1) + meta['description'] + m.group(2),
                                index.read_text(encoding='utf-8'), count=1), encoding='utf-8')
        for src, dest in CARRY:
            shutil.copy2(ROOT / src, stage / dest)
        manifest = json.loads((stage / 'app' / 'manifest.webmanifest').read_text(encoding='utf-8'))
        manifest['name'] = meta['manifest_name']
        manifest['short_name'] = meta['manifest_short_name']
        manifest['description'] = meta['description']
        (stage / 'app' / 'manifest.webmanifest').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        shutil.copytree(ROOT / 'icons', stage / 'app' / 'icons')
        for doc in DOCS:
            shutil.copy2(KIT / doc, stage / doc)
        for name in ('make-sample-plan.py', 'sample-plan-1F.pdf', 'sample-plan-2F.pdf'):
            shutil.copy2(KIT / 'sample' / name, stage / 'sample' / name)
        # Ready to become a repository: the Pages workflow publishes app/, not the root.
        for path in sorted((KIT / 'repo').rglob('*')):
            if path.is_file():
                dest = stage / path.relative_to(KIT / 'repo')
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
        (stage / 'plans').mkdir()
        (stage / 'plans' / 'README.md').write_text(
            '自分の図面 PDF をこのフォルダに置いてください。\n\n'
            'リポジトリにする場合は **private** にしてください。'
            '図面は施主・設計者の資産です。公開リポジトリに置くと誰でも見られます。\n',
            encoding='utf-8')
        shutil.copy2(KIT / 'building-sample.js', stage / 'sample' / 'building-sample.js')

        out_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    zf.write(path, path.relative_to(stage.parent))
    size = out_zip.stat().st_size
    print(f'build-kit: wrote {out_zip} ({size/1024:.0f} KB)')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('-o', '--output', type=pathlib.Path,
                    default=ROOT / 'dist' / 'walkthrough-kit.zip')
    build(ap.parse_args().output)


if __name__ == '__main__':
    main()
