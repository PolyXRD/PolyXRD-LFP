"""PolyXRD LFP 品牌资产生成器
================================
参照 PolyXRD 家族的视觉血统（Pillow 纯代码绘制，可复现、颜色精确）。

设计血统（与家族严格一致）
--------------------------
- 品牌深色 #0F172A (slate-950) → 品牌蓝 #0284C7 (sky-600) 对角线渐变
- 家族符号 = 「白色正六边形」。本工具的 motif =
  「橄榄石（Pnma）正交晶胞线框 + 蓝色 LFP 三强线衍射图样」
- 子工具强调色 = 青色 #22D3EE

与家族 RutAna 的差异（有意为之）
--------------------------------
RutAna 画的是两个四方晶胞（锐钛/金红石）；LFP 是**正交**晶系，且三轴不等，
因此晶胞线框按 a≠b≠c 的真实比例绘制（c 轴最短、a 轴最长），并把三强线
(200) 17.2°、(020) 29.7°、(311) 35.6° 抽象成三个峰——这样图标本身
就说明了「正交 + 三条特征线」，而不是通用装饰。

产出（写入 <root>/resources/）
------------------------------
- app-icon.png        256×256   运行时窗口图标
- app-icon@2x.png     512×512   高分屏备份
- app-icon.ico        多分辨率  给 exe 资源使用
- crystal-mark.png    256×256   透明底深色 mark（浅色背景用）
- logo-horizontal.png 512×160   横向 logo：mark + 「PolyXRD LFP」
- splash-screen.png   480×270   启动图（深色底 + logo + 版本 + tagline）
- hero-banner.png     1600×600  About 页头图

使用：
    python tools/build_artwork.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lfp.version import APP_TAGLINE, __version__  # noqa: E402

RES_DIR = ROOT / "resources"

# --------------------------------------------------------------------------- #
# 品牌常量（家族色，严格一致）
# --------------------------------------------------------------------------- #
BRAND_DARK = (15, 23, 42)        # #0F172A  slate-950  "Poly"
BRAND_BLUE = (2, 132, 199)       # #0284C7  sky-600    "XRD"
WHITE = (255, 255, 255)
SOFT = (226, 232, 240)           # #E2E8F0  slate-200
SLATE = (100, 116, 139)          # #64748B  slate-500
CYAN = (34, 211, 238)            # #22D3EE  子工具强调色
CYAN_LIGHT = (125, 211, 252)     # #7DD3FC
CYAN_DARK = (8, 145, 178)        # #0891B2  浅色背景上的青色词标

# 启动图 / 横幅的深空背景（与家族 splash 的墨青基调一致）
BG_INNER = (12, 48, 70)
BG_OUTER = (5, 12, 24)

FONT_BOLD = r"C:/Windows/Fonts/segoeuib.ttf"
FONT_SEMI = r"C:/Windows/Fonts/seguisb.ttf"
FONT_CN = r"C:/Windows/Fonts/msyh.ttc"

ICON_SIZES = [16, 24, 32, 48, 64, 128, 256]
COS30 = math.cos(math.radians(30.0))

#: LFP 三强线（Cu Kα1，2θ）：(200) 17.2°、(020) 29.7°、(311) 35.6°
#: 相对强度取 PDF 40-1499 量级：25 / 100 / 35（此处归一化为 0.55 / 1.00 / 0.72）
PEAK_POS = (0.20, 0.50, 0.735)
PEAK_REL = (0.55, 1.00, 0.72)
PEAK_SIGMA = 0.026

#: 正交晶胞三轴相对半长（a ≈ 10.33 Å > b ≈ 6.01 Å > c ≈ 4.69 Å）
CELL_A, CELL_B, CELL_C = 1.00, 0.62, 0.47


# --------------------------------------------------------------------------- #
# 基础几何 / 绘制工具
# --------------------------------------------------------------------------- #
def hex_points(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    """尖顶正六边形顶点（顶点在正上/正下）。"""
    return [
        (cx + r * math.cos(math.radians(-90 + 60 * k)),
         cy + r * math.sin(math.radians(-90 + 60 * k)))
        for k in range(6)
    ]


def draw_cell_ortho(draw: ImageDraw.ImageDraw, cx: float, cy: float,
                    a: float, b: float, c: float, color, lw: int) -> None:
    """正交晶胞线框：8 顶点 + 12 棱（等轴测投影，三轴不等长）。

    投影：x 轴 → 右下 30°，z 轴 → 左下 30°，y 轴 → 正上；a/b/c 为半长。
    """
    corners: dict[tuple[int, int, int], tuple[float, float]] = {}
    for xs in (-1, 1):
        for ys in (-1, 1):
            for zs in (-1, 1):
                px = (xs * a - zs * c) * COS30
                py = (xs * a + zs * c) * 0.5 - ys * b
                corners[(xs, ys, zs)] = (cx + px, cy + py)
    for cell, p in corners.items():
        for axis in range(3):
            other = list(cell)
            other[axis] = -other[axis]
            other = tuple(other)
            if cell < other:
                draw.line([p, corners[other]], fill=color, width=lw)


def draw_lfp_peaks(draw: ImageDraw.ImageDraw, x0: float, y0: float,
                   width: float, amp: float, color, lw: int) -> None:
    """蓝色衍射图样：基线 + 三个高斯峰（LFP 三强线的抽象表达）。"""
    pts: list[tuple[float, float]] = [(x0, y0)]
    n = 160
    for i in range(n + 1):
        t = i / n
        g = 0.0
        for pos, rel in zip(PEAK_POS, PEAK_REL):
            g += rel * math.exp(-((t - pos) ** 2) / (2 * PEAK_SIGMA ** 2))
        pts.append((x0 + t * width, y0 - amp * g))
    pts.append((x0 + width, y0))
    draw.line(pts, fill=color, width=lw, joint="curve")


def make_mark(size: int, hex_color, cell_color, axis_color,
              peak_color, hex_w_ratio: float = 0.070,
              glow: bool = False) -> Image.Image:
    """生成 LFP 家族符号：六边形 + 正交晶胞线框 + 三强线衍射（透明底 RGBA）。"""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cx = cy = size / 2.0
    r = size * 0.44
    hex_w = max(2, int(round(size * hex_w_ratio)))
    pts = hex_points(cx, cy, r)
    cell_lw = max(2, int(size * 0.012))
    peak_lw = max(2, int(size * 0.028))

    # 晶胞整体尺度：a 轴半长占符号半径的 ~0.30
    ca = size * 0.128 * CELL_A
    cb = size * 0.128 * CELL_B
    cc = size * 0.128 * CELL_C

    def motif(d: ImageDraw.ImageDraw) -> None:
        # 晶胞略偏上，衍射图样占下三分之一，视觉重心落在六边形中心
        draw_cell_ortho(d, cx - size * 0.015, cy - size * 0.055,
                        ca, cb, cc, cell_color, cell_lw)
        draw_lfp_peaks(d, cx - size * 0.26, cy + size * 0.285,
                       size * 0.52, size * 0.115, peak_color, peak_lw)

    if glow:
        gl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gl)
        gd.line(pts + [pts[0]], fill=hex_color, width=hex_w, joint="curve")
        motif(gd)
        gl = gl.filter(ImageFilter.GaussianBlur(max(2, size * 0.02)))
        im.alpha_composite(gl)

    d = ImageDraw.Draw(im)
    d.line(pts + [pts[0]], fill=hex_color, width=hex_w, joint="curve")
    motif(d)
    return im


def diagonal_gradient(size: int, c1, c2) -> Image.Image:
    """左上 → 右下 对角线渐变（低分辨率生成再放大，保证平滑）。"""
    small = Image.new("RGB", (96, 96))
    px = small.load()
    for y in range(96):
        for x in range(96):
            t = (x + y) / (2 * 95.0)
            px[x, y] = (round(c1[0] + (c2[0] - c1[0]) * t),
                        round(c1[1] + (c2[1] - c1[1]) * t),
                        round(c1[2] + (c2[2] - c1[2]) * t))
    return small.resize((size, size), Image.BICUBIC)


def radial_gradient(w: int, h: int, inner, outer) -> Image.Image:
    """径向渐变背景（中心亮 → 四周暗）。"""
    small = Image.new("RGB", (120, 68))
    px = small.load()
    cx, cy = 59.5, 33.0
    maxd = math.hypot(cx, cy)
    for y in range(68):
        for x in range(120):
            d = min(1.0, math.hypot(x - cx, y - cy) / maxd) ** 0.85
            px[x, y] = (round(inner[0] + (outer[0] - inner[0]) * d),
                        round(inner[1] + (outer[1] - inner[1]) * d),
                        round(inner[2] + (outer[2] - inner[2]) * d))
    return small.resize((w, h), Image.BICUBIC)


def rounded_mask(size: int, ratio: float = 0.22) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=int(size * ratio), fill=255)
    return m


def load_font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    """按顺序尝试加载字体，全部失败时退回默认位图字体。"""
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()  # type: ignore[return-value]


def draw_wordmark(draw: ImageDraw.ImageDraw, x: float, y_top: float,
                  segments: list[tuple[str, tuple[int, int, int]]],
                  font: ImageFont.FreeTypeFont) -> float:
    """按 segment 着色绘制词标，返回结束 x。"""
    for text, color in segments:
        draw.text((x, y_top), text, font=font, fill=color)
        x += draw.textlength(text, font=font)
    return x


# --------------------------------------------------------------------------- #
# 各类资产构建
# --------------------------------------------------------------------------- #
def build_icon() -> None:
    """应用图标：对角渐变底 + 发光 mark，256 / @2x / 多分辨率 ico。"""
    size = 512
    base = diagonal_gradient(size, BRAND_DARK, BRAND_BLUE).convert("RGBA")
    mark = make_mark(size, WHITE, CYAN, CYAN_LIGHT, CYAN_LIGHT,
                     hex_w_ratio=0.075, glow=True)
    base.alpha_composite(mark)
    base.putalpha(rounded_mask(size, 0.22))

    RES_DIR.mkdir(parents=True, exist_ok=True)
    base.resize((512, 512), Image.LANCZOS).save(
        RES_DIR / "app-icon@2x.png", format="PNG", optimize=True)
    base.resize((256, 256), Image.LANCZOS).save(
        RES_DIR / "app-icon.png", format="PNG", optimize=True)
    base.save(RES_DIR / "app-icon.ico", format="ICO",
              sizes=[(s, s) for s in ICON_SIZES])
    print("[icon] app-icon.png / app-icon@2x.png / app-icon.ico")


def build_crystal_mark() -> None:
    """透明底、深色线条版家族符号（浅色背景 About / 文档用）。"""
    mark = make_mark(256, BRAND_DARK, BRAND_BLUE, CYAN_DARK, BRAND_BLUE,
                     hex_w_ratio=0.055)
    mark.save(RES_DIR / "crystal-mark.png", format="PNG", optimize=True)
    print("[mark] crystal-mark.png")


def build_logo_horizontal() -> None:
    """横向 logo 512×160：mark + 「PolyXRD │ LFP」+ 物相副标。"""
    SS = 4
    W, H = 512 * SS, 160 * SS
    mark_size = int(H * 0.72)
    font_size = int(H * 0.30)
    sub = "LiFePO4 · Pnma (No. 62) · Rietveld"

    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mark = make_mark(mark_size, BRAND_DARK, BRAND_BLUE, CYAN_DARK, BRAND_BLUE,
                     hex_w_ratio=0.055)
    pad_x = int(H * 0.10)
    im.alpha_composite(mark, (pad_x, (H - mark_size) // 2))

    d = ImageDraw.Draw(im)
    font_big = load_font([FONT_BOLD], font_size)
    x_text = pad_x + mark_size + int(H * 0.12)
    seg_w = (d.textlength("PolyXRD ", font=font_big)
             + d.textlength("LFP", font=font_big))
    while x_text + seg_w > W - int(H * 0.10) and font_size > 24:
        font_size = int(font_size * 0.95)
        font_big = load_font([FONT_BOLD], font_size)
        seg_w = (d.textlength("PolyXRD ", font=font_big)
                 + d.textlength("LFP", font=font_big))
    y_big = int(H * 0.20)
    draw_wordmark(d, x_text, y_big,
                  [("PolyXRD ", BRAND_DARK), ("LFP", CYAN_DARK)], font_big)
    font_sub = load_font([FONT_SEMI, FONT_CN], int(H * 0.115))
    d.text((x_text, y_big + int(H * 0.40)), sub, font=font_sub, fill=SLATE)

    im.resize((W // SS, H // SS), Image.LANCZOS).save(
        RES_DIR / "logo-horizontal.png", format="PNG", optimize=True)
    print("[logo] logo-horizontal.png (512x160)")


def build_splash() -> None:
    """启动图 480×270：深色底 + mark + 标题 + 版本 + tagline。"""
    W, H = 480, 270
    SS = 2
    w, h = W * SS, H * SS
    bg = radial_gradient(w, h, BG_INNER, BG_OUTER).convert("RGBA")

    mark = make_mark(int(h * 0.42), WHITE, CYAN, CYAN_LIGHT, CYAN_LIGHT,
                     hex_w_ratio=0.070, glow=True)
    bg.alpha_composite(mark, ((w - mark.size[0]) // 2, int(h * 0.015)))

    d = ImageDraw.Draw(bg)
    font_t = load_font([FONT_BOLD], int(h * 0.115))
    tw = d.textlength("PolyXRD ", font=font_t) + d.textlength("LFP", font=font_t)
    draw_wordmark(d, (w - tw) / 2, int(h * 0.52),
                  [("PolyXRD ", SOFT), ("LFP", CYAN_LIGHT)], font_t)

    font_v = load_font([FONT_SEMI], int(h * 0.055))
    ver = f"v{__version__}"
    d.text(((w - d.textlength(ver, font=font_v)) / 2, int(h * 0.665)),
           ver, font=font_v, fill=CYAN)

    font_c = load_font([FONT_CN, FONT_SEMI], int(h * 0.052))
    tw = d.textlength(APP_TAGLINE, font=font_c)
    d.text(((w - tw) / 2, int(h * 0.755)), APP_TAGLINE, font=font_c,
           fill=(130, 176, 205))

    bg.convert("RGB").resize((W, H), Image.LANCZOS).save(
        RES_DIR / "splash-screen.png", format="PNG", optimize=True)
    print("[splash] splash-screen.png (480x270)")


def build_hero() -> None:
    """About 页头图 1600×600：深空底 + 大 mark + 标题 + tagline。"""
    W, H = 1600, 600
    bg = radial_gradient(W, H, BG_INNER, BG_OUTER).convert("RGBA")

    mark = make_mark(int(H * 0.40), WHITE, CYAN, CYAN_LIGHT, CYAN_LIGHT,
                     hex_w_ratio=0.070, glow=True)
    bg.alpha_composite(mark, ((W - mark.size[0]) // 2, int(H * 0.03)))

    d = ImageDraw.Draw(bg)
    font_t = load_font([FONT_BOLD], int(H * 0.135))
    tw = d.textlength("PolyXRD ", font=font_t) + d.textlength("LFP", font=font_t)
    draw_wordmark(d, (W - tw) / 2, int(H * 0.50),
                  [("PolyXRD ", SOFT), ("LFP", CYAN_LIGHT)], font_t)

    font_c = load_font([FONT_CN, FONT_SEMI], int(H * 0.052))
    tw = d.textlength(APP_TAGLINE, font=font_c)
    d.text(((W - tw) / 2, int(H * 0.72)), APP_TAGLINE, font=font_c,
           fill=(130, 176, 205))

    font_s = load_font([FONT_SEMI], int(H * 0.042))
    sub = ("Phase Identification  ·  Rietveld Whole-Pattern Fit  ·  "
           "Pnma (No. 62)  ·  Scherrer Size and Microstrain")
    tw = d.textlength(sub, font=font_s)
    d.text(((W - tw) / 2, int(H * 0.83)), sub, font=font_s, fill=CYAN)

    bg.convert("RGB").save(RES_DIR / "hero-banner.png", format="PNG", optimize=True)
    print("[hero] hero-banner.png (1600x600)")


def build_all() -> None:
    RES_DIR.mkdir(parents=True, exist_ok=True)
    build_icon()
    build_crystal_mark()
    build_logo_horizontal()
    build_splash()
    build_hero()
    files = sorted(p.name for p in RES_DIR.iterdir() if p.is_file())
    print(f"\n[done] 共 {len(files)} 个资产: {files}")


if __name__ == "__main__":
    build_all()
