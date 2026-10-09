"""Small workflow entry point; never invents visual review or edits PPT content."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import posixpath
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from validate_ledger import NS, CHECKS, digest, inventory, target_digest, validate_ledger, validate_review

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def fingerprints(path):
    """Hash each slide's transitive package dependencies; cycles are expected."""
    result = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        presentation = ET.fromstring(z.read('ppt/presentation.xml'))
        rels = ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
        targets = {r.get('Id'): r.get('Target') for r in rels}
        slide_parts = []
        for node in presentation.findall('p:sldIdLst/p:sldId', NS):
            target = targets[node.get('{%s}id' % NS['r'])]
            slide_parts.append(target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/' + target))
        ids = presentation.find('p:sldIdLst', NS)
        if ids is not None:
            presentation.remove(ids)
        # Embedded font and global presentation setting changes invalidate all.
        global_hash = hashlib.sha256(ET.tostring(presentation))
        for name in sorted(names):
            if name.startswith('ppt/fonts/') or name in ('[Content_Types].xml', 'ppt/presProps.xml', 'ppt/viewProps.xml', 'ppt/_rels/presentation.xml.rels'):
                global_hash.update(name.encode() + z.read(name))
        for part in slide_parts:
            visited = set()
            external = False
            def visit(name):
                nonlocal external
                if name in visited:
                    return
                visited.add(name)
                if name not in names:
                    raise ValueError(f'missing related package part: {name}')
                relname = posixpath.join(posixpath.dirname(name), '_rels', posixpath.basename(name) + '.rels')
                if relname not in names:
                    return
                visited.add(relname)
                for rel in ET.fromstring(z.read(relname)):
                    if rel.get('TargetMode') == 'External':
                        # Linked content is not captured by package hashes.
                        external = True
                        continue
                    target = rel.get('Target')
                    visit(target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(name), target)))
            visit(part)
            for relation in rels:
                target = relation.get('Target')
                resolved = target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/' + target)
                if resolved in slide_parts:
                    continue
                if relation.get('TargetMode') == 'External':
                    external = True
                else:
                    visit(resolved)
            h = hashlib.sha256(global_hash.digest())
            for name in sorted(visited):
                h.update(name.encode() + b'\0' + hashlib.sha256(z.read(name)).digest())
            result.append({'dependencySha256': h.hexdigest(), 'cacheable': not external})
    return result


def refresh(data, pptx, context):
    old = data.get('visualReview') or {}
    new = inventory(pptx)
    new['sourcePdfSha256'] = digest(Path(data['sourcePdf']))
    new['renderContext'] = context
    new['styleTargets'] = old.get('styleTargets', {})
    old_pages = {p['slide']: p for p in old.get('pages', [])}
    changed = []
    for page, binding in zip(new['pages'], fingerprints(pptx)):
        page.update(binding)
        previous = old_pages.get(page['slide'], {})
        reusable = (binding['cacheable'] and old.get('renderContext') == context
                    and new['sourcePdfSha256'] == old.get('sourcePdfSha256')
                    and previous.get('dependencySha256') == binding['dependencySha256'])
        for obj in previous.get('objects', []):
            if 'targetRef' in obj:
                target = new['styleTargets'].get(obj['targetRef'])
                if not isinstance(target, dict) or obj.get('targetSha256') != target_digest(target):
                    reusable = False
        if reusable:
            page.update(copy.deepcopy(previous))
        else:
            changed.append(page['slide'])
            page['referencePage'] = previous.get('referencePage')
            page['referenceImage'] = previous.get('referenceImage') if new['sourcePdfSha256'] == old.get('sourcePdfSha256') else None
            peers = {o['shapeId']: o for o in previous.get('objects', [])}
            for obj in page['objects']:
                peer = peers.get(obj['shapeId'], {})
                for key in ('referenceTargets', 'targetRef', 'targetSha256'):
                    if key in peer:
                        obj[key] = copy.deepcopy(peer[key])
                # Preserve intended targets only; actual checks/render are reset.
    data['version'] = 2
    data['state'] = 'working'
    data['outputPptx'] = str(pptx.resolve())
    data['visualReview'] = new
    gates = data.setdefault('gates', {})
    if old.get('pptxSha256') != new['pptxSha256'] or changed:
        for key in list(gates):
            if gates[key] != 'not-applicable':
                gates[key] = 'pending'
        for key in ('staticVisual', 'fontPage', 'animationTimeline'):
            gates[key] = 'pending'
        if gates.get('deliveryApplication') != 'not-applicable':
            gates['deliveryApplication'] = 'pending'
    return {'reviewPages': changed, 'reusedPages': len(new['pages']) - len(changed),
            'nextAction': 'Review pending pages against the PDF; do not bulk-fill pass.' if changed else 'Run applicable machine checks; confirm evidence still exists.'}


