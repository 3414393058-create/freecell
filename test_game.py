"""game.py 规则逻辑的单元测试。运行：python -m unittest test_game -v"""
import random
import unittest

from game import Card, FreeCell, RANKS, SUITS, new_deck


def make_game(columns=None):
    """构造指定牌局的游戏。columns: list of list[(rank, suit)]，从底部到顶部。"""
    g = FreeCell(rng=random.Random(0))
    g.columns = [[Card(s, r) for r, s in col] for col in (columns or [])]
    g.columns += [[] for _ in range(8 - len(g.columns))]
    g.free = [None] * 4
    g.foundations = [[] for _ in range(4)]
    g.history = []
    return g


class TestDeal(unittest.TestCase):
    def test_deal_size_and_layout(self):
        g = FreeCell(rng=random.Random(1))
        total = sum(len(c) for c in g.columns)
        self.assertEqual(total, 52)
        self.assertEqual([len(c) for c in g.columns][:4], [7] * 4)
        self.assertEqual([len(c) for c in g.columns][4:], [6] * 4)
        # 无重复牌
        all_cards = [c for col in g.columns for c in col]
        self.assertEqual(len(set(all_cards)), 52)

    def test_deck_content(self):
        self.assertEqual(len(new_deck()), 52)
        self.assertEqual(len(set(new_deck())), 52)


class TestMoves(unittest.TestCase):
    def test_ace_to_foundation(self):
        g = make_game([[("A", "S")]])
        self.assertTrue(g.move(("col", 0), ("foundation", 0)))
        self.assertEqual(g.foundations[0][-1], Card("S", "A"))
        self.assertFalse(g.columns[0])

    def test_foundation_order(self):
        g = make_game([[("2", "S"), ("A", "S")]])    # 2 在底、A 在顶
        self.assertTrue(g.move(("col", 0), ("foundation", 0)))   # A♠
        self.assertEqual(len(g.foundations[0]), 1)
        self.assertTrue(g.move(("col", 0), ("foundation", 0)))   # 2♠
        self.assertEqual(len(g.foundations[0]), 2)
        # 空回收位只收 A：2 不能进
        g2 = make_game([[("2", "S")]])
        self.assertFalse(g2.move(("col", 0), ("foundation", 0)))
        # 错误花色：A♠ 已进 ♠ 位后，2♥ 不能进 ♠ 位
        g3 = make_game([[("2", "H"), ("A", "S")]])
        g3.move(("col", 0), ("foundation", 0))         # A♠
        self.assertFalse(g3.move(("col", 0), ("foundation", 0)))  # 2♥ → ♠ 位

    def test_column_alternate_desc(self):
        # 黑5 放到 红6 上：颜色相反且点数小 1 → 合法
        g = make_game([[("5", "S")], [("6", "H")]])
        self.assertTrue(g.move(("col", 0), ("col", 1)))
        # 同色不行：红5 放到 红6 上
        g2 = make_game([[("5", "H")], [("6", "H")]])
        self.assertFalse(g2.move(("col", 0), ("col", 1)))
        # 点数不连续不行：黑4 放到 红6 上
        g3 = make_game([[("4", "S")], [("6", "H")]])
        self.assertFalse(g3.move(("col", 0), ("col", 1)))

    def test_free_cell_one_card(self):
        g = make_game([[("K", "S")]])
        self.assertTrue(g.move(("col", 0), ("free", 0)))
        # free 已被占用 → 不能再放
        g.columns[0] = [Card("Q", "H")]
        self.assertFalse(g.move(("col", 0), ("free", 0)))
        # 多张一组不能整体进 free
        g2 = make_game([[("2", "S"), ("A", "H")]])   # 交替降序，可整体拖 2 张
        self.assertFalse(g2.move(("col", 0), ("free", 0)))

    def test_move_count_rule(self):
        g = FreeCell(rng=random.Random(0))          # 真实开局：4 空 free、0 空列
        self.assertEqual(g.can_move_count(), 5)     # (4+1) * 2^0
        g.free = [g.columns[0].pop() for _ in range(4)]   # free 占满、仍无空列
        self.assertEqual(g.can_move_count(), 1)     # (0+1) * 2^0
        g.columns[0] = []
        self.assertEqual(g.can_move_count(), 2)     # (0+1) * 2^1

    def test_long_run_limited_by_move_count(self):
        g = FreeCell(rng=random.Random(0))          # 8 列全满、无空列
        # 构造一列 3 张交替降序，但 free 占满、无空列 → 只能移动 1 张
        g.columns[0] = [Card("H", "K"), Card("S", "Q"), Card("H", "J")]
        g.free = [Card("S", "A"), Card("H", "A"), Card("D", "A"), Card("C", "A")]
        group = g.can_select(("col", 0))
        self.assertEqual(len(group), 1)                 # 只能拖 1 张
        self.assertEqual(group[0], Card("H", "J"))

    def test_group_move_keeps_order(self):
        g = make_game([[("5", "S"), ("4", "H"), ("3", "S")]])
        g.columns[1] = [Card("H", "6")]
        g.free = [None, None, None, None]               # 空 4 个 free → 可移 5 张
        self.assertTrue(g.move(("col", 0), ("col", 1)))
        self.assertEqual(g.columns[1][-3:], [Card("S", "5"), Card("H", "4"), Card("S", "3")])
        self.assertFalse(g.columns[0])

    def test_undo(self):
        g = make_game([[("A", "S")]])
        g.move(("col", 0), ("foundation", 0))
        self.assertTrue(g.undo())
        self.assertEqual(g.columns[0], [Card("S", "A")])
        self.assertFalse(g.foundations[0])
        self.assertFalse(g.undo())                       # 栈空

    def test_auto_collect(self):
        g = make_game([
            [("A", "S")], [("2", "S")], [("A", "H")], [],
            [], [], [], [],
        ])
        n = g.auto_collect()
        self.assertEqual(n, 3)
        self.assertEqual(len(g.foundations[0]), 2)       # ♠ A,2
        self.assertEqual(len(g.foundations[1]), 1)       # ♥ A

    def test_is_won(self):
        g = make_game()
        g.foundations = [[Card(s, r) for r in RANKS] for s in SUITS]
        self.assertTrue(g.is_won())

    def test_any_move_and_deadlock(self):
        # 2♠ 独列、free 被 4 张 K 占满（K 无法进空回收位）、其他列全空：
        # 唯一规则允许的只有「移入空列」这类不推进的走法 → 判定为死局
        g = make_game()
        g.columns = [[Card("S", "2")], [], [], [], [], [], [], []]
        g.free = [Card("S", "K"), Card("H", "K"), Card("D", "K"), Card("C", "K")]
        g.foundations = [[], [], [], []]
        self.assertFalse(g.any_move())
        # 完全收完的胜利局面也没有可推进的移动
        g2 = make_game()
        g2.foundations = [[Card(s, r) for r in RANKS] for s in SUITS]
        g2.columns = [[] for _ in range(8)]
        g2.free = [None] * 4
        self.assertFalse(g2.any_move())
        self.assertTrue(g2.is_won())


if __name__ == "__main__":
    unittest.main()
