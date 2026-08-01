import os
import sys

# 允许在任意目录下运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame

from game import Card, FreeCell, RANKS, SUITS, SUIT_SYMBOLS
# 全局变量
# 布局常量
W, H = 1080, 700
MARGIN = 14
CARD_W, CARD_H = 78, 110
GAP = CARD_W + 10                     # 水平间隔 88
TOP_Y = MARGIN
COL_Y0 = TOP_Y + CARD_H + 34          # 列区起始 y
ROW_STEP = 26                         # 列内每张牌的垂直步进
STATUS_Y = H - 30                     # 底部状态栏 y

# 颜色
BG_TOP = (9, 96, 52)                 # 背景渐变：上（亮绿）
BG_BOTTOM = (3, 46, 27)              # 背景渐变：下（墨绿）
SLOT_BORDER = (6, 66, 38)
SLOT_FILL = (13, 92, 53)
SLOT_INNER = (22, 112, 66)           # 空槽内圈高光
SLOT_SYMBOL = (38, 138, 82)          # 空槽中央花色符号
CARD_BG = (252, 251, 246)            # 牌面底色（暖白）
CARD_BORDER = (172, 166, 152)
CARD_BORDER_LIGHT = (255, 255, 252)  # 牌面内圈白边
SELECT_BORDER = (255, 176, 32)       # 选中金框
SELECT_GLOW = (255, 190, 60, 90)     # 选中外圈光晕
RED = (193, 32, 42)
BLACK = (30, 30, 34)
TEXT_LIGHT = (228, 248, 234)
BTN_BG = (228, 232, 224)
BTN_BG_HOVER = (255, 255, 252)
BTN_BORDER = (94, 122, 100)
BTN_TEXT = (46, 58, 50)
STATUS_BG = (0, 30, 18, 150)         # 状态栏半透明底
SHADOW_ALPHA = 85

DRAG_THRESHOLD = 12                   # 超过该像素视为拖拽
DOUBLE_CLICK_MS = 350


FONT_CANDIDATES = [
    (r"C:\Windows\Fonts\msyh.ttc",  r"C:\Windows\Fonts\msyhbd.ttc"),   # 微软雅黑
    (r"C:\Windows\Fonts\simhei.ttf", None),                            # 黑体
    (r"C:\Windows\Fonts\simsun.ttc", None),                            # 宋体
    (r"C:\Windows\Fonts\arial.ttf",  r"C:\Windows\Fonts\arialbd.ttf"),  # Arial
]
# 花色符号专用字体：Segoe UI Symbol
SUIT_FONT_PATHS = [
    r"C:\Windows\Fonts\SegUISym.ttf",        # Segoe UI Symbol
    r"C:\Windows\Fonts\segui-sym.ttf",
]


def _load_font(size, bold=False):
    for normal, bold_path in FONT_CANDIDATES:
        path = bold_path if (bold and bold_path) else normal
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except Exception:
                continue
    return pygame.font.Font(None, size)


def _load_suit_font(size):
    for path in SUIT_FONT_PATHS:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except Exception:
                continue
    return _load_font(size)


# 预渲染资源

def _make_gradient_bg():
    strip = pygame.Surface((1, 2))
    strip.set_at((0, 0), BG_TOP)
    strip.set_at((0, 1), BG_BOTTOM)
    return pygame.transform.smoothscale(strip, (W, H))


