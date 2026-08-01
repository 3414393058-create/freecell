"""边界与压力测试：随机模拟对局、撤销对称性、回收位拖出等。

运行：python -m unittest test_stress -v
"""
import os
import random
import unittest

from game import Card, FreeCell, RANKS, SUITS, new_deck


def make_game(columns=None, free=None, foundations=None):
    g = FreeCell(rng=random.Random(0))
    g.columns = [[Card(s, r) for r, s in col] for col in (columns or [])]
    while len(g.columns) < 8:
        g.columns.append([])
    g.free = [Card(s, r) for r, s in free] if free else [None] * 4
    if len(g.free) < 4:
        g.free += [None] * (4 - len(g.free))
    # foundations: 每堆为 [(rank, suit), ...] 从底到顶
    g.foundations = [[Card(s, r) for r, s in f] for f in (foundations or [[]] * 4)]
    g.history = []
    return g


def all_locations(g):
    """所有可能的来源位置。"""
    locs = []
    for i in range(8):
        if g.columns[i]:
            locs.append(("col", i))
    for i in range(4):
        if g.free[i] is not None:
            locs.append(("free", i))
        if g.foundations[i]:
            locs.append(("foundation", i))
    return locs


def all_targets(g):
    return ([("col", i) for i in range(8)]
            + [("free", i) for i in range(4)]
            + [("foundation", i) for i in range(4)])


class TestFoundationMoveOut(unittest.TestCase):
    def test_foundation_top_can_be_taken_out(self):
        g = make_game(foundations=[[("A", "S"), ("2", "S")], [], [], []])
        # 回收位 ♠ 顶部 2♠ 可拖出
        self.assertEqual(g.can_select(("foundation", 0)), [Card("S", "2")])
        # 拖到空列
        self.assertTrue(g.move(("foundation", 0), ("col", 0)))
        self.assertEqual(g.columns[0], [Card("S", "2")])
        self.assertEqual(g.foundations[0], [Card("S", "A")])
        # undo 恢复
        self.assertTrue(g.undo())
        self.assertEqual(g.foundations[0], [Card("S", "A"), Card("S", "2")])

    def test_foundation_to_free(self):
        g = make_game(foundations=[[("A", "S")], [], [], []])
        self.assertTrue(g.move(("foundation", 0), ("free", 0)))
        self.assertEqual(g.free[0], Card("S", "A"))
        self.assertFalse(g.foundations[0])


class TestUndoSymmetry(unittest.TestCase):
    def test_undo_restores_exact_state(self):
        """随机走 200 步，每步 undo 后状态必须与移动前完全一致。"""
        rng = random.Random(42)
        g = FreeCell(rng=rng)
        for step in range(200):
            before = self._snapshot(g)
            locs = all_locations(g)
            rng.shuffle(locs)
            moved = False
            for src in locs:
                targets = all_targets(g)
                rng.shuffle(targets)
                for dst in targets:
                    if dst == src:
                        continue
                    if g.move(src, dst):
                        moved = True
                        break
                if moved:
                    break
            if not moved:
                # 没有合法移动时撤销回到上一步再继续
                if g.history:
                    g.undo()
                continue
            self.assertTrue(g.undo())
            after = self._snapshot(g)
            self.assertEqual(before, after, f"第 {step} 步 undo 不对称")

    def _snapshot(self, g):
        return (tuple(tuple(c) for c in g.columns),
                tuple(g.free),
                tuple(tuple(c) for c in g.foundations))

    def test_undo_auto_collect(self):
        g = make_game([[("A", "S")], [("2", "S")], [("A", "H")], [], [], [], [], []])
        n = g.auto_collect()
        self.assertEqual(n, 3)
        for _ in range(n):
            self.assertTrue(g.undo())
        self.assertEqual(len(g.columns[0]), 1)
        self.assertEqual(len(g.columns[1]), 1)
        self.assertEqual(len(g.columns[2]), 1)
        self.assertEqual(sum(len(f) for f in g.foundations), 0)


