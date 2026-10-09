import hashlib
import importlib.util
import json
import subprocess
import sys
import zipfile
import shutil
import pytest
from pathlib import Path

from test_review_coverage import fixture, M

SCRIPTS = Path(__file__).parents[1] / 'scripts'


def run(name, *args):
    return subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPTS / name), *map(str, args)], capture_output=True, text=True, encoding='utf-8')


def test_inventory_output_file_avoids_full_stdout(tmp_path):
    d = fixture(tmp_path)
    output = tmp_path / 'inventory.json'
    r = run('validate_ledger.py', '--inventory-pptx', d['outputPptx'], '--output', output)
    assert r.returncode == 0, r.stderr
    assert len(json.loads(output.read_text())['pages']) == 1
    assert 'pages' not in json.loads(r.stdout)
    assert 'readback' in json.loads(output.read_text())['pages'][0]['objects'][0]


def test_shared_targets_are_validated_and_bound(tmp_path):
    d = fixture(tmp_path)
    obj = d['visualReview']['pages'][0]['objects'][0]
    targets = obj.pop('referenceTargets')
    d['visualReview']['styleTargets'] = {'answer': targets}
    obj['targetRef'] = 'answer'
    obj['targetSha256'] = hashlib.sha256(json.dumps(targets, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    assert M.validate_ledger(d) == []
    targets['size'] = 'changed size'
    assert any('targetSha256' in e for e in M.validate_ledger(d))


def test_report_summary_keeps_full_file_and_failure_status(tmp_path):
    query = tmp_path / 'query.json'
    query.write_text(json.dumps({'results': []}))
    contract = tmp_path / 'contract.json'
    contract.write_text(json.dumps({'peerGroups': [{'slide': 1, 'shapeIds': [7], 'expectedCount': 1}]}))
    report = tmp_path / 'report.json'
    r = run('audit_ppt_layout_contract.py', '--query-json', query, '--contract', contract, '--report', report)
    assert r.returncode != 0
    assert 'issues' not in json.loads(r.stdout)
    assert json.loads(report.read_text())['issues']


def test_refresh_preserves_only_unchanged_review(tmp_path):
    d = fixture(tmp_path)
    ledger = tmp_path / 'ledger.json'
    ledger.write_text(json.dumps(d))
    cmd = ('refresh', '--ledger', ledger, '--pptx', d['outputPptx'], '--render-context', 'WPS-installed-fonts-v1')
    r = run('ppt_correct.py', *cmd)
    assert r.returncode == 0, r.stderr
    first = json.loads(ledger.read_text())
    assert first['visualReview']['pages'][0]['pageChecks']['size'] == 'pending'
    first['visualReview']['pages'][0]['pageChecks']['size'] = 'pass'
    ledger.write_text(json.dumps(first))
    r = run('ppt_correct.py', *cmd)
    assert r.returncode == 0, r.stderr
    assert json.loads(ledger.read_text())['visualReview']['pages'][0]['pageChecks']['size'] == 'pass'
    # Global rendering context (renderer/fonts) invalidates reuse.
    r = run('ppt_correct.py', *cmd[:-1], 'WPS-installed-fonts-v2')
    assert r.returncode == 0, r.stderr
    assert json.loads(ledger.read_text())['visualReview']['pages'][0]['pageChecks']['size'] == 'pending'


def test_refresh_tracks_related_media_changes(tmp_path):
    d = fixture(tmp_path)
    deck = Path(d['outputPptx'])
    with zipfile.ZipFile(deck, 'a') as z:
        z.writestr('ppt/slides/_rels/slide2.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="image1" Target="../media/image1.png"/></Relationships>')
        z.writestr('ppt/media/image1.png', b'old image')
    ledger = tmp_path / 'ledger.json'
    ledger.write_text(json.dumps(d))
    cmd = ('refresh', '--ledger', ledger, '--pptx', deck, '--render-context', 'fixed')
    assert run('ppt_correct.py', *cmd).returncode == 0
    saved = json.loads(ledger.read_text())
    saved['visualReview']['pages'][0]['pageChecks']['position'] = 'pass'
    ledger.write_text(json.dumps(saved))
    with zipfile.ZipFile(deck) as z:
        parts = {name: z.read(name) for name in z.namelist()}
    parts['ppt/media/image1.png'] = b'new image'
    with zipfile.ZipFile(deck, 'w') as z:
        for name, value in parts.items(): z.writestr(name, value)
    assert run('ppt_correct.py', *cmd).returncode == 0
    assert json.loads(ledger.read_text())['visualReview']['pages'][0]['pageChecks']['position'] == 'pending'


def test_check_records_failures_without_finalizing(tmp_path):
    d = fixture(tmp_path)
    ledger = tmp_path / 'ledger.json'
    ledger.write_text(json.dumps(d))
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'expectedSlideCount': 1, 'layoutApplicable': False}))
    r = run('ppt_correct.py', 'check', '--ledger', ledger, '--config', config, '--phase', 'static', '--report-dir', tmp_path / 'reports')
    assert r.returncode == 1, r.stdout + r.stderr
    updated = json.loads(ledger.read_text())
    assert updated['state'] == 'working'
    assert updated['gates']['fontPage'] == 'fail'
    assert (tmp_path / 'reports/font-page.log').is_file()
    assert 'Traceback' not in r.stdout


