#!/usr/bin/env python3
"""慢漫的AI人 · 动态表情包工作台

把生图工具画出的渐变色底归一化成纯抠图底色，并清掉右下角平台水印。

用法:
  # 精灵图：渐变紫粉底 -> 纯品红，顺带去水印
  python3 clean_bg.py 精灵图.png 精灵图_干净.png --bg "#FF00FF"

  # 角色含粉/紫时换纯绿底
  python3 clean_bg.py 精灵图.png 精灵图_干净.png --bg "#00FF00"

  # 角色设定图：只刷掉水印，不动浅灰底
  python3 clean_bg.py 设定图.png 设定图_干净.png --wm-only
"""
import argparse
import os
import numpy as np
from PIL import Image


def hex2rgb(s):
    s = s.lstrip('#')
    if len(s) != 6:
        raise ValueError('--bg 需要 #RRGGBB 格式')
    return np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.int16)


ap = argparse.ArgumentParser(description='背景归一化 + 去平台水印（慢漫的AI人）')
ap.add_argument('src')
ap.add_argument('dst')
ap.add_argument('--bg', default='#FF00FF', help='目标抠图底色 #RRGGBB，同时决定识别判据（品红族 / 绿族）')
ap.add_argument('--wm-x', type=float, default=0.92, help='水印区起始横坐标比例，默认 0.92')
ap.add_argument('--wm-y', type=float, default=0.905, help='水印区起始纵坐标比例，默认 0.905')
ap.add_argument('--no-wm', action='store_true', help='不处理水印区')
ap.add_argument('--wm-only', action='store_true', help='只清水印、不做全图归一化（浅灰底设定图用）')
ap.add_argument('--no-dilate', action='store_true', help='不做 1px 膨胀，保留最细的边缘')
args = ap.parse_args()

os.makedirs(os.path.dirname(os.path.abspath(args.dst)), exist_ok=True)

target = hex2rgb(args.bg)
a = np.asarray(Image.open(args.src).convert('RGB')).astype(np.int16)
h, w = a.shape[:2]
R, G, B = a[..., 0], a[..., 1], a[..., 2]

if args.wm_only:
    # 设定图是浅灰平涂底：用四角背景色填充水印矩形，不动角色
    corners = np.concatenate([
        a[:20, :20].reshape(-1, 3), a[:20, -20:].reshape(-1, 3),
        a[-20:, :20].reshape(-1, 3), a[-20:, -20:].reshape(-1, 3),
    ])
    fill = np.median(corners, axis=0).astype(np.int16)
    changed = '仅清理水印'
else:
    is_green = bool(target[1] > target[0] and target[1] > target[2])
    if is_green:
        bg = (G - R > 40) & (G - B > 40) & (G > 110) & (R < 190)
    else:
        # 紫粉 / 品红族：R、B 明显高于 G；黑白灰、肤色、蓝黄道具都不满足
        bg = (R - G > 40) & (B - G > 18) & (R > 110) & (G < 190) & (np.abs(R - B) < 140)

    if not args.no_dilate:
        g = bg.copy()
        g[1:] |= bg[:-1]
        g[:-1] |= bg[1:]
        g[:, 1:] |= bg[:, :-1]
        g[:, :-1] |= bg[:, 1:]
        bg = g

    a[bg] = target
    fill = target
    changed = f'背景归一化 {bg.mean():.1%}'

if not args.no_wm:
    y0, x0 = int(h * args.wm_y), int(w * args.wm_x)
    a[y0:, x0:] = fill
    changed += f' + 水印区 ({x0},{y0})→({w},{h})'

Image.fromarray(a.astype(np.uint8)).save(args.dst)
suffix = '' if args.wm_only else f' | 底色 {args.bg}'
print(f'[clean_bg] {args.src} → {args.dst} | {changed}{suffix}')