def checks(data, config, phase, report_dir):
    """Run fixed local auditors using an explicit config, never arbitrary commands."""
    pptx = Path(data['outputPptx']).resolve()
    reports = []
    gates = data.setdefault('gates', {})
    visual_errors = validate_review(data)
    gates['staticVisual'] = 'fail' if visual_errors else 'pass'
    font_report = report_dir / 'font-page.json'
    if type(config.get('expectedSlideCount')) is not int or config['expectedSlideCount'] < 1:
        raise ValueError('config requires positive expectedSlideCount')
    args = ['--final', str(pptx), '--report', str(font_report), '--expected-slide-count', str(config['expectedSlideCount']), '--require-font-files-for-used-fonts']
    for family, path in config.get('fontFiles', {}).items():
        args += ['--font-file', f'{family}={path}']
    for family in config.get('allowUnembeddedFonts', []):
        args += ['--allow-unembedded-font', family]
    commands = [('fontPage', [sys.executable, '-X', 'utf8', str(ROOT / 'verify_pptx_fonts_pages_size.py'), *args], font_report)]
    # Explicitly declare applicability so absence cannot silently skip layout QA.
    if type(config.get('layoutApplicable')) is not bool:
        raise ValueError('config requires layoutApplicable boolean')
    if config['layoutApplicable']:
        if not config.get('layoutContract'):
            raise ValueError('layoutApplicable requires layoutContract')
        report = report_dir / 'layout.json'
        commands.append(('layout', [sys.executable, '-X', 'utf8', str(ROOT / 'audit_ppt_layout_contract.py'), '--pptx', str(pptx), '--contract', config['layoutContract'], '--report', str(report)], report))
    else:
        gates['layout'] = 'not-applicable'
    if phase == 'final':
        if not config.get('animationPlan'):
            raise ValueError('final checks require animationPlan')
        commands.append(('animationTimeline', ['pwsh', '-NoProfile', '-File', str(ROOT / 'audit-ppt-animation.ps1'), '-PptPath', str(pptx), '-PlanPath', config['animationPlan'], '-FailOnMismatch'], report_dir / 'animation.json'))
    for gate, command, report in commands:
        completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        gates[gate] = 'pass' if completed.returncode == 0 else 'fail'
        # Log tool output to disk; only gate status/path reaches the model.
        log = report.with_suffix('.log')
        log.write_text(completed.stdout + '\n' + completed.stderr, encoding='utf-8')
        reports.append({'gate': gate, 'passed': completed.returncode == 0, 'log': str(log)})
    passed = not visual_errors and all(r['passed'] for r in reports)
    if phase == 'final' and passed:
        candidate = {**data, 'state': 'verified-final'}
        final_errors = validate_ledger(candidate)
        passed = not final_errors
        visual_errors.extend(final_errors)
    data['state'] = 'working'  # Publishing/final naming remains an explicit workflow step.
    return {'passed': passed, 'checks': reports, 'reviewErrors': visual_errors[:10],
            'errorCount': len(visual_errors), 'nextAction': 'Complete target-application/OfficeCLI checks and final ledger validation.' if passed else 'Resolve failing gates and review errors; rerun checks.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    refresh_parser = sub.add_parser('refresh')
    refresh_parser.add_argument('--ledger', type=Path, required=True)
    refresh_parser.add_argument('--pptx', type=Path, required=True)
    refresh_parser.add_argument('--render-context', required=True, help='Stable renderer/version/font-environment identity; update whenever that environment changes')
    check_parser = sub.add_parser('check')
    check_parser.add_argument('--ledger', type=Path, required=True)
    check_parser.add_argument('--config', type=Path, required=True)
    check_parser.add_argument('--phase', choices=('static', 'final'), required=True)
    check_parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        data = read(args.ledger)
        if args.command == 'refresh':
            if args.ledger.resolve() in {args.pptx.resolve(), Path(data['sourcePdf']).resolve()}:
                raise ValueError('ledger must be separate from source files')
            report = refresh(data, args.pptx, args.render_context)
        else:
            args.report_dir.mkdir(parents=True, exist_ok=True)
            report = checks(data, read(args.config), args.phase, args.report_dir)
            save(args.report_dir / 'workflow.json', report)
        save(args.ledger.with_suffix('.previous.json'), read(args.ledger))
        save(args.ledger, data)
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report.get('passed', True) else 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(json.dumps({'passed': False, 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
