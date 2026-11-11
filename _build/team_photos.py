#!/usr/bin/env python3
"""Prepare team photos for the Meet the team page.

    python3 _build/team_photos.py && python3 _build/build.py

Put each original photo in team-photos/ (in the website folder, not published), named like the
"photo" value in _build/team.py, e.g. team-photos/carolina-jaramillo.jpg. This script cuts each
person out onto a pure white background, frames a 4:5 portrait and saves assets/team/<name>.webp.
Needs macOS 14+, the Xcode command line tools and cwebp (brew install webp).
"""
import glob, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC, OUT = os.path.join(ROOT, 'team-photos'), os.path.join(ROOT, 'assets', 'team')
BIN = os.path.join(tempfile.gettempdir(), 'mc-cutout')
LEVEL = {'angie-pineda'}   # tilted (selfie) photos: rotate so the eyes are level
MIRROR_LEFT = {'angie-pineda'}
WIDEN = {'angie-pineda': '1.28'}   # narrow selfie shoulders: widen the body below the chin to fill the frame   # raised selfie arm on the frame's right: mirror the natural left shoulder

if not shutil.which('cwebp'):
    sys.exit('cwebp not found: brew install webp')
if not os.path.exists(BIN) or os.path.getmtime(BIN) < os.path.getmtime(os.path.join(HERE, 'cutout.swift')):
    sdks = sorted(glob.glob('/Library/Developer/CommandLineTools/SDKs/MacOSX14*.sdk'))   # matches the Swift 5.10 compiler
    cmd = ['swiftc', '-O', os.path.join(HERE, 'cutout.swift'), '-o', BIN] + (['-sdk', sdks[-1]] if sdks else [])
    if subprocess.run(cmd).returncode:
        sys.exit('could not compile _build/cutout.swift')

os.makedirs(OUT, exist_ok=True)
photos = [f for f in sorted(os.listdir(SRC)) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.webp'))] if os.path.isdir(SRC) else []
if not photos:
    sys.exit('No photos in team-photos/')
for f in photos:
    name = os.path.splitext(f)[0]
    png = os.path.join(tempfile.gettempdir(), name + '-white.png')
    r = subprocess.run([BIN, os.path.join(SRC, f), png] + (['--level'] if name in LEVEL else []) + (['--mirror-left'] if name in MIRROR_LEFT else []) + (['--widen', WIDEN[name]] if name in WIDEN else []), capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'{f}: {r.stdout.strip() or r.stderr.strip()}')
    subprocess.run(['cwebp', '-quiet', '-q', '82', png, '-o', os.path.join(OUT, name + '.webp')], check=True)
    os.unlink(png)
    print('  team photo', name)