class TestStateInvariants(unittest.TestCase):
    def test_invariants_hold_during_random_play(self):
        """随机合法对局中：牌数恒为 52、无重复、每列合法叠放。"""
        rng = random.Random(7)
        g = FreeCell(rng=rng)
        for _ in range(300):
            locs = all_locations(g)
            rng.shuffle(locs)
            for src in locs:
                targets = all_targets(g)
                rng.shuffle(targets)
                for dst in targets:
                    if dst == src:
                        continue
                    if g.move(src, dst):
                        break
                else:
                    continue
                break
            # 不变量
            all_cards = [c for col in g.columns for c in col]
            all_cards += [c for c in g.free if c]
            all_cards += [c for f in g.foundations for c in f]
            self.assertEqual(len(all_cards), 52)
            self.assertEqual(len(set(all_cards)), 52)
            # 列：仅要求「顶部 run」交替降序（开局发牌列底可任意顺序）
            for col in g.columns:
                n = len(col)
                s = n - 1
                while s > 0 and col[s].value == col[s - 1].value - 1 \
                        and col[s].color != col[s - 1].color:
                    s -= 1
                for a, b in zip(col[s:], col[s:][1:]):
                    self.assertEqual(a.value, b.value + 1)
                    self.assertNotEqual(a.color, b.color)
            for f in g.foundations:
                for a, b in zip(f, f[1:]):
                    self.assertEqual(a.suit, b.suit)
                    self.assertEqual(a.value + 1, b.value)

    def test_can_move_count_cases(self):
        g = FreeCell(rng=random.Random(0))          # 开局：4 空 free、0 空列
        self.assertEqual(g.can_move_count(), 5)     # (4+1)*2^0
        g.free[0] = g.columns[0].pop()              # 3 空 free、0 空列
        self.assertEqual(g.can_move_count(), 4)     # (3+1)*2^0
        g.columns[0] = []                           # 3 空 free、1 空列
        self.assertEqual(g.can_move_count(), 8)     # (3+1)*2^1
        g.free[1] = g.columns[1].pop()              # 2 空 free、1 空列
        self.assertEqual(g.can_move_count(), 6)     # (2+1)*2^1

    def test_won_state_has_no_meaningful_moves(self):
        g = make_game()
        g.foundations = [[Card(s, r) for r in RANKS] for s in SUITS]
        g.columns = [[] for _ in range(8)]
        g.free = [None] * 4
        self.assertTrue(g.is_won())
        self.assertFalse(g.any_move())

    def test_auto_collect_never_breaks_invariants(self):
        """从随机局面反复自动收牌，必须始终收敛且不变量成立。"""
        rng = random.Random(11)
        g = FreeCell(rng=rng)
        for _ in range(200):
            g.move(("col", rng.randrange(8)), ("free", rng.randrange(4))) \
                if g.columns[rng.randrange(8)] and g.free[rng.randrange(4)] is None else None
        g.auto_collect()
        all_cards = [c for col in g.columns for c in col]
        all_cards += [c for c in g.free if c]
        all_cards += [c for f in g.foundations for c in f]
        self.assertEqual(len(all_cards), 52)
        self.assertEqual(len(set(all_cards)), 52)


class TestPartialMove(unittest.TestCase):
    def test_move_top_n_cards_only(self):
        g = make_game([[("6", "S"), ("5", "H"), ("4", "S")]])   # run 3 张
        self.assertTrue(g.move(("col", 0), ("col", 1), n=1))     # 只移顶部 4♠
        self.assertEqual(g.columns[0], [Card("S", "6"), Card("H", "5")])
        self.assertEqual(g.columns[1], [Card("S", "4")])
        self.assertTrue(g.undo())
        self.assertEqual(len(g.columns[0]), 3)

    def test_move_top_n_to_foundation(self):
        # 双击收牌场景：run 多张，只收顶部 A♠
        g = make_game([[("3", "S"), ("2", "H"), ("A", "S")]])
        self.assertTrue(g.move(("col", 0), ("foundation", 0), n=1))
        self.assertEqual(g.foundations[0], [Card("S", "A")])
        self.assertEqual(g.columns[0], [Card("S", "3"), Card("H", "2")])
        # 整组 3 张不能进回收位
        self.assertFalse(g.move(("col", 0), ("foundation", 0)))

    def test_move_n_out_of_range(self):
        g = make_game([[("3", "S"), ("2", "H"), ("A", "S")]])
        self.assertFalse(g.move(("col", 0), ("col", 1), n=0))
        self.assertFalse(g.move(("col", 0), ("col", 1), n=4))

    def test_partial_move_undo_symmetry(self):
        """部分移动的撤销必须与整组移动一样严格对称。"""
        rng = random.Random(5)
        g = FreeCell(rng=rng)
        for step in range(100):
            before = (tuple(tuple(c) for c in g.columns), tuple(g.free),
                      tuple(tuple(c) for c in g.foundations))
            locs = all_locations(g)
            rng.shuffle(locs)
            moved = False
            for src in locs:
                targets = all_targets(g)
                rng.shuffle(targets)
                n = rng.randint(1, len(g.can_select(src)))
                for dst in targets:
                    if dst == src:
                        continue
                    if g.move(src, dst, n=n):
                        moved = True
                        break
                if moved:
                    break
            if not moved:
                if g.history:
                    g.undo()
                continue
            self.assertTrue(g.undo())
            after = (tuple(tuple(c) for c in g.columns), tuple(g.free),
                     tuple(tuple(c) for c in g.foundations))
            self.assertEqual(before, after, f"第 {step} 步部分移动 undo 不对称")


