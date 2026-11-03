#!/usr/bin/env python3
"""Unit tests for tools/score.py (2026 Botball Fall Game scorer).

Run from the repo root:
    python tools/test_score.py
    python -m unittest discover -s tools -p "test_score.py" -v

Expected numbers are worked out by hand from docs/official/Botball_Fall_Game_Rule_Summary.txt
(pages 5-7) and the scoresheet, not copied from the scorer's output.
"""
from __future__ import annotations

import contextlib
import io
import itertools
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import score as S  # noqa: E402  (path set above)


def mk(**kw):
    """Scenario with Botguy/Big Duck out of play so only the piece under test scores."""
    return {"botguy": "none", "big_duck": "none", **kw}


def total(data, **interp):
    return S.score(data, interp or None)["total"]


def cups(*pieces, nested=False, orientation="upright"):
    return {"nested": nested, "nest_orientation": orientation, "pieces": list(pieces)}


def cup(upright=False, on_tape=False, touching_board=True):
    return {"upright": upright, "on_tape": on_tape, "touching_board": touching_board}


def zone_ducks(*zones, each=1):
    return {str(z): {"ducks": each} for z in zones}


class TestInterpretation(unittest.TestCase):
    def test_defaults_match_written_rule(self):
        d = S.default_interpretation()
        self.assertIs(d["zone5_counts_for_multiplier"], True)
        self.assertIs(d["pom_base_additive"], True)
        self.assertIs(d["special_base_additive"], True)
        self.assertIs(d["platform_counts_as_board_surface"], False)
        self.assertEqual(d["tape_duck_policy"], "ignore")
        self.assertEqual(d["pom_groups_per_zone"], "merge")
        self.assertIsNone(d["max_rings_per_neck"])

    def test_unknown_option_rejected(self):
        with self.assertRaises(ValueError):
            S.resolve_interpretation({"nonsense": True})

    def test_bad_value_rejected(self):
        for bad in ({"pom_base_additive": 1}, {"tape_duck_policy": "maybe"}, {"max_rings_per_neck": True},
                    {"max_rings_per_neck": 2}, {"zone5_counts_for_multiplier": "yes"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                S.resolve_interpretation(bad)

    def test_later_layer_wins_and_inputs_not_mutated(self):
        first = {"pom_base_additive": False}
        merged = S.resolve_interpretation(first, {"pom_base_additive": True})
        self.assertTrue(merged["pom_base_additive"])
        self.assertEqual(first, {"pom_base_additive": False})

    def test_scenario_embedded_overrides_apply_and_argument_wins(self):
        data = mk(interpretation={"zone5_counts_for_multiplier": False}, zones=zone_ducks(1, 2, 3, 4, 5))
        self.assertEqual(total(data), 20)                                   # embedded: 4x
        self.assertEqual(total(data, zone5_counts_for_multiplier=True), 25)  # argument wins: 5x


class TestPomGroups(unittest.TestCase):
    def poms(self, **colors):
        return mk(zones={"3": {"poms": colors}})

    def test_same_color_linear_additive_with_base(self):
        for n in (1, 2, 3, 4):
            with self.subTest(n=n):
                self.assertEqual(total(self.poms(red=n)), 2 * n)          # n group + n base
                self.assertEqual(total(self.poms(red=n), pom_base_additive=False), n)

    def test_complete_set_is_flat_25(self):
        self.assertEqual(total(self.poms(yellow=5)), 30)                          # 25 + 5 base
        self.assertEqual(total(self.poms(yellow=5), pom_base_additive=False), 25)

    def test_all_different_is_n_squared(self):
        colors = ["red", "yellow", "green", "blue", "purple"]
        for n in (2, 3, 4, 5):
            with self.subTest(n=n):
                data = self.poms(**dict.fromkeys(colors[:n], 1))
                self.assertEqual(total(data), n * n + n)
                self.assertEqual(total(data, pom_base_additive=False), n * n)

    def test_mixed_group_is_base_only_in_both_modes(self):
        for colors in ({"red": 2, "blue": 1}, {"red": 2, "blue": 2, "green": 1}, {"red": 4, "blue": 1}):
            with self.subTest(colors=colors):
                n = sum(colors.values())
                self.assertEqual(total(self.poms(**colors)), n)
                self.assertEqual(total(self.poms(**colors), pom_base_additive=False), n)

    def test_five_of_a_color_plus_another_color_is_mixed_not_a_set(self):
        # written rule: Complete Set needs "no other colors present"; the scoresheet formula alone would pay 25.
        self.assertEqual(total(self.poms(red=5, blue=1)), 6)

    def test_empty_zone_scores_nothing(self):
        self.assertEqual(total(mk(zones={"3": {"poms": {}}})), 0)

    def test_zones_are_independent(self):
        data = mk(zones={"1": {"poms": {"red": 3}}, "2": {"poms": {"blue": 2}}})
        self.assertEqual(total(data), 6 + 4)

    def test_multiple_piles_merge_vs_separate(self):
        data = mk(zones={"2": {"poms": [{"red": 3}, {"blue": 2}]}})
        self.assertEqual(total(data), 5)                                              # merged = mixed: base only
        self.assertEqual(total(data, pom_groups_per_zone="separate"), 6 + 4)         # 3 red + 2 blue, each additive
        self.assertEqual(total(data, pom_groups_per_zone="separate", pom_base_additive=False), 3 + 2)

    def test_color_aliases(self):
        self.assertEqual(total(self.poms(gold=2, yellow=1)), 6)                        # yellow x3 -> 3 + 3

    def test_poms_outside_zones_score_base_only(self):
        self.assertEqual(total(mk(poms_elsewhere={"red": 2, "blue": 1})), 3)

    def test_sixth_pom_of_a_color_rejected(self):
        data = mk(zones={"1": {"poms": {"red": 3}}, "2": {"poms": {"red": 3}}})
        with self.assertRaises(ValueError):
            S.score(data)
        with self.assertRaises(ValueError):
            S.score(mk(zones={"1": {"poms": {"red": 4}}}, platform={"poms": {"red": 2}}))

    def test_classify_pom_group(self):
        self.assertEqual(S.classify_pom_group({}), ("empty", 0, 0))
        self.assertEqual(S.classify_pom_group({"red": 1}), ("same_color", 1, 1))
        self.assertEqual(S.classify_pom_group({"red": 5}), ("complete_set", 5, 25))
        self.assertEqual(S.classify_pom_group({"red": 1, "blue": 1}), ("all_different", 2, 4))
        self.assertEqual(S.classify_pom_group({"red": 2, "blue": 1}), ("mixed", 3, 0))
        self.assertEqual(S.classify_pom_group({"red": 0, "blue": 3}), ("same_color", 3, 3))


class TestMysteryRedPom(unittest.TestCase):
    def platform(self, **kw):
        return mk(platform={"poms": {"red": 1}, "mystery_red_pom": True, **kw})

    def test_alone_scores_50_without_base(self):
        self.assertEqual(total(self.platform()), 50)

    def test_other_pom_on_platform_voids_bonus(self):
        data = mk(platform={"poms": {"red": 1, "blue": 1}, "mystery_red_pom": True})
        result = S.score(data)
        self.assertEqual(result["total"], 0)
        self.assertTrue(any("voided" in n for n in result["notes"]))

    def test_visible_red_pom_without_flag_scores_nothing_by_default(self):
        self.assertEqual(total(mk(platform={"poms": {"red": 1}})), 0)
        self.assertEqual(total(mk(platform={"poms": {"red": 1}}), any_red_pom_is_mystery=True), 50)

    def test_bonus_is_multiplied(self):
        data = self.platform()
        data["zones"] = zone_ducks(1, 2)
        self.assertEqual(S.score(data)["subtotal"], 52)       # 50 + 2 duck base
        self.assertEqual(total(data), 104)                    # x2

    def test_platform_as_board_surface_adds_base(self):
        self.assertEqual(total(self.platform(), platform_counts_as_board_surface=True), 51)
        self.assertEqual(total(self.platform(), platform_counts_as_board_surface=True,
                               special_base_additive=False), 50)

    def test_flag_without_red_pom_rejected(self):
        with self.assertRaises(ValueError):
            S.score(mk(platform={"poms": {"blue": 1}, "mystery_red_pom": True}))


class TestBotguyAndBigDuck(unittest.TestCase):
    def test_botguy_on_platform_15(self):
        self.assertEqual(total({"botguy": "platform", "big_duck": "none"}), 15)
        self.assertEqual(total({"botguy": "platform", "big_duck": "none"}, platform_counts_as_board_surface=True), 16)

    def test_big_duck_at_botguy_start_15_plus_base(self):
        self.assertEqual(total({"botguy": "none", "big_duck": "botguy_start"}), 16)
        self.assertEqual(total({"botguy": "none", "big_duck": "botguy_start"}, special_base_additive=False), 15)

    def test_big_duck_elsewhere_and_unmoved(self):
        self.assertEqual(total({"botguy": "none", "big_duck": "board"}), 1)
        self.assertEqual(total({"botguy": "none", "big_duck": "platform"}), 0)
        self.assertEqual(total({"botguy": "none", "big_duck": "platform"}, platform_counts_as_board_surface=True), 1)

    def test_unmoved_botguy_default_gets_base(self):
        self.assertEqual(total({}), 1)
        self.assertEqual(total({}, unmoved_botguy_scores_base=False), 0)
        self.assertEqual(total({"botguy": "board"}, unmoved_botguy_scores_base=False), 1)

    def test_swap_scores_both_fifteens(self):
        self.assertEqual(total({"botguy": "platform", "big_duck": "botguy_start"}), 31)

    def test_bad_states_rejected(self):
        for bad in ({"botguy": "floating"}, {"big_duck": "up"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                S.score(bad)


class TestDucksAndMultiplier(unittest.TestCase):
    def test_multiplier_steps(self):
        self.assertEqual(S.score(mk())["multiplier"], 1)
        for k, expected_mult in ((1, 1), (2, 2), (3, 3), (4, 4), (5, 5)):
            with self.subTest(k=k):
                data = mk(zones=zone_ducks(*range(1, k + 1)))
                self.assertEqual(S.score(data)["multiplier"], expected_mult)
                self.assertEqual(total(data), k * expected_mult)          # k duck base points x multiplier

    def test_zone_with_two_ducks_does_not_qualify(self):
        data = mk(zones={"1": {"ducks": 2}, "2": {"ducks": 1}, "3": {"ducks": 1}})
        result = S.score(data)
        self.assertEqual(result["qualifying_zones"], [2, 3])
        self.assertEqual(result["total"], 4 * 2)

    def test_ducks_under_platform_do_not_count_for_multiplier(self):
        data = mk(ducks={"under_platform": 5})
        self.assertEqual(S.score(data)["multiplier"], 1)
        self.assertEqual(total(data), 5 * (3 + 1))
        self.assertEqual(total(data, special_base_additive=False), 15)

    def test_ducks_elsewhere_off_tape_score_base_only(self):
        self.assertEqual(total(mk(ducks={"elsewhere_off_tape": 2})), 2)

    def test_tape_policy_duck_touching_tape_beside_clean_duck(self):
        data = mk(zones={"1": {"ducks": 1, "ducks_on_tape": 1}, "2": {"ducks": 1}})
        self.assertEqual(total(data), 2 * 2)                              # ignore: both zones qualify
        self.assertEqual(total(data, tape_duck_policy="count"), 2)        # zone 1 now has 2 ducks
        self.assertEqual(total(data, tape_duck_policy="spoil"), 2)

    def test_tape_policy_lone_duck_on_tape(self):
        data = mk(zones={"1": {"ducks_on_tape": 1}, "2": {"ducks": 1}, "3": {"ducks": 1}})
        self.assertEqual(total(data), 2 * 2)                              # ignore: zones 2,3
        self.assertEqual(total(data, tape_duck_policy="count"), 2 * 3)    # zone 1 qualifies too (no base for tape duck)
        self.assertEqual(total(data, tape_duck_policy="spoil"), 2 * 2)    # present but cannot qualify

    def test_zone5_exclusion(self):
        data = mk(zones=zone_ducks(1, 2, 3, 4, 5))
        self.assertEqual(total(data), 25)
        self.assertEqual(total(data, zone5_counts_for_multiplier=False), 5 * 4)   # zone-5 duck still earns base

    def test_big_duck_in_zone_option(self):
        data = mk(zones=zone_ducks(1, 2, 3), big_duck="board", big_duck_zone=3)
        self.assertEqual(total(data), 4 * 3)                                         # 3 ducks + big duck base, 3x
        self.assertEqual(total(data, big_duck_counts_for_multiplier=True), 4 * 2)    # zone 3 has two "ducks"

    def test_big_duck_zone_requires_board_state(self):
        with self.assertRaises(ValueError):
            S.score(mk(big_duck_zone=3))

    def test_multiplier_applies_to_whole_subtotal(self):
        data = mk(zones=zone_ducks(1, 2, 3), pickleballs={"under_platform": 1})
        self.assertEqual(S.score(data)["subtotal"], 3 + 8)
        self.assertEqual(total(data), 11 * 3)

    def test_zone_detail_reports_each_zone(self):
        detail = S.score(mk(zones=zone_ducks(2)))["multiplier_detail"]
        self.assertTrue(detail[2]["qualifies"])
        self.assertFalse(detail[1]["qualifies"])

    def test_too_many_ducks_rejected(self):
        with self.assertRaises(ValueError):
            S.score(mk(zones=zone_ducks(1, 2, 3, 4, 5), ducks={"under_platform": 1}))


class TestCups(unittest.TestCase):
    def test_flat_on_tape_earns_bonus_but_no_base(self):
        data = mk(cups=cups(cup(True, on_tape=True), cup(True, on_tape=True)))
        self.assertEqual(total(data), 40)

    def test_flat_off_tape_adds_base(self):
        data = mk(cups=cups(cup(True), cup(True)))
        self.assertEqual(total(data), 42)
        self.assertEqual(total(data, special_base_additive=False), 40)

    def test_plain_cups_follow_base_and_black_tape_rule(self):
        self.assertEqual(total(mk(cups=cups(cup(), cup()))), 2)
        self.assertEqual(total(mk(cups=cups(cup(on_tape=True)))), 0)

    def test_nested_regardless_of_tape(self):
        data = mk(cups=cups(cup(on_tape=True), cup(on_tape=True), nested=True))
        self.assertEqual(total(data), 20)

    def test_nested_off_tape_gives_base_to_both(self):
        data = mk(cups=cups(cup(), cup(), nested=True))
        self.assertEqual(total(data), 22)
        self.assertEqual(total(data, special_base_additive=False), 20)

    def test_nested_and_both_flat_is_60_as_written(self):
        data = mk(cups=cups(cup(True, on_tape=True), cup(True, on_tape=True), nested=True))
        self.assertEqual(total(data), 60)
        self.assertEqual(total(mk(cups=cups(cup(True), cup(True), nested=True))), 62)

    def test_inner_cup_off_the_board_is_not_flat(self):
        data = mk(cups=cups(cup(True), cup(True, touching_board=False), nested=True))
        self.assertEqual(total(data), 20 + 20 + 1)

    def test_inverted_nest_option(self):
        data = mk(cups=cups(cup(), cup(), nested=True, orientation="inverted"))
        self.assertEqual(total(data), 22)
        self.assertEqual(total(data, inverted_nest_counts_as_nested=False), 2)    # base only, no nested bonus

    def test_nested_needs_both_cups_and_max_two(self):
        with self.assertRaises(ValueError):
            S.score(mk(cups=cups(cup(), nested=True)))
        with self.assertRaises(ValueError):
            S.score(mk(cups=cups(cup(), cup(), cup())))

    def test_bad_orientation_rejected(self):
        with self.assertRaises(ValueError):
            S.score(mk(cups=cups(cup(), cup(), nested=True, orientation="sideways")))


class TestRingsAndPickleballs(unittest.TestCase):
    def test_rings(self):
        self.assertEqual(total(mk(rings={"on_neck": 2})), 30)                        # no Base: not on the board
        self.assertEqual(total(mk(rings={"touching_bottle": 2})), 2 * (3 + 1))
        self.assertEqual(total(mk(rings={"touching_bottle": 2}), special_base_additive=False), 6)
        self.assertEqual(total(mk(rings={"board_off_tape": 2})), 2)
        self.assertEqual(total(mk(rings={"on_neck": 6})), 90)

    def test_max_one_ring_per_neck(self):
        data = mk(rings={"on_neck": 3, "on_neck_per_bottle": [3, 0, 0]})
        self.assertEqual(total(data), 45)
        self.assertEqual(total(data, max_rings_per_neck=1), 15)
        spread = mk(rings={"on_neck": 3, "on_neck_per_bottle": [1, 1, 1]})
        self.assertEqual(total(spread, max_rings_per_neck=1), 45)

    def test_cap_needs_per_bottle_list(self):
        with self.assertRaises(ValueError):
            S.score(mk(rings={"on_neck": 2}), {"max_rings_per_neck": 1})

    def test_per_bottle_list_validated(self):
        with self.assertRaises(ValueError):
            S.score(mk(rings={"on_neck": 2, "on_neck_per_bottle": [1, 0, 0]}))
        with self.assertRaises(ValueError):
            S.score(mk(rings={"on_neck": 1, "on_neck_per_bottle": [1, 0]}))

    def test_seven_rings_rejected(self):
        with self.assertRaises(ValueError):
            S.score(mk(rings={"on_neck": 6, "board_off_tape": 1}))

    def test_pickleballs(self):
        self.assertEqual(total(mk(pickleballs={"under_platform": 4})), 4 * 8)
        self.assertEqual(total(mk(pickleballs={"under_platform": 4}), special_base_additive=False), 28)
        self.assertEqual(total(mk(pickleballs={"board_off_tape": 1})), 1)
        with self.assertRaises(ValueError):
            S.score(mk(pickleballs={"under_platform": 4, "board_off_tape": 1}))


class TestBaseScoreAndGates(unittest.TestCase):
    def test_judge_entered_base_count_overrides_derived(self):
        data = mk(zones=zone_ducks(1, 2), base_eligible_count=10)
        self.assertEqual(S.score(data)["subtotal"], 10)
        self.assertEqual(total(data), 20)                        # x2

    def test_derived_base_is_listed_in_the_note(self):
        result = S.score(mk(zones=zone_ducks(1)))
        self.assertIn("ducks in zones", result["items"][0]["note"])

    def test_robot_that_never_leaves_scores_zero(self):
        data = mk(zones=zone_ducks(1, 2, 3), robot={"left_start_box": False})
        result = S.score(data)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["ungated_total"], 9)                        # 3 duck base x 3
        self.assertIn("never left", result["gate"])

    def test_disqualification_scores_zero(self):
        result = S.score(mk(zones=zone_ducks(1, 2)), None)
        self.assertEqual(result["total"], 4)
        result = S.score(mk(zones=zone_ducks(1, 2), robot={"disqualified": True}))
        self.assertEqual(result["total"], 0)
        self.assertIn("disqualified", result["gate"])

    def test_non_object_scenario_rejected(self):
        for bad in ([], "x", 3, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                S.score(bad)

    def test_zone_keys_are_normalised(self):
        self.assertEqual(total(mk(zones={"01": {"ducks": 1}, 2: {"ducks": 1}})), 2 * 2)

    def test_scenario_is_not_mutated(self):
        data = mk(zones={"1": {"poms": {"red": 2}}})
        snapshot = json.dumps(data, sort_keys=True)
        S.score(data)
        S.sensitivity(data)
        self.assertEqual(json.dumps(data, sort_keys=True), snapshot)

    def test_validation_errors(self):
        bad_inputs = [
            {"zones": {"6": {}}},
            {"zones": {"1": {"ducks": -1}}},
            {"zones": {"1": {"ducks": True}}},
            {"zones": {"1": {"ducks": 1.5}}},
            {"zones": {"1": {"poms": {"pink": 1}}}},
            {"cups": {"nested": "yes", "pieces": []}},
            {"base_eligible_count": -3},
            {"robot": {"left_start_box": "yes"}},
            {"zones": {"1": None}},
            {"zones": {"1": {}, "01": {}}},
            {"zones": {"north": {}}},
            {"zones": []},
            {"cups": {"pieces": [None]}},
            {"cups": {"pieces": {}}},
            {"rings": {"on_neck": 1, "on_neck_per_bottle": "100"}},
            {"platform": []},
            {"interpretation": 3},
        ]
        for bad in bad_inputs:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                S.score(bad)


class TestScoresheetParity(unittest.TestCase):
    """The scoresheet xlsx pom formula must agree with classify_pom_group for correctly-entered B/C."""

    @staticmethod
    def sheet_pom(b, c):
        # =IF(B=5,25,IF(B>=1,B,IF(C>=2,C^2,0)))
        if b == 5:
            return 25
        if b >= 1:
            return b
        return c * c if c >= 2 else 0

    def test_formula_agrees_for_sorted_and_unique_groups(self):
        for n in range(1, 6):
            with self.subTest(sorted=n):
                _, _, pts = S.classify_pom_group({"red": n})
                self.assertEqual(self.sheet_pom(n, 0), pts)
        for n in range(2, 6):
            with self.subTest(unique=n):
                colors = dict.fromkeys(S.COLORS[:n], 1)
                _, _, pts = S.classify_pom_group(colors)
                self.assertEqual(self.sheet_pom(0, n), pts)

    def test_sheet_priority_trap_same_color_wins_if_b_is_filled(self):
        # If a judge types B=1 ("each color appears once") for a rainbow of 3, the sheet pays 1, not 9.
        self.assertEqual(self.sheet_pom(1, 3), 1)
        self.assertEqual(S.classify_pom_group({"red": 1, "blue": 1, "green": 1})[2], 9)

    def test_sheet_cannot_see_other_colors_for_five_of_a_kind(self):
        self.assertEqual(self.sheet_pom(5, 0), 25)       # sheet: 25 whatever else is in the zone
        self.assertEqual(S.classify_pom_group({"red": 5, "blue": 1})[0], "mixed")

    def test_xlsx_formulas_unchanged(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl not installed")
        path = REPO / "Botball_Fall_Seeding_Scoresheet.xlsx"
        if not path.exists():
            self.skipTest("scoresheet not in repo")
        ws = openpyxl.load_workbook(path).active
        for r in range(22, 27):
            self.assertEqual(ws[f"E{r}"].value, f"=IF(B{r}=5,25,IF(B{r}>=1,B{r},IF(C{r}>=2,C{r}^2,0)))")
        self.assertEqual(ws["E28"].value, "=SUM(E9:E18)+SUM(E22:E26)")
        self.assertEqual(ws["B37"].value, "=SUM(B32:B36)")
        self.assertEqual(ws["B38"].value, "=MAX(1,MIN(5,B37))")
        self.assertEqual(ws["E40"].value, "=E28*B38")
        points = {r: ws[f"D{r}"].value for r in range(9, 19)}
        self.assertEqual(points, {9: 1, 10: 7, 11: 3, 12: 15, 13: 3, 14: 20, 15: 20, 16: 15, 17: 15, 18: 50})


class TestDuckMath(unittest.TestCase):
    def test_totals_and_marginals(self):
        self.assertEqual(S.duck_zone_totals(20), [20, 21, 44, 69, 96, 125])
        self.assertEqual(S.duck_zone_marginals(20), [1, 23, 25, 27, 29])

    def test_marginal_formula_for_k_ge_2(self):
        for s in (0, 7, 33, 150):
            for k, m in enumerate(S.duck_zone_marginals(s), 1):
                self.assertEqual(m, 1 if k == 1 else s + 2 * k - 1)

    def test_zone_totals_cap_at_5x(self):
        self.assertEqual(S.duck_zone_totals(10, max_zones=5)[5], 15 * 5)

    def test_best_allocation_thresholds(self):
        self.assertEqual(S.best_duck_allocation(0), {"zones": 3, "under_platform": 2, "elsewhere": 0, "total": 33})
        self.assertEqual(S.best_duck_allocation(2), {"zones": 4, "under_platform": 1, "elsewhere": 0, "total": 40})
        self.assertEqual(S.best_duck_allocation(7)["total"], 60)      # tie between 4+1 and 5+0
        self.assertEqual(S.best_duck_allocation(8), {"zones": 5, "under_platform": 0, "elsewhere": 0, "total": 65})
        self.assertEqual(S.best_duck_allocation(100)["zones"], 5)

    def test_best_allocation_without_zone5(self):
        best = S.best_duck_allocation(100, {"zone5_counts_for_multiplier": False})
        self.assertEqual(best, {"zones": 4, "under_platform": 1, "elsewhere": 0, "total": (100 + 4 + 4) * 4})

    def test_best_allocation_matches_scorer(self):
        data = mk(zones=zone_ducks(1, 2, 3), ducks={"under_platform": 2})
        self.assertEqual(total(data), S.best_duck_allocation(0)["total"])


def best_pom_split(counts, additive):
    """Exhaustive optimum for splitting poms into at most 5 zone groups (independent check of the scorer)."""
    from functools import lru_cache

    value = {}
    for vec in itertools.product(range(6), repeat=5):
        kind, n, pts = S.classify_pom_group({c: v for c, v in zip(S.COLORS, vec) if v})
        value[vec] = 0 if kind == "empty" else (n if kind == "mixed" else pts + (n if additive else 0))

    @lru_cache(maxsize=None)
    def go(zones_left, remaining):
        if zones_left == 0 or not sum(remaining):
            return 0
        best = 0
        for sub in itertools.product(*[range(r + 1) for r in remaining]):
            nxt = tuple(sorted(r - s for r, s in zip(remaining, sub)))
            best = max(best, value[sub] + go(zones_left - 1, nxt))
        return best

    return go(5, tuple(sorted(counts)))


class TestValueTable(unittest.TestCase):
    """Rows of `--value-table` (and docs/rules-digest.md section 5.1) must equal what the scorer awards."""

    def test_item_rows_match_scorer(self):
        rows = {
            "Duck under platform": (mk(ducks={"under_platform": 1}), 4),
            "Pickleball under platform": (mk(pickleballs={"under_platform": 1}), 8),
            "Ring touching bottle": (mk(rings={"touching_bottle": 1}), 4),
            "Ring on neck": (mk(rings={"on_neck": 1}), 15),
            "Cup flat on tape": (mk(cups=cups(cup(True, on_tape=True))), 20),
            "Cup flat off tape": (mk(cups=cups(cup(True))), 21),
            "Botguy on platform": ({"botguy": "platform", "big_duck": "none"}, 15),
            "Big Duck at Botguy start": ({"botguy": "none", "big_duck": "botguy_start"}, 16),
            "Mystery Red Pom": (mk(platform={"poms": {"red": 1}, "mystery_red_pom": True}), 50),
            "Pom group of 5": (mk(zones={"3": {"poms": dict.fromkeys(S.COLORS, 1)}}), 30),
        }
        for label, (data, expected) in rows.items():
            with self.subTest(label=label):
                self.assertEqual(total(data), expected)
                self.assertIn(f"| {expected} |", S.value_table_markdown())

    def test_multiplier_columns(self):
        table = S.value_table_markdown()
        self.assertIn("| Mystery Red Pom alone on platform | 50 | 50 | 100 | 150 | 200 | 250 |", table)
        self.assertIn("| Cup flat/upright, off tape | 20 | 21 | 42 | 63 | 84 | 105 |", table)


class TestScenarioFiles(unittest.TestCase):
    EXPECTED = {
        "a_theoretical_max": (410, 5, 2050),
        "a2_theoretical_max_conservative": (325, 4, 1300),
        "b_ducks_only": (6, 5, 30),
        "c_novice": (43, 2, 86),
        "d_strong": (152, 3, 456),
        "e_ducks_under_platform": (21, 1, 21),
    }

    @staticmethod
    def load(name):
        return json.loads((REPO / "data" / "scenarios" / f"{name}.json").read_text(encoding="utf-8"))

    def test_totals(self):
        for name, (subtotal, mult, tot) in self.EXPECTED.items():
            with self.subTest(name=name):
                result = S.score(self.load(name))
                self.assertEqual((result["subtotal"], result["multiplier"], result["total"]), (subtotal, mult, tot))
                self.assertEqual(result["subtotal"] * result["multiplier"], result["total"])

    def test_expected_scenario_files_exist(self):
        files = {p.stem for p in (REPO / "data" / "scenarios").glob("*.json")}
        self.assertLessEqual(set(self.EXPECTED), files)

    def test_ducks_only_variants(self):
        data = self.load("b_ducks_only")
        self.assertEqual(total(data, unmoved_botguy_scores_base=False), 25)
        self.assertEqual(total(data, zone5_counts_for_multiplier=False), 6 * 4)

    def test_max_scenario_uses_each_piece_once(self):
        sc = S.normalize(self.load("a_theoretical_max"))
        by_color = Counter()
        for zone in sc["zones"].values():
            for group in zone["poms"]:
                by_color.update(group)
        by_color.update(sc["platform"]["poms"])
        self.assertEqual(dict(by_color), {color: 5 for color in S.COLORS})      # all 25 poms placed
        self.assertEqual(sum(z["ducks"] for z in sc["zones"].values()), 5)
        self.assertEqual(sc["pickleballs"]["under_platform"], 4)
        self.assertEqual(sc["rings"]["on_neck"], 6)
        self.assertEqual(len(sc["cups"]["pieces"]), 2)

    def test_max_scenario_pom_component_is_optimal(self):
        poms_only = {z: {"poms": self.load("a_theoretical_max")["zones"][z]["poms"]} for z in "12345"}
        self.assertEqual(total(mk(zones=poms_only)), 140)
        self.assertEqual(best_pom_split((4, 5, 5, 5, 5), additive=True), 140)
        self.assertEqual(best_pom_split((5, 5, 5, 5, 5), additive=True), 150)       # mystery on platform: 140 + 50 > 150

    def test_conservative_scenario_pom_component_is_optimal(self):
        poms_only = {z: {"poms": self.load("a2_theoretical_max_conservative")["zones"][z]["poms"]} for z in "12345"}
        self.assertEqual(total(mk(zones=poms_only), pom_base_additive=False), 116)
        self.assertEqual(best_pom_split((4, 5, 5, 5, 5), additive=False), 116)
        self.assertEqual(best_pom_split((5, 5, 5, 5, 5), additive=False), 125)      # 116 + 50 still wins

    def test_conservative_scenario_duck_split_is_optimal(self):
        cfg = self.load("a2_theoretical_max_conservative")["interpretation"]
        subtotal_without_ducks = 325 - 4 - 3
        best = S.best_duck_allocation(subtotal_without_ducks, cfg)
        self.assertEqual((best["zones"], best["under_platform"]), (4, 1))

    def test_sensitivity_label_for_embedded_rulings(self):
        rows = S.sensitivity(self.load("a2_theoretical_max_conservative"))
        self.assertEqual(rows[0], ("scenario's embedded rulings", 1300))

    def test_sensitivity_rows(self):
        rows = dict(S.sensitivity(self.load("d_strong")))
        self.assertEqual(rows["default (official written rule)"], 456)
        self.assertEqual(rows["zone5_counts_for_multiplier=False"], 456)          # no duck in zone 5 anyway
        self.assertEqual(rows["platform_counts_as_board_surface=True"], 3 * (152 + 2))   # Botguy + red pom gain Base
        self.assertLess(rows["ALL conservative rulings"], 456)


class TestCli(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = S.main(list(argv))
            except SystemExit as exc:  # argparse errors
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_table_output(self):
        code, out, _ = self.run_cli(str(REPO / "data" / "scenarios" / "c_novice.json"))
        self.assertEqual(code, 0)
        self.assertIn("TOTAL: 86", out)
        self.assertIn("Multiplier: 2x", out)

    def test_json_output(self):
        code, out, _ = self.run_cli(str(REPO / "data" / "scenarios" / "d_strong.json"), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["total"], 456)

    def test_set_override_and_conservative(self):
        path = str(REPO / "data" / "scenarios" / "b_ducks_only.json")
        code, out, _ = self.run_cli(path, "--set", "zone5_counts_for_multiplier=false", "--json")
        self.assertEqual((code, json.loads(out)["total"]), (0, 24))        # 6 base x 4
        code, out, _ = self.run_cli(path, "--conservative", "--json")
        self.assertEqual((code, json.loads(out)["total"]), (0, 20))        # no unmoved-Botguy base, 4x

    def test_sensitivity_flag(self):
        code, out, _ = self.run_cli(str(REPO / "data" / "scenarios" / "a_theoretical_max.json"), "--sensitivity")
        self.assertEqual(code, 0)
        self.assertIn("ALL conservative rulings", out)

    def test_value_table_and_options(self):
        code, out, _ = self.run_cli("--value-table")
        self.assertEqual(code, 0)
        self.assertIn("Marginal value of the k-th qualifying duck zone", out)
        code, out, _ = self.run_cli("--list-options")
        self.assertEqual(code, 0)
        for key in S.OPTIONS:
            self.assertIn(key, out)

    def test_errors_return_exit_code_2(self):
        code, _, err = self.run_cli(str(REPO / "data" / "scenarios" / "does_not_exist.json"))
        self.assertEqual(code, 2)
        self.assertIn("error", err)
        code, _, err = self.run_cli(str(REPO / "data" / "scenarios" / "c_novice.json"), "--set", "bogus=1")
        self.assertEqual(code, 2)

    def test_no_arguments_is_an_argparse_error(self):
        code, _, _ = self.run_cli()
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
