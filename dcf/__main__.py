"""Command line entry point.

    python -m dcf examples/semis_example.json
    python -m dcf examples/semis_example.json --price 210
    python -m dcf examples/semis_example.json --csv out.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .model import Assumptions, implied_growth, run_dcf, sensitivity_grid


def load(path: Path) -> tuple[Assumptions, dict]:
    raw = json.loads(path.read_text())
    grid = raw.pop("sensitivity", {})
    return Assumptions(**raw), grid


def fmt_money(x: float) -> str:
    return f"{x:,.0f}"


def print_report(a: Assumptions, grid_cfg: dict, price: float | None, out=sys.stdout) -> None:
    v = run_dcf(a)
    w = out.write
    w(f"\n{a.name}: DCF summary\n" + "=" * (len(a.name) + 14) + "\n\n")
    w(f"{'Year':<6}{'Growth':>9}{'Revenue':>14}{'FCF':>12}{'PV of FCF':>13}\n")
    for i, (g, r, f, p) in enumerate(zip(a.revenue_growth, v.revenues, v.fcfs, v.pv_fcfs), start=1):
        w(f"{i:<6}{g:>9.1%}{fmt_money(r):>14}{fmt_money(f):>12}{fmt_money(p):>13}\n")
    w("\n")
    w(f"PV of terminal value   {fmt_money(v.pv_terminal_value):>14}  ({v.terminal_share_of_ev:.0%} of EV)\n")
    w(f"Enterprise value       {fmt_money(v.enterprise_value):>14}\n")
    w(f"+ Net cash             {fmt_money(a.net_cash):>14}\n")
    w(f"Equity value           {fmt_money(v.equity_value):>14}\n")
    w(f"Value per share        {v.value_per_share:>14,.2f}\n")

    waccs = grid_cfg.get("wacc", [a.wacc - 0.01, a.wacc, a.wacc + 0.01])
    gs = grid_cfg.get("terminal_growth", [a.terminal_growth - 0.005, a.terminal_growth, a.terminal_growth + 0.005])
    w("\nSensitivity: value per share (rows = WACC, cols = terminal growth)\n")
    w(f"{'':>8}" + "".join(f"{g:>10.1%}" for g in gs) + "\n")
    for wacc, row in zip(waccs, sensitivity_grid(a, waccs, gs)):
        w(f"{wacc:>8.1%}" + "".join(f"{'n/a' if c is None else f'{c:,.2f}':>10}" for c in row) + "\n")

    if price is not None:
        g = implied_growth(a, price)
        w(f"\nReverse DCF: a price of {price:,.2f} implies ~{g:.1%} revenue growth "
          f"per year for {len(a.revenue_growth)} years at a {a.fcf_margin:.0%} FCF margin.\n")
    w("\n")


def write_csv(a: Assumptions, path: Path) -> None:
    v = run_dcf(a)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["year", "growth", "revenue", "fcf", "discount_factor", "pv_fcf"])
        for i, row in enumerate(zip(a.revenue_growth, v.revenues, v.fcfs, v.discount_factors, v.pv_fcfs), 1):
            writer.writerow([i, *(round(x, 6) for x in row)])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dcf", description="Run a DCF, sensitivity grid and reverse DCF from a JSON file.")
    p.add_argument("config", type=Path)
    p.add_argument("--price", type=float, help="market price per share for a reverse DCF")
    p.add_argument("--csv", type=Path, help="write the yearly build to this CSV")
    args = p.parse_args(argv)

    a, grid_cfg = load(args.config)
    print_report(a, grid_cfg, args.price)
    if args.csv:
        write_csv(a, args.csv)
        print(f"Wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
