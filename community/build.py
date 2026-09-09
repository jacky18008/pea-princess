#!/usr/bin/env python3
"""Build the standalone local community form; no downloads or publishing."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys

if __package__:
    from . import core, feedback
else:
    import core
    import feedback


def embedded(value):
    return json.dumps(value, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def hash_source(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def render(places):
    core.catalog(places)
    source = (core.HERE / 'form.js').read_text()
    if '</script' in source.lower():
        raise core.Rejected('unsafe_script_source')
    template = (core.HERE / 'form.html').read_text()
    styles = re.findall(r'<style>(.*?)</style>', template, re.S)
    csp = "default-src 'none'; script-src %s; style-src %s; connect-src 'none'; base-uri 'none'; form-action 'none'; object-src 'none'" % (
        hash_source(source), ' '.join(hash_source(style) for style in styles))
    replacements = {'__COMMUNITY_SCHEMA_JSON__': embedded(core.schema(places)),
                    '__COMMUNITY_CATALOG_JSON__': embedded(places),
                    '__COMMUNITY_SCRIPT__': source, '__COMMUNITY_CSP__': csp}
    for key, value in replacements.items():
        if template.count(key) != 1:
            raise core.Rejected('invalid_build_template')
        template = template.replace(key, value)
    return template


def main(argv=None):
    try:
        parser = feedback.Parser(description=__doc__)
        parser.add_argument('--catalog', default=str(core.HERE / 'catalog.json'))
        parser.add_argument('--out', default=str(core.HERE / 'index.html'))
        parser.add_argument('--schema-out', default=str(core.HERE / 'public-schema.json'))
        args = parser.parse_args(argv)
        places = core.load_catalog(args.catalog)
        html = render(places)
        output, schema_output = feedback.safe_path(args.out), feedback.safe_path(args.schema_out)
        protected = {Path(args.catalog).resolve(), core.HERE / 'form.html', core.HERE / 'form.js'}
        if output.resolve() in protected or schema_output.resolve() in protected:
            raise core.Rejected('build_output_conflicts_with_source')
        if output == schema_output or output.suffix != '.html' or schema_output.suffix != '.json':
            raise core.Rejected('invalid_build_destinations')
        for path in (output, schema_output):
            if path.exists() and not path.is_file():
                raise core.Rejected('output_must_be_regular_file')
            path.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding='utf-8')
        schema_output.write_text(json.dumps(core.schema(places), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'ok': True, 'status': 'built_local_only', 'demo': places['demo']}))
        return 0
    except (core.Rejected, OSError, ValueError):
        print(json.dumps({'ok': False, 'error': 'local_build_failed'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
