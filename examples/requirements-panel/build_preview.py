#!/usr/bin/env python3
"""Wrap the versioned, self-contained panel fragment for local browser review."""
import hashlib
import json
from pathlib import Path


def main():
    directory = Path(__file__).resolve().parent
    fragment_path = directory / 'panel.fragment.html'
    fragment = fragment_path.read_text(encoding='utf-8')
    shell = '''<!doctype html>
<html lang="zh-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src data:; object-src 'none'; base-uri 'none'; form-action 'none'">
<title>Pea Princess · 需求面板範例</title>
<style>:root{color-scheme:light dark}body{margin:0;padding:16px}#pea-requirements-preview{max-width:1088px;margin:auto}@media(max-width:420px){body{padding:8px}}</style>
</head>
<body>
'''
    destination = directory / 'index.html'
    destination.write_text(shell + fragment + '\n</body>\n</html>\n', encoding='utf-8')
    print(json.dumps({
        'output': str(destination),
        'fragment_sha256': hashlib.sha256(fragment.encode('utf-8')).hexdigest(),
        'model_calls': 0,
    }))


if __name__ == '__main__':
    main()
