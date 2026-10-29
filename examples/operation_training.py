"""Prepare portable native Studio plans and verify evidence; never auto-run Studio."""
import argparse
import json
from pathlib import Path


def block(prototype, inputs=None, output=None, outputs=None):
    item = {'prototype': prototype, 'label': prototype, 'inputs': inputs or {}}
    if output is not None:
        item['output'] = output
    if outputs is not None:
        item['outputs'] = outputs
    return item


def expr(value):
    return {'expression': value}


def var(name, value, kind='any'):
    return block('programing.variable', {'value_type': kind, 'value': expr(value)}, output=name)


def prepare(directory, web_base_url='http://127.0.0.1:18765'):
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=False)
    fixture = root / 'inventory.html'
    fixture.write_text('''<!doctype html><meta charset="utf-8"><title>RPA training</title>
<label>库存阈值<input id="threshold" value="2"></label><button id="apply">筛选</button>
<table id="stock"><tr><th>商品</th><th>库存</th></tr>
<tr data-id="A"><td>笔</td><td>0</td></tr><tr data-id="B"><td>本</td><td>3</td></tr>
<tr data-id="C"><td>尺</td><td>1</td></tr></table><output id="result"></output>
<script>document.querySelector('#apply').onclick=()=>{
document.querySelector('#result').textContent=JSON.stringify(
[...document.querySelectorAll('#stock tr[data-id]')].filter(r=>Number(r.cells[1].textContent)<Number(document.querySelector('#threshold').value)).map(r=>r.dataset.id));};</script>''', encoding='utf-8')
    plans = {}
    plans['logic'] = [
        var('accepted', '[]', 'list'),
        block('workflow.forin', {'list': expr('[0, 0.5, 2, 0, 3, 1]'), 'loop_start_index': 0,
              'loop_end_index': -1, 'output_with_index': False}, outputs={'loop_item': 'current_hours'}),
        block('workflow.if', {'operand1': {'variable': 'current_hours'}, 'operator': '>', 'operand2': 0}),
        var('accepted', 'accepted + [current_hours]', 'list'),
        block('workflow.endif'), block('workflow.endloop'),
        var('training_result', "{'values': accepted, 'total': sum(accepted)}", 'dict')]
    text_path = str(root / 'native-order.txt')
    plans['file_wait_regex'] = [
        block('file.write', {'path': text_path, 'content': 'ORDER:A102;QTY:3', 'write_way': 'overwrite',
                            'is_text': True, 'new_line': False, 'encoding': 'UTF-8'}),
        block('file.wait', {'path': text_path, 'desired_state': 'created', 'is_wait': True, 'timeout_seconds': 2}, output='ready'),
        block('programing.sleep', {'random_number': False, 'seconds': 0.1, 'start_number': 1, 'stop_number': 1}),
        block('file.read', {'path': text_path, 'read_way': 'all_text', 'encoding': 'UTF-8'}, output='order_text'),
        var('training_result', "{'ready': ready, 'matches': __import__('re').findall(r'ORDER:([A-Z][0-9]+);QTY:([0-9]+)', order_text)}", 'dict')]
    plans['web_local'] = [
        block('web.create', {'web_type': 'chrome', 'value': web_base_url.rstrip('/') + '/inventory.html', 'silent_running': False,
              'wait_load_completed': True, 'load_timeout': 15, 'stop_load_if_load_timeout': 'handleExcept'}, output='training_browser'),
        block('web.browser.execute_javascript', {'browser': {'variable': 'training_browser'},
              'code': "function(){document.querySelector('#threshold').value='2';document.querySelector('#apply').click();return JSON.parse(document.querySelector('#result').textContent);}",
              'timeout': 10, 'execution_world': 'MAIN'}, output='training_result'),
        block('web.browser.close', {'operation': 'close_specified', 'browser': {'variable': 'training_browser'},
              'task_kill': False, 'ignore_beforeunload': False})]
    expected = {'logic': {'values': [0.5, 2, 3, 1], 'total': 6.5},
                'file_wait_regex': {'ready': True, 'matches': [['A102', '3']]}, 'web_local': ['A', 'C']}
    for name, blocks in plans.items():
        plan = {'flow_id': 'REPLACE_WITH_NEW_FLOW_ID', 'blocks': blocks,
                'out_parameters': [{'name': 'training_result', 'type': 'any'}]}
        (root / (name + '.json')).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'expected.json').write_text(json.dumps(expected, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'directory': str(root), 'cases': list(plans), 'status': 'prepared_not_executed'}


def verify(directory, case, actual_file):
    expected = json.loads((Path(directory) / 'expected.json').read_text(encoding='utf-8'))[case]
    actual = json.loads(Path(actual_file).read_text(encoding='utf-8-sig'))
    # Caller must extract the real training_result; do not interpret missing envelopes as success.
    if actual != expected:
        raise ValueError('Business result mismatch: expected %r, actual %r' % (expected, actual))
    return {'case': case, 'verified': True, 'actual': actual}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'verify', 'serve'])
    parser.add_argument('--directory', required=True)
    parser.add_argument('--case', choices=['logic', 'file_wait_regex', 'web_local'])
    parser.add_argument('--actual')
    parser.add_argument('--port', type=int, default=18765)
    parser.add_argument('--web-base-url', default='http://127.0.0.1:18765')
    args = parser.parse_args()
    if args.command == 'verify' and (not args.case or not args.actual):
        parser.error('verify requires --case and --actual (JSON containing actual output value)')
    if args.command == 'serve':
        import functools
        from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
        directory = Path(args.directory).resolve(strict=True)
        if not (directory / 'inventory.html').is_file():
            parser.error('serve requires a prepared training directory')
        server = ThreadingHTTPServer(('127.0.0.1', args.port), functools.partial(SimpleHTTPRequestHandler, directory=str(directory)))
        print('Serving training fixture on http://127.0.0.1:%d; Ctrl+C stops' % server.server_port, flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        raise SystemExit(0)
    print(json.dumps(prepare(args.directory, args.web_base_url) if args.command == 'prepare' else
                     verify(args.directory, args.case, args.actual), ensure_ascii=False, indent=2))
