#!/usr/bin/env python3
"""慢漫的AI人 · 动态表情包工作台

精灵图出图后的自动质检：网格、各格字幕齐全度、角色占比、背景纯度、水印残留。
兼容不透明纯色底、渐变底，以及生图后端直接输出的真透明底。
不通过就按报告改提示词重画，不要带着问题进切帧步骤。

用法:
  python3 qa_check.py 精灵图.png --cols 3 --rows 2
  python3 qa_check.py 精灵图.png --cols 3 --rows 3 --bg "#0000FF"   # 自定义抠图底色
  python3 qa_check.py 精灵图.png --cols 3 --rows 2 --strict          # WARN 也算不通过
退出码: FAIL=1，其余=0
"""
import argparse
import sys
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser(description='精灵图自动质检（慢漫的AI人）')
ap.add_argument('src')
ap.add_argument('--cols', type=int, default=3)
ap.add_argument('--rows', type=int, default=2)
ap.add_argument('--bg', default='', help='自定义抠图底色 #RRGGBB；默认识别品红/绿族')
ap.add_argument('--caption-band', type=float, default=0.22, help='每格底部字幕带高度比例')
ap.add_argument('--strict', action='store_true', help='WARN 也判为不通过')
args = ap.parse_args()

rgba = np.asarray(Image.open(args.src).convert('RGBA')).astype(np.int16)
a = rgba[..., :3]
alpha = rgba[..., 3]
H, W = a.shape[:2]
cw, ch = W // args.cols, H // args.rows
R, G, B = a[..., 0], a[..., 1], a[..., 2]
issues = []

custom_key = None
if args.bg:
    s = args.bg.lstrip('#')
    if len(s) != 6:
        raise SystemExit('--bg 需要 #RRGGBB 格式')
    custom_key = np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.int16)

transparent_ratio = float((alpha < 128).mean())
transparent_bg = transparent_ratio > 0.05


def add(level, msg):
    issues.append((level, msg))


# 1. 网格
if W % args.cols or H % args.rows:
    add('FAIL', f'尺寸 {W}x{H} 不能被 {args.cols}x{args.rows} 整除')
ratio = cw / ch
if not 0.85 <= ratio <= 1.18:
    add('WARN', f'格子 {cw}x{ch} 不够方（比例 {ratio:.2f}），切帧后可能变形')
print(f'[网格] {W}x{H} → {args.cols}×{args.rows}，格子 {cw}x{ch}，{"透明底" if transparent_bg else "不透明底"}')

