from __future__ import annotations

import argparse
import json
import sys
import hashlib
import posixpath
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path


STATES = {"working", "candidate", "verified-final", "failed"}
ITEM_STATUSES = {"open", "closed", "accepted-exception"}
GATE_STATUSES = {"pending", "pass", "fail", "unavailable", "not-applicable"}
CHECKS = ('content', 'size', 'position', 'color')
EXCEPTION_FIELDS = ('limitation', 'attemptedRepairs', 'acceptanceEvidence', 'acceptedBy', 'acceptedAt')
NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def documented_exception(item: dict) -> bool:
    evidence = item.get('exception')
    return (isinstance(item.get('id'), str) and bool(item['id'].strip())
            and item.get('status') == 'accepted-exception'
            and isinstance(evidence, dict)
            and all(isinstance(evidence.get(k), str) and evidence[k].strip() for k in EXCEPTION_FIELDS))


def target_digest(targets: dict) -> str:
    return hashlib.sha256(json.dumps(targets, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def inventory(path: Path) -> dict:
    """Read presentation order (not slide filenames), grouped text and tables.

    Chart/SmartArt, inherited master text and image-baked text require page
    review; this inventory deliberately does not claim to enumerate their glyphs.
    """
    pages = []
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read('ppt/presentation.xml'))
        rels = ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
        targets = {r.get('Id'): r.get('Target') for r in rels if r.get('TargetMode') != 'External'}
        for index, slide in enumerate(root.findall('p:sldIdLst/p:sldId', NS), 1):
            target = targets[slide.get('{%s}id' % NS['r'])]
            part = target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/' + target)
            xml = ET.fromstring(archive.read(part))
            objects = []
            for shape in xml.iter():
                if shape.tag not in {f"{{{NS['p']}}}sp", f"{{{NS['p']}}}graphicFrame"}:
                    continue
                text = '\n'.join(t.text or '' for t in shape.findall('.//a:t', NS)).strip()
                if not text:
                    continue
                identity = shape.find('.//p:cNvPr', NS)
                # Explicit OOXML only: inherited effective styling is still read
                # through OfficeCLI/renderer. Keep details on disk, not stdout.
                readback = {'explicitOnly': True,
                            'transforms': [ET.tostring(n, encoding='unicode') for tag in ('a:xfrm', 'p:xfrm') for n in shape.findall('.//' + tag, NS)],
                            'bodyProperties': [dict(n.attrib) for n in shape.findall('.//a:bodyPr', NS)],
                            'paragraphProperties': [ET.tostring(n, encoding='unicode') for n in shape.findall('.//a:pPr', NS)],
                            'runs': [{'text': ''.join(t.text or '' for t in n.findall('a:t', NS)),
                                      'properties': ET.tostring(n.find('a:rPr', NS), encoding='unicode') if n.find('a:rPr', NS) is not None else None}
                                     for n in shape.findall('.//a:r', NS)]}
                objects.append({'shapeId': int(identity.get('id')), 'text': text,
                                'readback': readback,
                                'checks': {k: 'pending' for k in CHECKS},
                                'referenceTargets': {k: '' for k in CHECKS[1:]}})
            pages.append({'slide': index, 'referencePage': None,
                          'referenceImage': None, 'renderImage': None,
                          'pageChecks': {k: 'pending' for k in CHECKS}, 'objects': objects})
    return {'pptxSha256': digest(path), 'sourcePdfSha256': None, 'pages': pages}


def validate_review(data: dict) -> list[str]:
    errors = []
    review = data.get('visualReview')
    if not isinstance(review, dict):
        return ['verified-final requires visualReview coverage']
    try:
        actual = inventory(Path(data['outputPptx']))
        if review.get('pptxSha256') != actual['pptxSha256']:
            errors.append('visualReview pptxSha256 is stale; recheck the saved delivery file')
        if review.get('sourcePdfSha256') != digest(Path(data['sourcePdf'])):
            errors.append('visualReview sourcePdfSha256 is stale')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, zipfile.BadZipFile, ET.ParseError) as exc:
        return [f'visualReview cannot read source/deck inventory: {exc}']

    def checks(value, label):
        if not isinstance(value, dict):
            errors.append(f'{label}: missing checks')
            return
        for key in CHECKS:
            if value.get(key) != 'pass':
                # An exception must point to an accepted item, not merely say N/A.
                result = value.get(key)
                accepted = isinstance(result, dict) and isinstance(result.get('exceptionItem'), str) and bool(result['exceptionItem'].strip()) and any(
                    isinstance(item, dict) and item.get('id') == result.get('exceptionItem')
                    and documented_exception(item)
                    for item in data.get('items', []))
                if not accepted:
                    errors.append(f'{label}: {key} is not reviewed/pass')

    pages = review.get('pages')
    if not isinstance(pages, list):
        return errors + ['visualReview page coverage must be an array']
    expected = {p['slide']: {o['shapeId'] for o in p['objects']} for p in actual['pages']}
    seen = set()
    for page in pages:
        if not isinstance(page, dict) or type(page.get('slide')) is not int:
            errors.append('visualReview invalid page coverage entry')
            continue
        slide = page['slide']
        if slide in seen:
            errors.append(f'duplicate page {slide}')
        seen.add(slide)
        if type(page.get('referencePage')) is not int or page['referencePage'] < 1:
            errors.append(f'slide {slide}: referencePage must identify the PDF page')
        checks(page.get('pageChecks'), f'slide {slide}')
        for key in ('referenceImage', 'renderImage'):
            evidence = page.get(key)
            try:
                if not isinstance(evidence, dict) or digest(Path(evidence['path'])) != evidence.get('sha256'):
                    raise ValueError('missing or changed file')
            except (OSError, KeyError, TypeError, ValueError) as exc:
                errors.append(f'slide {slide}: {key} evidence invalid: {exc}')
        objects = page.get('objects')
        if not isinstance(objects, list):
            errors.append(f'slide {slide}: object coverage must be an array')
            continue
        ids = set()
        for obj in objects:
            if not isinstance(obj, dict) or type(obj.get('shapeId')) is not int:
                errors.append(f'slide {slide}: invalid object coverage entry')
                continue
            sid = obj['shapeId']
            if sid in ids:
                errors.append(f'slide {slide}: duplicate shape {sid}')
            ids.add(sid)
            checks(obj.get('checks'), f'slide {slide} shape {sid}')
            targets = obj.get('referenceTargets')
            if 'targetRef' in obj:
                shared = review.get('styleTargets', {})
                ref = obj['targetRef']
                targets = shared.get(ref) if isinstance(shared, dict) and isinstance(ref, str) else None
                if isinstance(targets, dict) and obj.get('targetSha256') != target_digest(targets):
                    errors.append(f'slide {slide} shape {sid}: targetSha256 is stale; recheck shared target')
            if not isinstance(targets, dict) or any(not isinstance(targets.get(k), str) or not targets[k].strip() for k in CHECKS[1:]):
                errors.append(f'slide {slide} shape {sid}: referenceTargets requires size, position, color evidence')
        if ids != expected.get(slide, set()):
            errors.append(f'slide {slide}: object coverage mismatch; expected {sorted(expected.get(slide, set()))}, got {sorted(ids)}')
    if seen != set(expected):
        errors.append(f'page coverage mismatch; expected {sorted(expected)}, got {sorted(seen)}')
    return errors


