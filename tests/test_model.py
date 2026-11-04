import unittest
from dataclasses import replace

from dcf import Assumptions, implied_growth, run_dcf, sensitivity_grid


def simple() -> Assumptions:
    return Assumptions(
        base_revenue=100.0,
        revenue_growth=[0.10, 0.10],
        fcf_margin=0.20,
        wacc=0.10,
        terminal_growth=0.02,
        net_cash=10.0,
        shares_outstanding=10.0,
    )


class RunDcfTests(unittest.TestCase):
    def test_hand_calculated_example(self):
        v = run_dcf(simple())
        # Year 1: rev 110, fcf 22, pv 20.0
        # Year 2: rev 121, fcf 24.2, pv 20.0
        self.assertAlmostEqual(v.pv_fcfs[0], 20.0)
        self.assertAlmostEqual(v.pv_fcfs[1], 20.0)
        # TV = 24.2 * 1.02 / 0.08 = 308.55, PV = 308.55 / 1.21 = 255.0
        self.assertAlmostEqual(v.terminal_value, 308.55)
        self.assertAlmostEqual(v.pv_terminal_value, 255.0)
        self.assertAlmostEqual(v.enterprise_value, 295.0)
        self.assertAlmostEqual(v.value_per_share, 30.5)

    def test_higher_wacc_lowers_value(self):
        a = simple()
        self.assertLess(run_dcf(replace(a, wacc=0.12)).value_per_share, run_dcf(a).value_per_share)

    def test_rejects_wacc_below_terminal_growth(self):
        with self.assertRaises(ValueError):
            replace(simple(), wacc=0.02, terminal_growth=0.03)


class SensitivityTests(unittest.TestCase):
    def test_shape_and_invalid_cells(self):
        grid = sensitivity_grid(simple(), [0.03, 0.10], [0.02, 0.04])
        self.assertEqual(len(grid), 2)
        self.assertEqual(len(grid[0]), 2)
        self.assertIsNone(grid[0][1])  # wacc 3% <= g 4%
        self.assertAlmostEqual(grid[1][0], 30.5)


class ReverseDcfTests(unittest.TestCase):
    def test_round_trip(self):
        a = replace(simple(), revenue_growth=[0.15] * 5)
        price = run_dcf(a).value_per_share
        self.assertAlmostEqual(implied_growth(a, price), 0.15, places=5)

    def test_unreachable_price(self):
        with self.assertRaises(ValueError):
            implied_growth(simple(), 1e12)


if __name__ == "__main__":
    unittest.main()