# 2. 每格字幕：统计底部字幕带的白字像素量，同一张图内应高度一致
band_h = int(ch * args.caption_band)
counts = []
for r in range(args.rows):
    for c in range(args.cols):
        cell = a[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
        band = cell[-band_h:]
        white = ((band[..., 0] > 185) & (band[..., 1] > 185) & (band[..., 2] > 185)).sum()
        counts.append(int(white))
n = args.cols * args.rows
lo, hi = min(counts), max(counts)
print(f'[字幕] {n} 格白字像素: {counts} | min/max = {lo/max(hi,1):.2f}')
if lo < 800:
    add('FAIL', f'有格子几乎没有字幕（最低 {lo} 白字像素），检查是否漏画字幕或字幕位置过高')
elif lo / max(hi, 1) < 0.6:
    add('FAIL', f'各格字幕量差异过大（{lo} ~ {hi}），可能有错字、漏字或位置不一致')

# 3. 角色占比：过小通常是"全身小人"，过大可能被裁切
# 背景族判据同时兼容纯品红底、渐变紫粉底、纯绿底、自定义底色与 alpha 透明区
pure = (np.abs(R - 255) < 25) & (G < 35) & (np.abs(B - 255) < 25)
grad = (R - G > 40) & (B - G > 18) & (R > 110) & (G < 190) & (np.abs(R - B) < 140)
green = (G - R > 40) & (G - B > 40) & (G > 110) & (R < 190)
custom = (np.abs(a - custom_key).sum(-1) < 90) if custom_key is not None else np.zeros((H, W), bool)
bgmask = pure | grad | green | custom | (alpha < 128)
ratios = []
for r in range(args.rows):
    for c in range(args.cols):
        cell = bgmask[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
        ratios.append(round(float(1 - cell.mean()), 3))
print(f'[角色占比] {ratios}（非背景像素比例）')
if min(ratios) < 0.18:
    add('FAIL', f'有格子角色占比仅 {min(ratios):.1%}，疑似全身小人 / 角色过小，改提示词为「只画头部和上半身特写」重画')
elif min(ratios) < 0.28:
    add('WARN', f'有格子角色占比仅 {min(ratios):.1%}，构图偏小，检查是不是画成了全身站姿')
if max(ratios) > 0.82:
    add('WARN', f'有格子角色占比 {max(ratios):.1%}，可能被裁切')
if min(ratios) > 0 and max(ratios) - min(ratios) > 0.3:
    add('WARN', '各格角色占比差异较大，帧间可能有大小跳动')

# 4. 背景纯度：只取四角（画面边缘中部常被角色／高马尾占满，取了会误报），
#    再看全图"背景族"像素的颜色集中度；真透明底不需要这一步
bg_standard = False
if transparent_bg:
    print(f'[背景] 真透明底（透明像素 {transparent_ratio:.1%}），跳过纯度检查')
else:
    corners = [a[:20, :20], a[:20, -20:], a[-20:, :20], a[-20:, -20:]]
    medians = np.array([np.median(p.reshape(-1, 3), axis=0) for p in corners])
    targets = [[255, 0, 255], [0, 255, 0]]
    if custom_key is not None:
        targets.append(custom_key.tolist())
    tarr = [np.array(t, dtype=float) for t in targets]
    worst = float(np.min([np.linalg.norm(medians - t, axis=1) for t in tarr], axis=0).max())
    bgp = a[bgmask & (alpha >= 128)]
    p95 = 0.0
    if len(bgp):
        d_all = np.min([np.linalg.norm(bgp.astype(float) - t, axis=1) for t in tarr], axis=0)
        p95 = float(np.percentile(d_all, 95))
    bg_standard = worst <= 40 and p95 <= 40
    print(f'[背景] 四角偏差 {worst:.1f}，背景像素距离 p95 {p95:.1f}')
    if not bg_standard:
        add('WARN', f'背景不是标准纯色底（四角偏差 {worst:.1f} / p95 {p95:.1f}，多为渐变紫粉或浅灰），建议先跑 clean_bg.py 归一化再抠图')

# 5. 右下角水印残留（排除真透明区域，避免把透明像素的 RGB 误判成水印）
#    已归一化的纯色底：右下角矩形必然已被 clean_bg.py 刷成背景色，
#    那里剩下的亮白像素是第 6 格字幕，不是水印，跳过以免误报
if bg_standard:
    print('[水印] 已归一化纯色底，水印区为背景色；右下角亮白像素来自字幕，跳过')
else:
    wm = a[int(H * 0.90):, int(W * 0.915):]
    wm_opaque = alpha[int(H * 0.90):, int(W * 0.915):] > 128
    wm_white = int((((wm[..., 0] > 185) & (wm[..., 1] > 185) & (wm[..., 2] > 185)) & wm_opaque).sum())
    print(f'[水印] 右下角亮白像素 {wm_white}')
    if wm_white > 200:
        add('WARN', f'右下角疑似平台水印（{wm_white} 亮白像素），用 clean_bg.py 清理')

# 汇总
fails = [m for lv, m in issues if lv == 'FAIL']
warns = [m for lv, m in issues if lv == 'WARN']
print('\n=== 质检结果 ===')
for lv, m in issues:
    print(f'  {lv}: {m}')
if fails:
    print(f'结论：FAIL（{len(fails)} 项阻断 / {len(warns)} 项提醒）→ 改提示词重画这一张')
    sys.exit(1)
if warns and args.strict:
    print(f'结论：FAIL（strict 模式，{len(warns)} 项提醒）')
    sys.exit(1)
if warns:
    print(f'结论：PASS（{len(warns)} 项提醒，建议处理后再切帧）')
else:
    print('结论：PASS（全部通过，可以进入背景归一化与切帧）')