def validate_ledger(data: dict) -> list[str]:
    errors: list[str] = []
    state = data.get("state")
    if state not in STATES:
        errors.append(f"invalid state: {state!r}")

    items = data.get("items")
    if not isinstance(items, list):
        errors.append("items must be an array")
        items = []
    item_ids = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"item {index} must be an object")
            continue
        status = item.get("status")
        if data.get('version') == 2:
            item_id = item.get('id')
            if not isinstance(item_id, str) or not item_id.strip():
                errors.append(f'item {index} requires a nonempty id')
            elif item_id in item_ids:
                errors.append(f'duplicate ledger item id: {item_id}')
            else:
                item_ids.add(item_id)
            if status == 'accepted-exception' and not documented_exception(item):
                errors.append(f'item {index} requires documented exception acceptance: {EXCEPTION_FIELDS}')
        if status not in ITEM_STATUSES:
            errors.append(f"item {item.get('id', index)!r} has invalid status: {status!r}")
        if status == "accepted-exception" and not item.get("exception"):
            errors.append(f"item {item.get('id', index)!r} is missing exception evidence")

    gates = data.get("gates")
    if not isinstance(gates, dict) or not gates:
        errors.append("gates must be a non-empty object")
        gates = {}
    for name, status in gates.items():
        if status not in GATE_STATUSES:
            errors.append(f"gate {name!r} has invalid status: {status!r}")

    output = data.get("outputPptx")
    output_name = Path(output).name if isinstance(output, str) and output else ""
    if state == "candidate" and not output_name.endswith("_动画版_候选.pptx"):
        errors.append("candidate output must end with _动画版_候选.pptx")
    if state == "verified-final":
        if data.get('version') != 2:
            errors.append('verified-final requires version 2 review coverage; legacy ledgers remain resumable')
        for gate in ('staticVisual', 'fontPage', 'animationTimeline'):
            if gates.get(gate) != 'pass':
                errors.append(f'required gate {gate} must pass')
        if gates.get('deliveryApplication') not in {'pass', 'not-applicable'}:
            errors.append('deliveryApplication must pass or be explicitly not-applicable')
        errors.extend(validate_review(data))
        if not output_name.endswith("_动画版.pptx") or output_name.endswith("_动画版_候选.pptx"):
            errors.append("verified-final output must end with _动画版.pptx")
        if any(item.get("status") == "open" for item in items if isinstance(item, dict)):
            errors.append("verified-final cannot contain an open ledger item")
        blocking_gates = {
            name: status
            for name, status in gates.items()
            if status not in {"pass", "not-applicable"}
        }
        if blocking_gates:
            errors.append(f"verified-final has unresolved gates: {blocking_gates}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a ppt-correct correction ledger")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ledger", type=Path)
    mode.add_argument("--inventory-pptx", type=Path, help="Emit pending visualReview JSON; never marks review complete")
    parser.add_argument('--output', type=Path, help='Write inventory/report to disk and print only a summary')
    args = parser.parse_args()

    if args.inventory_pptx:
        try:
            result = inventory(args.inventory_pptx)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps({'pageCount': len(result['pages']), 'objectCount': sum(len(p['objects']) for p in result['pages']), 'output': str(args.output.resolve())}))
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except (OSError, ValueError, KeyError, AttributeError, zipfile.BadZipFile, ET.ParseError) as exc:
            print(f'could not inventory PPTX: {exc}', file=sys.stderr)
            return 2

    try:
        data = json.loads(args.ledger.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"could not read ledger: {exc}", file=sys.stderr)
        return 2

    if not isinstance(data, dict):
        print("ledger root must be an object", file=sys.stderr)
        return 2

    errors = validate_ledger(data)
    report = {"passed": not errors, "state": data.get("state"), "errorCount": len(errors)}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({**report, 'errors': errors}, ensure_ascii=False, indent=2), encoding='utf-8')
        report['report'] = str(args.output.resolve())
    print(json.dumps(report, ensure_ascii=False))
    if errors:
        for error in errors[:10] if args.output else errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
