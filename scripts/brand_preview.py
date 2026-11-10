#!/usr/bin/env python3
"""慢漫的AI人 · 动态表情包工作台

生成品牌预览卡：暖白底、圆角白卡片、中文标题、多宫格表情首帧、右下角署名。
中文字体在 macOS / Windows / Linux 自动查找，也可以用 --font 手动指定。

用法:
  python3 brand_preview.py gif --title "疑惑 · 动态表情包" --out 预览_全套.png
  python3 brand_preview.py gif --order "让我想想,马上改,啊,我看看,懂了,下班"
  python3 brand_preview.py gif --font /path/to/NotoSansCJK-Regular.ttc
"""
import argparse
import glob
import os
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser(description='品牌预览卡（慢漫的AI人）')
ap.add_argument('src', help='切帧输出目录，读取其中的 *_帧01.png')
ap.add_argument('--title', default='动态表情包')
ap.add_argument('--subtitle', default='')
ap.add_argument('--out', default='预览_全套.png')
ap.add_argument('--order', default='', help='逗号分隔的表情顺序（不含 _帧01.png 后缀）')
ap.add_argument('--per-row', type=int, default=3)
ap.add_argument('--font', default='', help='手动指定中文字体文件（.ttf / .ttc / .otf）')
ap.add_argument('--label-map', default='', help='标签覆盖，格式「key=value,key=value」；用于补回文件名里去掉的标点')
args = ap.parse_args()

os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

overrides = {}
for pair in args.label_map.split(','):
    if '=' in pair:
        k, v = pair.split('=', 1)
        overrides[k.strip()] = v.strip()

paths = sorted(glob.glob(os.path.join(args.src, '*_帧01.png')))
if args.order:
    wanted = [x.strip() for x in args.order.split(',') if x.strip()]
    index = {os.path.basename(p).replace('_帧01.png', ''): p for p in paths}
    paths = [index[k] for k in wanted if k in index] or paths
if not paths:
    raise SystemExit(f'{args.src}/ 下没找到 *_帧01.png，先跑 make_gif.py')

windir = os.environ.get('WINDIR', 'C:/Windows')
FONT_CANDIDATES = [
    # macOS
    '/System/Library/Fonts/PingFang.ttc',
    '/System/Library/Fonts/STHeiti Light.ttc',
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/Library/Fonts/Arial Unicode.ttf',
    # Windows
    os.path.join(windir, 'Fonts', 'msyh.ttc'),
    os.path.join(windir, 'Fonts', 'msyhbd.ttc'),
    os.path.join(windir, 'Fonts', 'simhei.ttf'),
    os.path.join(windir, 'Fonts', 'simsun.ttc'),
    # Linux / 通用
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/usr/share/fonts/truetype/arphic/uming.ttc',
]
FONT_GLOBS = [
    '/usr/share/fonts/**/*NotoSansCJK*',
    '/usr/share/fonts/**/*SourceHanSans*',
    '/usr/share/fonts/**/*wqy*',
    os.path.expanduser('~/Library/Fonts/*'),
    os.path.expanduser('~/.fonts/*'),
    os.path.expanduser('~/.local/share/fonts/*'),
]


def pick_font():
    if args.font:
        if not os.path.exists(args.font):
            raise SystemExit(f'指定的字体文件不存在：{args.font}')
        return args.font
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    for pattern in FONT_GLOBS:
        hits = sorted(glob.glob(pattern, recursive=True))
        if hits:
            return hits[0]
    return None


fp = pick_font()
if fp is None:
    print('[brand_preview] 警告：没找到系统中文字体，中文可能显示为方框；用 --font <字体文件路径> 指定一个')


def font(size):
    if fp:
        return ImageFont.truetype(fp, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # 旧版 Pillow 不支持 size 参数
        return ImageFont.load_default()


n = len(paths)
per_row = min(args.per_row, n)
rows = (n + per_row - 1) // per_row
CARD, GAP, TOP = 344, 26, 165
W = 58 * 2 + per_row * CARD + (per_row - 1) * GAP
H = TOP + rows * 355 + 40
c = Image.new('RGB', (W, H), '#F5F6F8')
d = ImageDraw.Draw(c)
d.text((58, 38), args.title, font=font(46), fill='#1B1C1E')
sub = args.subtitle or f'{n} 款  |  480 / 240 透明 GIF + APNG  |  无水印'
d.text((60, 104), sub, font=font(21), fill='#8A8F98')

for i, p in enumerate(paths):
    col, row = i % per_row, i // per_row
    x0 = 58 + col * (CARD + GAP)
    y0 = TOP + row * 355
    d.rounded_rectangle((x0, y0, x0 + CARD, y0 + 306), radius=22, fill='white', outline='#E4E7EB', width=2)
    fr = Image.open(p).convert('RGBA')
    fr.thumbnail((286, 272), Image.LANCZOS)
    c.paste(fr, (x0 + (CARD - fr.width) // 2, y0 + (292 - fr.height) // 2), fr)
    key = os.path.basename(p).replace('_帧01.png', '')
    label = overrides.get(key, key)
    d.text((x0 + 6, y0 + 312), label, font=font(25), fill='#33363B')

d.text((W - 250, H - 34), '慢漫的AI人', font=font(20), fill='#9AA0A8')
c.save(args.out)
print(f'[brand_preview] {n} 款 → {args.out} ({W}x{H}) | 字体 {fp or "默认"}')