def test_global_relationship_change_invalidates_review_and_all_gates(tmp_path):
    d = fixture(tmp_path)
    ledger = tmp_path / 'ledger.json'
    ledger.write_text(json.dumps(d))
    cmd = ('refresh', '--ledger', ledger, '--pptx', d['outputPptx'], '--render-context', 'fixed')
    assert run('ppt_correct.py', *cmd).returncode == 0
    saved = json.loads(ledger.read_text())
    saved['visualReview']['pages'][0]['pageChecks']['size'] = 'pass'
    saved['gates']['layout'] = 'pass'
    ledger.write_text(json.dumps(saved))
    deck = Path(d['outputPptx'])
    with zipfile.ZipFile(deck) as z: parts = {n: z.read(n) for n in z.namelist()}
    parts['ppt/_rels/presentation.xml.rels'] = parts['ppt/_rels/presentation.xml.rels'].replace(b'</Relationships>', b'<Relationship Id="font1" Target="fonts/f1.fntdata"/></Relationships>')
    parts['ppt/fonts/f1.fntdata'] = b'font fixture'
    with zipfile.ZipFile(deck, 'w') as z:
        for n, v in parts.items(): z.writestr(n, v)
    assert run('ppt_correct.py', *cmd).returncode == 0
    saved = json.loads(ledger.read_text())
    assert saved['gates']['layout'] == 'pending'
    # After review, changing only a global relationship must invalidate it again.
    saved['visualReview']['pages'][0]['pageChecks']['size'] = 'pass'
    ledger.write_text(json.dumps(saved))
    parts['ppt/_rels/presentation.xml.rels'] = parts['ppt/_rels/presentation.xml.rels'].replace(b'Id="font1"', b'Id="font2"')
    with zipfile.ZipFile(deck, 'w') as z:
        for n, v in parts.items(): z.writestr(n, v)
    assert run('ppt_correct.py', *cmd).returncode == 0
    assert json.loads(ledger.read_text())['visualReview']['pages'][0]['pageChecks']['size'] == 'pending'


@pytest.mark.skipif(not shutil.which('officecli') or not shutil.which('pwsh'), reason='requires existing OfficeCLI/PowerShell')
def test_animation_audit_uses_presentation_order(tmp_path):
    deck = tmp_path / 'renumbered.pptx'
    generated = subprocess.run([sys.executable, str(SCRIPTS.parent / 'tests/make_animation_fixture.py'), str(deck)], capture_output=True)
    assert generated.returncode == 0
    with zipfile.ZipFile(deck) as z: parts = {n: z.read(n) for n in z.namelist()}
    parts['ppt/slides/slide7.xml'] = parts.pop('ppt/slides/slide1.xml')
    for name in ('ppt/_rels/presentation.xml.rels', '[Content_Types].xml'):
        parts[name] = parts[name].replace(b'slide1.xml', b'slide7.xml')
    if 'ppt/slides/_rels/slide1.xml.rels' in parts:
        parts['ppt/slides/_rels/slide7.xml.rels'] = parts.pop('ppt/slides/_rels/slide1.xml.rels')
    with zipfile.ZipFile(deck, 'w') as z:
        for n, v in parts.items(): z.writestr(n, v)
    plan = tmp_path / 'plan.json'
    plan.write_text(json.dumps({'slides': {'1': {'orderedShapeIds': [2, 3, 4]}}}))
    r = subprocess.run(['pwsh', '-NoProfile', '-File', str(SCRIPTS / 'audit-ppt-animation.ps1'), '-PptPath', str(deck), '-PlanPath', str(plan), '-FailOnMismatch'], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)['planMismatchCount'] == 0