def _make_shadow_surface():
    surf = pygame.Surface((CARD_W + 8, CARD_H + 8), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, surf.get_width(), surf.get_height())
    pygame.draw.rect(surf, (0, 0, 0, SHADOW_ALPHA), rect, border_radius=12)
    small = pygame.transform.smoothscale(surf, (surf.get_width() // 5, surf.get_height() // 5))
    return pygame.transform.smoothscale(small, (surf.get_width(), surf.get_height()))


def _render_card_surface(rank_font, suit_big_font, suit_small_font, card):
    surf = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
    rect = surf.get_rect()

    # 暖白圆角底、双层描边
    pygame.draw.rect(surf, CARD_BG, rect, border_radius=10)
    pygame.draw.rect(surf, CARD_BORDER, rect, width=2, border_radius=10)
    pygame.draw.rect(surf, CARD_BORDER_LIGHT, rect.inflate(-4, -4), width=1, border_radius=8)

    color = RED if card.color == "red" else BLACK
    symbol = SUIT_SYMBOLS[card.suit]
    rank = "10" if card.rank == "T" else card.rank

    # 中央大花色
    big = suit_big_font.render(symbol, True, color)
    big_shadow = suit_big_font.render(symbol, True, (0, 0, 0, 46))
    cx, cy = CARD_W // 2, CARD_H // 2 + 4
    surf.blit(big_shadow, (cx - big.get_width() // 2 + 1, cy - big.get_height() // 2 + 2))
    surf.blit(big, (cx - big.get_width() // 2, cy - big.get_height() // 2))

    # 角标
    rank_img = rank_font.render(rank, True, color)
    suit_img = suit_small_font.render(symbol, True, color)
    corner_w = max(rank_img.get_width(), suit_img.get_width())
    x0, y0 = 7, 5
    surf.blit(rank_img, (x0, y0))
    surf.blit(suit_img, (x0 + (rank_img.get_width() - suit_img.get_width()) // 2,
                         y0 + rank_img.get_height() - 1))
    # 右下角：整个角标旋转 180°
    corner = pygame.Surface((corner_w + 2, rank_img.get_height() + suit_img.get_height() + 4),
                            pygame.SRCALPHA)
    corner.blit(rank_img, (0, 0))
    corner.blit(suit_img, ((rank_img.get_width() - suit_img.get_width()) // 2,
                           rank_img.get_height() - 1))
    corner = pygame.transform.rotate(corner, 180)
    surf.blit(corner, (CARD_W - 8 - corner.get_width(), CARD_H - 7 - corner.get_height()))
    return surf


CARD_SURFACES = {}          # (suit, rank) -> 牌面 Surface
SHADOW_SURF = None
BG_SURF = None
SUIT_SMALL_FONT = None      # 空槽花色符号用字体


def _build_assets(rank_font, suit_big_font, suit_small_font):
    global SHADOW_SURF, BG_SURF, SUIT_SMALL_FONT
    SHADOW_SURF = _make_shadow_surface()
    BG_SURF = _make_gradient_bg()
    SUIT_SMALL_FONT = suit_small_font
    CARD_SURFACES.clear()
    for s in SUITS:
        for r in RANKS:
            CARD_SURFACES[(s, r)] = _render_card_surface(
                rank_font, suit_big_font, suit_small_font, Card(s, r))


class GameUI:
    def __init__(self, game=None):
        self.game = game if game is not None else FreeCell()
        self.selected = None            # (from_loc, group)
        self.drag = None                # (from_loc, group, origin_pos)
        self.message = ""
        self.last_click = None          # (pos, loc, time_ms)
        self.hover_btn = None

    # 坐标
    def free_rect(self, i):
        return pygame.Rect(MARGIN + i * GAP, TOP_Y, CARD_W, CARD_H)

    def foundation_rect(self, i):
        return pygame.Rect(MARGIN + 4 * GAP + 28 + i * GAP, TOP_Y, CARD_W, CARD_H)

    def col_x(self, i):
        return MARGIN + i * GAP

    def col_step(self, i):
        n = len(self.game.columns[i])
        if n <= 1:
            return ROW_STEP
        avail = H - COL_Y0 - 44
        return max(9, min(ROW_STEP, (avail - CARD_H) // (n - 1)))

    def panel_rect(self):
        """右上角工具面板。"""
        return pygame.Rect(W - MARGIN - 250, 10, 250, 164)

    def btn_rects(self):
        panel = self.panel_rect()
        w, h, gap = panel.w - 24, 30, 7
        x, y0 = panel.x + 12, panel.y + 42
        labels = [("new", "新局  N"), ("undo", "撤销  U"), ("auto", "自动收牌  A")]
        return [(key, pygame.Rect(x, y0 + i * (h + gap), w, h), label)
                for i, (key, label) in enumerate(labels)]

    def loc_at(self, pos):
        """返回鼠标位置对应的 (kind, i)；不在任何区域返回 None。"""
        for i in range(4):
            if self.free_rect(i).collidepoint(pos):
                return ("free", i)
        for i in range(4):
            if self.foundation_rect(i).collidepoint(pos):
                return ("foundation", i)
        x, y = pos
        if y >= COL_Y0 - 14:
            for i in range(8):
                if self.col_x(i) - 8 <= x <= self.col_x(i) + CARD_W + 8:
                    return ("col", i)
        return None

    def card_index_at(self, pos):
        """列中哪张牌被点到；返回该牌在列中的索引；未点中牌返回 None。"""
        x, y = pos
        for i in range(8):
            if not (self.col_x(i) - 8 <= x <= self.col_x(i) + CARD_W + 8):
                continue
            col = self.game.columns[i]
            if not col:
                return None
            step = self.col_step(i)
            for idx in range(len(col) - 1, -1, -1):
                rect = pygame.Rect(self.col_x(i), COL_Y0 + idx * step, CARD_W, CARD_H)
                if rect.collidepoint(pos):
                    return idx
            return None
        return None

    def clickable_card_loc(self, pos):
        """点击位置对应的「有牌可点」的位置：free/foundation 直接返回，
        列则要求点中牌且该牌在可拖序列内；否则返回 None。"""
        loc = self.loc_at(pos)
        if loc is None:
            return None
        kind, i = loc
        if kind in ("free", "foundation"):
            if self.game.can_select(loc):
                return loc
            return None
        idx = self.card_index_at(pos)
        if idx is None:
            return None
        start, _ = self.game.column_run(i)
        return loc if idx >= start else None

    # 交互
    def try_drop(self, from_loc, to_loc, n=None):
        if to_loc is None:
            return False
        if self.game.move(from_loc, to_loc, n=n):
            self.message = ""
            return True
        self.message = "不能放到那里"
        return False

    def try_auto_single(self, loc):
        """把 loc 的顶部 1 张牌直接收进回收位。"""
        if loc[0] == "foundation":
            return False                    # 回收位里的牌无需再收
        group = self.game.can_select(loc)
        if not group:
            return False
        top = group[-1]                     # 被收的是列顶/格顶那张
        if self.game.move(loc, ("foundation", SUITS.index(top.suit)), n=1):
            self.message = ""
            return True
        return False

    def handle_mouse_down(self, pos, time_ms):
        # 按钮
        for key, rect, _ in self.btn_rects():
            if rect.collidepoint(pos):
                if key == "new":
                    self.game.reset()
                    self.selected = self.drag = None
                    self.message = "新的一局"
                elif key == "undo":
                    if self.game.undo():
                        self.selected = self.drag = None
                        self.message = "已撤销"
                    else:
                        self.message = "没有可撤销的步"
                elif key == "auto":
                    n = self.game.auto_collect()
                    self.selected = self.drag = None
                    self.message = f"自动收牌 {n} 张" if n else "没有可自动收的牌"
                return

        loc = self.loc_at(pos)
        clickable = self.clickable_card_loc(pos)

        # 双击自动收牌
        if clickable is not None and self.last_click is not None:
            last_pos, last_loc, last_t = self.last_click
            if last_loc == clickable and time_ms - last_t <= DOUBLE_CLICK_MS \
                    and (last_pos[0] - pos[0]) ** 2 + (last_pos[1] - pos[1]) ** 2 < 400:
                if self.try_auto_single(clickable):
                    self.selected = self.drag = None
                    self.last_click = None
                    return
        self.last_click = (pos, clickable, time_ms)

        # 已有选中，尝试落位/取消
        if self.selected is not None:
            from_loc, group = self.selected
            if loc is not None and loc != from_loc:
                ok = self.try_drop(from_loc, loc, n=len(group))
                self.selected = self.drag = None
                if ok:
                    self.last_click = None
            else:
                self.selected = self.drag = None
            return

        # 新选择
        if clickable is not None:
            group = self.game.can_select(clickable)
            if clickable[0] == "col":
                # 只选中「被点击的牌往上」的部分，而非整段 run
                idx = self.card_index_at(pos)
                start = len(self.game.columns[clickable[1]]) - len(group)
                group = group[idx - start:]
            self.selected = (clickable, group)
            self.drag = (clickable, group, pos)

    def handle_mouse_up(self, pos):
        if self.drag is None:
            return
        from_loc, group, origin = self.drag
        dist = ((pos[0] - origin[0]) ** 2 + (pos[1] - origin[1]) ** 2) ** 0.5
        self.drag = None
        if dist >= DRAG_THRESHOLD:
            to_loc = self.loc_at(pos)
            if to_loc is not None and to_loc != from_loc:
                self.try_drop(from_loc, to_loc, n=len(group))
            self.selected = None
        # 距离小于阈值则保留 selected，等待点击落位

    def handle_key(self, key):
        if key in (pygame.K_n,):
            self.game.reset()
            self.selected = self.drag = None
            self.message = "新的一局"
            self.last_click = None
        elif key == pygame.K_u:
            if self.game.undo():
                self.selected = self.drag = None
                self.message = "已撤销"
            else:
                self.message = "没有可撤销的步"
        elif key == pygame.K_a:
            n = self.game.auto_collect()
            self.selected = self.drag = None
            self.message = f"自动收牌 {n} 张" if n else "没有可自动收的牌"
        elif key == pygame.K_ESCAPE:
            self.selected = self.drag = None

    # 渲染
    def draw_slot(self, surf, rect, label=None, label_font=None):
        """凹陷式空槽：深底 + 内圈高光 + 中央半透明花色。"""
        pygame.draw.rect(surf, SLOT_BORDER, rect, border_radius=10)
        pygame.draw.rect(surf, SLOT_FILL, rect.inflate(-4, -4), border_radius=8)
        pygame.draw.rect(surf, SLOT_INNER, rect.inflate(-8, -8), width=1, border_radius=6)
        if label:
            font = label_font or SUIT_SMALL_FONT
            if font:
                img = font.render(label, True, SLOT_SYMBOL)
                surf.blit(img, (rect.x + (CARD_W - img.get_width()) // 2,
                                rect.y + (CARD_H - img.get_height()) // 2))

    def draw_card(self, surf, x, y, card, selected=False):
        """绘制一张牌：投影 + 预渲染牌面 + 选中发光。"""
        if SHADOW_SURF is not None:
            surf.blit(SHADOW_SURF, (x - 4, y - 5))
        surf.blit(CARD_SURFACES[(card.suit, card.rank)], (x, y))
        if selected:
            rect = pygame.Rect(x, y, CARD_W, CARD_H)
            glow = pygame.Surface(rect.inflate(10, 10).size, pygame.SRCALPHA)
            pygame.draw.rect(glow, SELECT_GLOW, glow.get_rect(), width=6, border_radius=14)
            surf.blit(glow, rect.inflate(10, 10).topleft)
            pygame.draw.rect(surf, SELECT_BORDER, rect, width=3, border_radius=9)

    def draw(self, surf, rank_font, btn_font, status_font, big_font):
        if BG_SURF is not None:
            surf.blit(BG_SURF, (0, 0))
        else:
            surf.fill(BG_TOP)

        # 自由单元格
        for i in range(4):
            rect = self.free_rect(i)
            card = self.game.free[i]
            if card is None:
                self.draw_slot(surf, rect)
            else:
                self.draw_card(surf, rect.x, rect.y, card,
                               selected=self.selected is not None and self.selected[0] == ("free", i))

        # 回收位
        for i in range(4):
            rect = self.foundation_rect(i)
            f = self.game.foundations[i]
            if not f:
                self.draw_slot(surf, rect, label=SUIT_SYMBOLS[SUITS[i]])
            else:
                self.draw_card(surf, rect.x, rect.y, f[-1],
                               selected=self.selected is not None and self.selected[0] == ("foundation", i))

        # 主列
        for i in range(8):
            col = self.game.columns[i]
            step = self.col_step(i)
            x = self.col_x(i)
            for idx, card in enumerate(col):
                y = COL_Y0 + idx * step
                selected = (self.selected is not None and self.selected[0] == ("col", i)
                            and idx >= len(col) - len(self.selected[1]))
                self.draw_card(surf, x, y, card, selected=selected)
            if not col:
                self.draw_slot(surf, pygame.Rect(x, COL_Y0, CARD_W, CARD_H))

        # 右上角工具面板
        panel = self.panel_rect()
        p = pygame.Surface(panel.size, pygame.SRCALPHA)
        p.fill((16, 68, 43, 218))
        surf.blit(p, panel.topleft)
        pygame.draw.rect(surf, (48, 122, 78), panel, width=2, border_radius=12)
        title = btn_font.render("空当接龙", True, (238, 250, 242))
        surf.blit(title, (panel.x + 12, panel.y + 10))
        steps = btn_font.render(f"步数 {len(self.game.history)}", True, (196, 218, 204))
        surf.blit(steps, (panel.right - 12 - steps.get_width(), panel.y + 10))

        # 按钮
        for key, rect, label in self.btn_rects():
            hover = self.hover_btn == key
            bg = BTN_BG_HOVER if hover else BTN_BG
            pygame.draw.rect(surf, BTN_BORDER, rect, border_radius=7)
            pygame.draw.rect(surf, bg, rect.inflate(-4, -4), border_radius=5)
            img = btn_font.render(label, True, BTN_TEXT)
            surf.blit(img, (rect.x + (rect.w - img.get_width()) // 2,
                            rect.y + (rect.h - img.get_height()) // 2))
            if hover:
                shine = pygame.Surface((rect.w - 6, 10), pygame.SRCALPHA)
                shine.fill((255, 255, 255, 90))
                surf.blit(shine, (rect.x + 3, rect.y + 3))

        # 状态栏
        bar = pygame.Rect(0, STATUS_Y - 6, W, H - STATUS_Y + 6)
        strip = pygame.Surface(bar.size, pygame.SRCALPHA)
        strip.fill(STATUS_BG)
        surf.blit(strip, bar.topleft)
        text = self.message
        if self.game.is_won():
            text = "🎉 恭喜通关！按 N 或点「新局」再来一局"
            img = big_font.render(text, True, (255, 240, 120))
        else:
            img = status_font.render(text, True, TEXT_LIGHT)
        surf.blit(img, (MARGIN, STATUS_Y))

        # 拖拽中的牌置顶
        if self.drag is not None:
            from_loc, group, origin = self.drag
            mx, my = pygame.mouse.get_pos()
            dx, dy = mx - origin[0], my - origin[1]
            if from_loc[0] == "col":
                base_idx = len(self.game.columns[from_loc[1]]) - len(group)
                base_y = COL_Y0 + base_idx * self.col_step(from_loc[1]) + dy
            else:
                base_y = TOP_Y + dy
            base_x = self.col_x(from_loc[1]) if from_loc[0] == "col" else \
                (self.free_rect(from_loc[1]).x if from_loc[0] == "free"
                 else self.foundation_rect(from_loc[1]).x)
            for k, card in enumerate(group):
                self.draw_card(surf, base_x + dx, base_y + k * ROW_STEP, card)

        # 胜利弹窗
        if self.game.is_won():
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 110))
            surf.blit(overlay, (0, 0))
            panel = pygame.Rect(W // 2 - 250, H // 2 - 90, 500, 180)
            pygame.draw.rect(surf, (242, 241, 232), panel, border_radius=16)
            pygame.draw.rect(surf, (200, 170, 60), panel, width=3, border_radius=16)
            title = big_font.render("🎉 恭喜通关！", True, (150, 110, 20))
            hint = status_font.render("按 N 或点「新局」再来一局", True, (70, 70, 70))
            surf.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 26))
            surf.blit(hint, (panel.centerx - hint.get_width() // 2, panel.y + 100))


def main(max_frames=None):
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("空当接龙 FreeCell")

    rank_font = _load_font(26, bold=True)          # 牌面点数
    btn_font = _load_font(20)                      # 按钮/面板文字
    status_font = _load_font(22)                   # 状态栏
    big_font = _load_font(30, bold=True)           # 弹窗标题
    suit_big_font = _load_suit_font(52)            # 中央大花色
    suit_small_font = _load_suit_font(24)          # 角标花色
    _build_assets(rank_font, suit_big_font, suit_small_font)

    ui = GameUI()
    clock = pygame.time.Clock()
    frames = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.MOUSEMOTION:
                ui.hover_btn = None
                for key, rect, _ in ui.btn_rects():
                    if rect.collidepoint(event.pos):
                        ui.hover_btn = key
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                ui.handle_mouse_down(event.pos, pygame.time.get_ticks())
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                ui.handle_mouse_up(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                ui.selected = ui.drag = None
            elif event.type == pygame.KEYDOWN:
                ui.handle_key(event.key)

        # 死局提示
        if not ui.game.is_won() and not ui.game.any_move() and not ui.message:
            ui.message = "没有可移动的牌了，按 N 重开一局"

        ui.draw(screen, rank_font, btn_font, status_font, big_font)
        pygame.display.flip()
        clock.tick(60)
        frames += 1
        if max_frames is not None and frames >= max_frames:
            pygame.quit()
            return


if __name__ == "__main__":
    main()
