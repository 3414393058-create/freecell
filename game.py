import random

SUITS = "SHDC"
RANKS = "A23456789TJQK"
SUIT_SYMBOLS = {"S": "\u2660", "H": "\u2665", "D": "\u2666", "C": "\u2663"}
RED_SUITS = {"H", "D"}

DECK_SIZE = 52


class Card:
    __slots__ = ("suit", "rank")

    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    @property
    def value(self):
        return RANKS.index(self.rank)

    @property
    def color(self):
        return "red" if self.suit in RED_SUITS else "black"

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def __eq__(self, other):
        return isinstance(other, Card) and other.suit == self.suit and other.rank == self.rank

    def __hash__(self):
        return hash((self.suit, self.rank))


def new_deck():
    return [Card(s, r) for s in SUITS for r in RANKS]


class FreeCell:
    NUM_COLS = 8
    NUM_FREE = 4
    NUM_FOUNDATIONS = 4

    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random.Random()
        self.reset()

    # ---------- 牌局生成 ----------
    def reset(self):
        """洗牌并发牌：交替发到 8 列，4 列 7 张、4 列 6 张。"""
        deck = new_deck()
        self.rng.shuffle(deck)
        self.columns = [[] for _ in range(self.NUM_COLS)]
        for i, card in enumerate(deck):
            self.columns[i % self.NUM_COLS].append(card)
        self.free = [None] * self.NUM_FREE
        self.foundations = [[] for _ in range(self.NUM_FOUNDATIONS)]
        self.history = []           # 撤销栈

    # 规则查询
    def can_move_count(self):
        """一次最多可移动的牌数 = (空自由单元格数 + 1) * 2^空列数。"""
        empty_free = sum(1 for c in self.free if c is None)
        empty_cols = sum(1 for c in self.columns if not c)
        return (empty_free + 1) * (2 ** empty_cols)

    def column_run(self, i):
        col = self.columns[i]
        n = len(col)
        if n == 0:
            return 0, []
        k = n - 1
        while k > 0 and col[k].value == col[k - 1].value - 1 \
                and col[k].color != col[k - 1].color:
            k -= 1
        limit = self.can_move_count()
        start = max(k, n - limit)
        return start, col[start:]

    def can_select(self, loc):
        kind, i = loc
        if kind == "free":
            c = self.free[i]
            return [c] if c is not None else []
        if kind == "foundation":
            f = self.foundations[i]
            return [f[-1]] if f else []
        if kind == "col":
            _, group = self.column_run(i)
            return group
        raise ValueError(f"未知位置类型: {kind}")

    def _col_valid_placement(self, i, bottom_card):
        """bottom_card 能否放到列 i 的顶部。"""
        col = self.columns[i]
        if not col:
            return True
        top = col[-1]
        return top.color != bottom_card.color and top.value == bottom_card.value + 1

    def _foundation_valid_placement(self, i, card):
        f = self.foundations[i]
        if not f:
            return card.value == 0                    # 只收 A
        top = f[-1]
        return top.suit == card.suit and card.value == top.value + 1

    def _foundation_index(self, suit):
        return SUITS.index(suit)

    def _placement_ok(self, to_loc, group):
        kind, i = to_loc
        bottom = group[0]
        if kind == "free":
            return self.free[i] is None and len(group) == 1
        if kind == "col":
            return self._col_valid_placement(i, bottom)
        if kind == "foundation":
            return len(group) == 1 and self._foundation_valid_placement(i, bottom)
        raise ValueError(f"未知位置类型: {kind}")

    def valid_move(self, from_loc, to_loc):
        group = self.can_select(from_loc)
        if not group:
            return False
        return self._placement_ok(to_loc, group)

    # ---------- 执行 ----------
    def move(self, from_loc, to_loc, n=None):
        group = self.can_select(from_loc)
        if not group:
            return False
        if n is not None:
            if n <= 0 or n > len(group):
                return False
            group = group[-n:]              # 取顶部 n 张（保持自下而上的顺序）
        if not self._placement_ok(to_loc, group):
            return False
        self._take(from_loc, len(group))
        self._put(to_loc, group)
        self.history.append((list(group), from_loc, to_loc))
        return True

    def _take(self, loc, n):
        kind, i = loc
        if kind == "free":
            self.free[i] = None
        elif kind == "foundation":
            del self.foundations[i][-n:]
        else:
            del self.columns[i][-n:]

    def _put(self, loc, group):
        kind, i = loc
        if kind == "free":
            self.free[i] = group[0]
        elif kind == "foundation":
            self.foundations[i].extend(group)
        else:
            self.columns[i].extend(group)

    def undo(self):
        if not self.history:
            return False
        group, from_loc, to_loc = self.history.pop()
        self._take(to_loc, len(group))
        self._put(from_loc, group)
        return True

    # ---------- 自动收牌 / 胜利 / 死局 ----------
    def collectible(self):
        locs = []
        for i in range(self.NUM_FREE):
            c = self.free[i]
            if c is not None and \
                    self._foundation_valid_placement(self._foundation_index(c.suit), c):
                locs.append(("free", i))
        for i in range(self.NUM_COLS):
            col = self.columns[i]
            if col:
                c = col[-1]
                if self._foundation_valid_placement(self._foundation_index(c.suit), c):
                    locs.append(("col", i))
        return locs

    def auto_collect(self):
        n = 0
        while True:
            locs = self.collectible()
            if not locs:
                break
            kind, i = locs[0]
            card = self.free[i] if kind == "free" else self.columns[i][-1]
            self.move((kind, i), ("foundation", self._foundation_index(card.suit)))
            n += 1
        return n

    def is_won(self):
        return sum(len(f) for f in self.foundations) == DECK_SIZE

    def any_move(self):
        sources = []
        for i in range(self.NUM_FREE):
            if self.free[i] is not None:
                sources.append(("free", i))
        for i in range(self.NUM_COLS):
            if self.columns[i]:
                sources.append(("col", i))
        for s in sources:
            group = self.can_select(s)
            for k in range(1, len(group) + 1):
                sub = group[-k:]
                for j in range(self.NUM_FREE):
                    if s != ("free", j) and self._placement_ok(("free", j), sub):
                        return True
                for j in range(self.NUM_COLS):
                    if s != ("col", j) and self.columns[j] \
                            and self._placement_ok(("col", j), sub):
                        return True
                for j in range(self.NUM_FOUNDATIONS):
                    if self._placement_ok(("foundation", j), sub):
                        return True
        return False
