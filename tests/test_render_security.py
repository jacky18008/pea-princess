"""Untrusted report text and viewer import state; no browser, network or model calls."""
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/vet-flat/scripts'))
import render


def sample():
    return json.loads((ROOT / 'tests/fixtures/report-sample.json').read_text())


class ReportTextBoundary(unittest.TestCase):
    def setUp(self):
        self.labels = render.Labels(render.load_glossary(str(ROOT / 'skills/vet-flat/references/glossary.yaml')), 'en')

    def test_markdown_report_text_cannot_introduce_active_html_images_or_links(self):
        data = sample()
        payload = '<img src="https://invalid.example/pixel" onerror="alert(1)">' \
                  '<script>alert(1)</script> ![photo](https://invalid.example/pixel) ' \
                  '[open](javascript:alert(1)) &#60;img src=x&#62;'
        data['candidates'][0]['verdict']['headline'] = payload
        data['candidates'][0]['axes'][0]['finding'] = payload
        data['profile_snapshot']['my_questions'] = [payload]
        data['profile_snapshot'][payload] = 'user-defined profile label'
        before = copy.deepcopy(data)
        output = render.render_markdown(data, self.labels)
        for active in ('<img ', '<script>', '![photo]', '[open](javascript:', '&#60;img'):
            self.assertNotIn(active, output)
        self.assertIn('&lt;img ', output)
        self.assertIn(r'!\[photo\]', output)
        self.assertIn(r'\[open\](javascript:', output)
        self.assertIn('## 1. Verdict', output)
        self.assertEqual(before, data)

    def test_html_renderer_escapes_attribute_and_element_breakout(self):
        data = sample()
        data['candidates'][0]['verdict']['headline'] = '</p><script>alert(1)</script>'
        data['sources'][0]['url'] = 'https://invalid.example/" onclick="alert(1)'
        output = render.HtmlRenderer(data, self.labels).render()
        self.assertNotIn('<script>', output)
        self.assertNotIn('href="https://invalid.example/" onclick=', output)
        self.assertIn('&lt;script&gt;', output)
        self.assertIn('&quot; onclick=&quot;', output)


@unittest.skipUnless(shutil.which('node'), 'Node is optional; needed to execute the offline viewer logic')
class ViewerImportBoundary(unittest.TestCase):
    def test_failed_import_never_leaves_a_previous_report_or_share_card_available(self):
        # DOM is a tiny local stub. The test executes the real page script without
        # opening a browser or giving it networking/file access.
        script = re.search(r'<script>\s*(.*?)</script>',
                           (ROOT / 'viewer/viewer.html').read_text(), re.S).group(1)
        harness = r'''
const vm = require('node:vm');
const assert = require('node:assert/strict');
const elements = new Map();
function get(id) {
  if (!elements.has(id)) elements.set(id, {value: '', innerHTML: '', textContent: '',
    style: {}, addEventListener() {}, remove() {}, select() {}});
  return elements.get(id);
}
const context = {document: {getElementById: get,
  documentElement: {lang: 'en', setAttribute() {}, removeAttribute() {}},
  querySelector() {return {textContent: ''};}}, navigator: {}, setTimeout() {}};
vm.createContext(context);
vm.runInContext(SCRIPT, context);
const originalFinding = context.SAMPLE.candidates[0].axes.find(axis => axis.id === 10).finding;
for (const lang of ['en', 'zh-TW', 'zh-CN']) {
  const labels = new context.Labels(lang);
  const output = context.renderBody(context.SAMPLE, labels);
  const configuration = context.esc(context.configLine(context.SAMPLE, labels));
  const about = output.indexOf('<h2 id="about">');
  assert.ok(about >= 0);
  assert.equal(output.split(configuration).length - 1, 1);
  assert.ok(output.indexOf(configuration) > about);
  assert.ok(output.includes(labels.label('ui.all_in_pcm')));
  for (const key of ['axis.10', 'ui.all_in_pcm', 'ui.all_in_planning',
                      'ui.arith_all_in_low', 'ui.arith_all_in_planning', 'ui.arith_all_in_stress']) {
    assert.doesNotMatch(labels.label(key), /all-in/i);
  }
}
assert.equal(context.SAMPLE.candidates[0].axes.find(axis => axis.id === 10).finding, originalFinding);
assert.equal(context.sBand(2400), '£2,000–2,400 total per month');
assert.equal(JSON.stringify(context.FORMULAS), JSON.stringify(FORMULAS));
for (const bad of ['{', 'null', '[]', '{"candidates":[null]}',
                   JSON.stringify({...context.SAMPLE, candidates: [{}]})]) {
  get('json').value = JSON.stringify(context.SAMPLE);
  context.run();
  assert.ok(context.current, get('messages').innerHTML);
  assert.ok(get('report').innerHTML);
  get('json').value = bad;
  assert.doesNotThrow(() => context.run());
  assert.equal(context.current, null);
  assert.equal(get('report').innerHTML, '');
  assert.equal(get('share').innerHTML, '');
  assert.match(get('messages').innerHTML, /not valid JSON|cannot be rendered/);
}
const privateText = 'Contact Sample Person at 123 Example Road, funds £12345';
const card = context.shareBlock({profile_snapshot: {my_questions: [privateText]}});
assert.match(card, /free text is not anonymized/);
assert.match(card, /Read the card below and remove personal details/);
assert.ok(card.includes(privateText)); // no false claim of complete anonymization
console.log('viewer import and sharing checks passed');
'''.replace('SCRIPT', json.dumps(script)).replace('JSON.stringify(FORMULAS)',
                                                'JSON.stringify(' + json.dumps(render.FORMULAS) + ')')
        result = subprocess.run(['node', '-'], input=harness, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == '__main__':
    unittest.main()
