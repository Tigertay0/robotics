"""Embed the build-manual data into template.html -> a self-contained HTML file.

usage: python build.py [template.html] [output.html]
Reads docs/manual/robot_a.glb, robot_b.glb and steps.json (version 2) and replaces the
single /*__DATA__*/ marker with `const GLB_A = "...";`, `const GLB_B = "...";`, `const STEPS = {...};`.
"""
import base64, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r'C:/Users/Tigre/robotics/docs/manual/'
tpl_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'template.html')
out_path = sys.argv[2] if len(sys.argv) > 2 else r'C:/Users/Tigre/ovwork/build_manual.html'

tpl = open(tpl_path, encoding='utf-8').read()
a = base64.b64encode(open(SRC + 'robot_a.glb', 'rb').read()).decode()
b = base64.b64encode(open(SRC + 'robot_b.glb', 'rb').read()).decode()
steps = json.load(open(SRC + 'steps.json', encoding='utf-8'))
assert steps.get('version') == 2, 'expected steps.json version 2'
st = json.dumps(steps, separators=(',', ':'), ensure_ascii=False).replace('</', '<' + chr(92) + '/')
data = f'const GLB_A = "{a}";\nconst GLB_B = "{b}";\nconst STEPS = {st};'
assert tpl.count('/*__DATA__*/') == 1, 'template must contain exactly one /*__DATA__*/ marker'
out = tpl.replace('/*__DATA__*/', data)
open(out_path, 'w', encoding='utf-8', newline='\n').write(out)
print(out_path, len(out))
