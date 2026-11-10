#!/usr/bin/env python3
"""安装后自检：确认这个 skill 在当前 Agent 环境里能不能跑起来。

用法：
    python3 <skill目录>/scripts/check_env.py

特点：本脚本只用标准库，即使 numpy / Pillow 没装也能正常运行并给出清晰提示。
退出码：必需项齐全为 0，缺必需依赖或文件为 1。
"""

import argparse
import glob
import os
import sys

ap = argparse.ArgumentParser(description='动态表情包工作台 · 安装自检')
ap.add_argument('--dir', default='', help='skill 根目录（含 SKILL.md 的目录），默认自动取本脚本的上一级')
args = ap.parse_args()

ROOT = os.path.abspath(args.dir) if args.dir else os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

ok = True


def line(status, label, detail=''):
    print(f'  {status}  {label:<28}{detail}')


def fail(label, detail=''):
    global ok
    ok = False
    line('FAIL', label, detail)


print(f'skill 根目录：{ROOT}')
print()

print('[1/4] 运行环境')
ver = sys.version_info
if ver >= (3, 9):
    line('OK', 'Python', f'{ver.major}.{ver.minor}.{ver.micro}（{sys.executable}）')
else:
    fail('Python', f'{ver.major}.{ver.minor}.{ver.micro}，需要 3.9+')

try:
    import numpy as np
    line('OK', 'numpy', np.__version__)
except ImportError:
    fail('numpy', '未安装')

try:
    import PIL
    line('OK', 'Pillow', PIL.__version__)
except ImportError:
    fail('Pillow', '未安装')

try:
    import scipy
    line('OK', 'scipy（可选）', scipy.__version__)
except ImportError:
    line('--', 'scipy（可选）', '未安装，会自动走纯 numpy 实现，不影响结果')

print()
print('[2/4] 文件完整性')
skill_md = os.path.join(ROOT, 'SKILL.md')
if os.path.isfile(skill_md):
    head = open(skill_md, encoding='utf-8').read(400)
    if 'name:' in head and 'description:' in head:
        line('OK', 'SKILL.md', '位于仓库根目录，frontmatter 含 name / description')
    else:
        fail('SKILL.md', 'frontmatter 缺 name 或 description，部分 Agent 会拒绝加载')
else:
    fail('SKILL.md', '根目录找不到，检查是否把整个仓库放进了 skills 目录')

scripts = ['qa_check.py', 'clean_bg.py', 'make_gif.py', 'overview.py',
           'brand_preview.py', 'check_env.py']
missing = [s for s in scripts if not os.path.isfile(os.path.join(ROOT, 'scripts', s))]
if missing:
    fail('scripts/', '缺少：' + ', '.join(missing))
else:
    line('OK', 'scripts/', f'{len(scripts)} 个脚本齐全')

refs = glob.glob(os.path.join(ROOT, 'references', '*.md'))
if len(refs) >= 5:
    line('OK', 'references/', f'{len(refs)} 篇规范文档')
else:
    fail('references/', f'只找到 {len(refs)} 篇，正常应有 6 篇')

print()
print('[3/4] 中文字体（只影响品牌预览卡的标题）')
windir = os.environ.get('WINDIR', r'C:\Windows')
candidates = [
    '/System/Library/Fonts/PingFang.ttc',
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/Library/Fonts/Arial Unicode.ttf',
    os.path.join(windir, 'Fonts', 'msyh.ttc'),
    os.path.join(windir, 'Fonts', 'simhei.ttf'),
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
]
found = next((p for p in candidates if os.path.isfile(p)), '')
if found:
    line('OK', '中文字体', found)
else:
    extra = glob.glob('/usr/share/fonts/**/*CJK*', recursive=True) + glob.glob(
        '/usr/share/fonts/**/*wqy*', recursive=True)
    if extra:
        line('OK', '中文字体', extra[0])
    else:
        line('--', '中文字体', '未找到，预览卡标题可能显示方框；用 --font <字体文件> 指定，不影响 GIF')

print()
print('[4/4] 生图后端')
line('--', '生图能力', '由 Agent 在运行时探测，本 skill 不绑定任何模型；没有内置能力时会给 A/B/C 备选')

print()
if ok:
    print('结论：PASS —— 环境已就绪，可以直接说「用这张图帮我做一套动态表情包」。')
    print('      想零成本验证脚本链路，见 README 的「零成本复现」一节。')
    sys.exit(0)

pip_cmd = 'py -3 -m pip' if os.name == 'nt' else 'python3 -m pip'
print('结论：FAIL —— 先补齐上面标 FAIL 的项：')
print(f'      {pip_cmd} install -r "{os.path.join(ROOT, "requirements.txt")}"')
print('      装完重跑本脚本；若用的是虚拟环境，请用该环境的 python 执行。')
sys.exit(1)