class TestUIInteraction(unittest.TestCase):
    """UI 层交互（点击截取、双击收牌），需要 pygame（dummy 驱动）。"""

    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        import main as m
        cls.m = m

    def _click_pos(self, col_idx, card_idx):
        m = self.m
        return (m.MARGIN + col_idx * m.GAP + 10, m.COL_Y0 + card_idx * 26 + 10)

    def test_double_click_collects_top_of_run(self):
        m = self.m
        g = make_game([[("3", "S"), ("2", "H"), ("A", "S")]])
        ui = m.GameUI(g)
        pos = self._click_pos(0, 2)                       # 列顶 A♠
        ui.handle_mouse_down(pos, 100)
        ui.handle_mouse_up(pos)
        ui.handle_mouse_down(pos, 300)                    # 双击
        ui.handle_mouse_up(pos)
        self.assertEqual(g.foundations[0], [Card("S", "A")])
        self.assertEqual(len(g.columns[0]), 2)

    def test_click_middle_selects_upper_part(self):
        m = self.m
        g = make_game([[("5", "S"), ("4", "H"), ("3", "S"), ("2", "H"), ("A", "S")]])
        ui = m.GameUI(g)
        ui.handle_mouse_down(self._click_pos(0, 2), 100)  # 点 3♠
        ui.handle_mouse_up(self._click_pos(0, 2))
        from_loc, group = ui.selected
        self.assertEqual(from_loc, ("col", 0))
        self.assertEqual([str(c) for c in group], ["3S", "2H", "AS"])

    def test_clicked_group_drop_uses_selected_n(self):
        """点击选中 run 上半段后，拖拽落位只移动选中部分。"""
        m = self.m
        g = make_game([[("5", "S"), ("4", "H"), ("3", "S"), ("2", "H"), ("A", "S")]])
        ui = m.GameUI(g)
        pos = self._click_pos(0, 2)
        ui.handle_mouse_down(pos, 100)
        ui.handle_mouse_up((pos[0] + 300, pos[1] + 80))   # 拖走
        self.assertEqual(len(g.columns[0]), 2)            # 只剩底 2 张
        self.assertEqual(sum(len(c) for c in g.columns), 5)  # 总牌数不变
        dst = [i for i in range(8) if g.columns[i][:1] == [Card("S", "3")]
               and len(g.columns[i]) == 3]
        self.assertEqual(len(dst), 1)                     # 3 张整体落在同一列



    def test_card_value_and_color(self):
        self.assertEqual(Card("S", "A").value, 0)
        self.assertEqual(Card("D", "K").value, 12)
        self.assertEqual(Card("H", "5").color, "red")
        self.assertEqual(Card("C", "5").color, "black")

    def test_deck_has_all_52(self):
        deck = new_deck()
        self.assertEqual(len(deck), 52)
        self.assertEqual(len(set(deck)), 52)
        for s in SUITS:
            for r in RANKS:
                self.assertIn(Card(s, r), deck)


if __name__ == "__main__":
    unittest.main()
