"""Embed the build-manual data into template.html -> a self-contained HTML file.

usage: python tools/build_manual_html.py   (writes docs/manual/build_manual.html from tools/manual_template.html)
Reads docs/manual/robot_a.glb, robot_b.glb and steps.json (version 2) and replaces the
single /*__DATA__*/ marker with `const GLB_A = "...";`, `const GLB_B = "...";`, `const STEPS = {...};`.
"""
import base64, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'manual') + os.sep
tpl_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'manual_template.html')
out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(SRC, 'build_manual.html')

with open(tpl_path, encoding='utf-8') as f:
    tpl = f.read()
with open(SRC + 'robot_a.glb', 'rb') as f:
    a = base64.b64encode(f.read()).decode()
with open(SRC + 'robot_b.glb', 'rb') as f:
    b = base64.b64encode(f.read()).decode()
with open(SRC + 'steps.json', encoding='utf-8') as f:
    steps = json.load(f)
assert steps.get('version') == 2, 'expected steps.json version 2'
st = json.dumps(steps, separators=(',', ':'), ensure_ascii=False).replace('</', '<' + chr(92) + '/')
data = f'const GLB_A = "{a}";\nconst GLB_B = "{b}";\nconst STEPS = {st};'
assert tpl.count('/*__DATA__*/') == 1, 'template must contain exactly one /*__DATA__*/ marker'
out = tpl.replace('/*__DATA__*/', data)
with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(out)
print(out_path, len(out))
