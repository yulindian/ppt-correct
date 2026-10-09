import copy
import hashlib
import importlib.util
import zipfile
import json
import subprocess
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('ledger', Path(__file__).parents[1] / 'scripts/validate_ledger.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def fixture(tmp_path):
    deck = tmp_path / 'demo_动画版.pptx'
    with zipfile.ZipFile(deck, 'w') as z:
        z.writestr('ppt/presentation.xml', '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>')
        z.writestr('ppt/_rels/presentation.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="slides/slide2.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"/></Relationships>')
        z.writestr('ppt/slides/slide2.xml', '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:grpSp><p:sp><p:nvSpPr><p:cNvPr id="7"/></p:nvSpPr><p:txBody><a:p><a:r><a:t>Answer</a:t></a:r></a:p></p:txBody></p:sp></p:grpSp><p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="9"/></p:nvGraphicFramePr><a:graphic><a:graphicData><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>Cell</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl></a:graphicData></a:graphic></p:graphicFrame></p:spTree></p:cSld></p:sld>')
    pdf = tmp_path / 'source.pdf'
    pdf.write_bytes(b'reference fixture')
    images = []
    for name in ('reference.png', 'render.png'):
        p = tmp_path / name
        p.write_bytes(name.encode())
        images.append({'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    review = {'pptxSha256': hashlib.sha256(deck.read_bytes()).hexdigest(), 'sourcePdfSha256': hashlib.sha256(pdf.read_bytes()).hexdigest(), 'pages': [{'slide': 1, 'referencePage': 1, 'referenceImage': images[0], 'renderImage': images[1], 'pageChecks': {k: 'pass' for k in ('content', 'size', 'position', 'color')}, 'objects': [{'shapeId': n, 'checks': {k: 'pass' for k in ('content', 'size', 'position', 'color')}, 'referenceTargets': {'size': 'PDF glyph height matched', 'position': 'PDF card inset and baseline matched', 'color': 'PDF base blue, emphasis red'}} for n in (7, 9)]}]}
    return {'version': 2, 'state': 'verified-final', 'sourcePdf': str(pdf), 'outputPptx': str(deck), 'items': [], 'gates': {k: 'pass' for k in ('staticVisual', 'fontPage', 'animationTimeline', 'deliveryApplication')}, 'visualReview': review}


def test_complete_review_passes(tmp_path):
    assert M.validate_ledger(fixture(tmp_path)) == []


@pytest.mark.parametrize('mutation, expected', [
    ('missing_review', 'visualReview'), ('missing_object', 'coverage'),
    ('missing_page', 'coverage'), ('unchecked_color', 'color'),
    ('missing_target', 'referenceTargets'), ('stale_deck', 'pptxSha256'),
    ('stale_pdf', 'sourcePdfSha256'), ('missing_gate', 'fontPage'),
    ('na_gate', 'staticVisual'), ('duplicate_object', 'duplicate'),
    ('missing_image', 'evidence'), ('changed_image', 'evidence'),
])
def test_incomplete_or_stale_review_is_blocked(tmp_path, mutation, expected):
    d = fixture(tmp_path)
    page = d['visualReview']['pages'][0]
    if mutation == 'missing_review': del d['visualReview']
    elif mutation == 'missing_object': page['objects'].pop()
    elif mutation == 'missing_page': d['visualReview']['pages'] = []
    elif mutation == 'unchecked_color': page['objects'][0]['checks']['color'] = 'pending'
    elif mutation == 'missing_target': del page['objects'][0]['referenceTargets']['size']
    elif mutation == 'stale_deck': d['visualReview']['pptxSha256'] = 'old'
    elif mutation == 'stale_pdf': Path(d['sourcePdf']).write_bytes(b'changed')
    elif mutation == 'missing_gate': del d['gates']['fontPage']
    elif mutation == 'na_gate': d['gates']['staticVisual'] = 'not-applicable'
    elif mutation == 'duplicate_object': page['objects'].append(copy.deepcopy(page['objects'][0]))
    elif mutation == 'missing_image': Path(page['renderImage']['path']).unlink()
    elif mutation == 'changed_image': Path(page['renderImage']['path']).write_bytes(b'changed')
    assert any(expected in e for e in M.validate_ledger(d))


def test_legacy_self_attestation_cannot_be_final():
    d = {'version': 1, 'state': 'verified-final', 'outputPptx': 'x_动画版.pptx', 'items': [], 'gates': {'staticVisual': 'pass'}}
    assert M.validate_ledger(d)


def test_empty_exception_reference_cannot_bypass_review(tmp_path):
    d = fixture(tmp_path)
    d['visualReview']['pages'][0]['pageChecks'] = {k: {} for k in M.CHECKS}
    d['items'] = [{'status': 'accepted-exception', 'exception': 'ok'}]
    assert M.validate_ledger(d)


def test_explicit_documented_exception_can_pass(tmp_path):
    d = fixture(tmp_path)
    d['items'] = [{'id': 'exception-1', 'status': 'accepted-exception', 'exception': {
        'limitation': 'font differs', 'attemptedRepairs': 'tested available faces',
        'acceptanceEvidence': 'user message explicitly accepts this font difference',
        'acceptedBy': 'user', 'acceptedAt': '2026-10-05'}}]
    d['visualReview']['pages'][0]['objects'][0]['checks']['size'] = {'exceptionItem': 'exception-1'}
    assert M.validate_ledger(d) == []


def test_cli_inventory_is_pending_and_completed_ledger_passes(tmp_path):
    d = fixture(tmp_path)
    result = subprocess.run([sys.executable, '-X', 'utf8', str(M.__file__), '--inventory-pptx', d['outputPptx']], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    template = json.loads(result.stdout)
    assert [o['shapeId'] for o in template['pages'][0]['objects']] == [7, 9]
    assert template['pages'][0]['objects'][0]['checks']['size'] == 'pending'
    ledger = tmp_path / 'ledger.json'
    ledger.write_text(json.dumps(d), encoding='utf-8-sig')
    result = subprocess.run([sys.executable, '-X', 'utf8', str(M.__file__), '--ledger', str(ledger)], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['passed']
