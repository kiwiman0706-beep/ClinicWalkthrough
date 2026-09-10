#!/usr/bin/env python3
"""Fold a state exported from the app back into the source as the new defaults.

The app's 「変更点をコピー」 button produces a short JSON blob holding only what
differs from the drawing-derived defaults. Paste it into a file (or pipe it in)
and run:

    python3 tools/apply-settings.py state.json
    pbpaste | python3 tools/apply-settings.py -

which rewrites the `const savedState={...};` line in src/clinicwalkthrough.html
and regenerates index.html. Passing `--clear` drops back to the built-in
defaults. The built-in figures stay in the file either way, so the drawing
baseline is never lost.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'src' / 'clinicwalkthrough.html'
ANCHOR = re.compile(r'^const savedState=.*;$', re.M)
LEVELS = ('0', '1', '2')
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')
FINISH_KEYS = ('wall', 'floor', 'ceiling', 'dado')
NUM_KEYS = ('x', 'z', 'w', 'd', 'h')


def fail(message):
    sys.exit('apply-settings: ' + message)


def check(state):
    """Reject anything the app itself would refuse, so a bad paste fails here."""
    if not isinstance(state, dict) or state.get('format') != 'clinic-state-v1':
        fail('not a clinic-state-v1 export (check you copied the whole block)')
    for level, rooms in (state.get('finishes') or {}).items():
        if level not in LEVELS or not isinstance(rooms, dict):
            fail(f'bad finishes entry: {level!r}')
        for room, spec in rooms.items():
            if not isinstance(spec, dict):
                fail(f'bad finish for {room!r}')
            for key, value in spec.items():
                if key not in FINISH_KEYS or not (isinstance(value, str) and HEX.match(value)):
                    fail(f'bad finish {key!r} for {room!r}: {value!r}')
    for level, items in (state.get('furniture') or {}).items():
        if level not in LEVELS or not isinstance(items, dict):
            fail(f'bad furniture entry: {level!r}')
        for index, spec in items.items():
            if not index.isdigit() or not isinstance(spec, dict):
                fail(f'bad furniture index: {index!r}')
            for key, value in spec.items():
                if key == 'name':
                    continue
                if key == 'r':
                    if not isinstance(value, int) or not 0 <= value < 360:
                        fail(f'bad rotation for item {index}: {value!r}')
                elif key in NUM_KEYS:
                    if not isinstance(value, (int, float)):
                        fail(f'bad {key} for item {index}: {value!r}')
                else:
                    fail(f'unknown furniture key {key!r} on item {index}')


def summarise(state):
    rooms = sum(len(v) for v in (state.get('finishes') or {}).values())
    items = sum(len(v) for v in (state.get('furniture') or {}).values())
    globals_ = len(state.get('global') or {})
    saved = state.get('saved', '?')
    return f'saved {saved}: {globals_} global setting(s), {rooms} room finish(es), {items} furniture change(s)'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', nargs='?', help='exported JSON file, or - for stdin')
    parser.add_argument('--clear', action='store_true', help='drop back to the built-in defaults')
    args = parser.parse_args()

    if args.clear:
        payload, note = '{}', 'cleared: back to the built-in defaults'
    else:
        if not args.state:
            parser.error('give a state file (or - for stdin), or --clear')
        text = sys.stdin.read() if args.state == '-' else pathlib.Path(args.state).read_text(encoding='utf-8')
        try:
            state = json.loads(text)
        except json.JSONDecodeError as exc:
            fail(f'not valid JSON ({exc})')
        check(state)
        payload = json.dumps(state, ensure_ascii=False, separators=(',', ':'))
        note = summarise(state)

    source = SRC.read_text(encoding='utf-8')
    if len(ANCHOR.findall(source)) != 1:
        fail('could not find the savedState line in src/clinicwalkthrough.html')
    SRC.write_text(ANCHOR.sub(lambda _: 'const savedState=' + payload + ';', source, count=1), encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'apply-pwa-patch.py'), str(SRC)], check=True)
    print('apply-settings: ' + note)


if __name__ == '__main__':
    main()
