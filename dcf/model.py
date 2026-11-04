"""Core discounted-cash-flow math.

Everything here is plain Python so the model is easy to audit line by line,
the same way you would trace a formula in Excel.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Assumptions:
    """Inputs for a five-year (or N-year) unlevered FCF model, per share."""

    base_revenue: float            # last fiscal year revenue (in $mm)
    revenue_growth: list[float]    # one growth rate per forecast year, e.g. [0.22, 0.20, ...]
    fcf_margin: float              # free cash flow / revenue
    wacc: float                    # discount rate
    terminal_growth: float         # perpetual growth after the forecast window
    net_cash: float                # cash minus debt (in $mm); negative if net debt
    shares_outstanding: float      # diluted shares (or ADRs) in mm
    name: str = "Company"
    notes: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.wacc <= self.terminal_growth:
            raise ValueError("WACC must be greater than terminal growth, or the terminal value is infinite.")
        if not self.revenue_growth:
            raise ValueError("Need at least one forecast year.")
        if self.shares_outstanding <= 0:
            raise ValueError("Shares outstanding must be positive.")


@dataclass(frozen=True)
class Valuation:
    revenues: list[float]
    fcfs: list[float]
    discount_factors: list[float]
    pv_fcfs: list[float]
    terminal_value: float
    pv_terminal_value: float
    enterprise_value: float
    equity_value: float
    value_per_share: float

    @property
    def terminal_share_of_ev(self) -> float:
        """How much of the value sits in the terminal year. High numbers mean the
        answer is mostly a bet on the long run, which is worth flagging."""
        return self.pv_terminal_value / self.enterprise_value


def run_dcf(a: Assumptions) -> Valuation:
    revenues, fcfs, factors, pvs = [], [], [], []
    revenue = a.base_revenue
    for year, g in enumerate(a.revenue_growth, start=1):
        revenue *= 1 + g
        fcf = revenue * a.fcf_margin
        factor = 1 / (1 + a.wacc) ** year
        revenues.append(revenue)
        fcfs.append(fcf)
        factors.append(factor)
        pvs.append(fcf * factor)

    terminal_value = fcfs[-1] * (1 + a.terminal_growth) / (a.wacc - a.terminal_growth)
    pv_tv = terminal_value * factors[-1]
    ev = sum(pvs) + pv_tv
    equity = ev + a.net_cash
    return Valuation(
        revenues=revenues,
        fcfs=fcfs,
        discount_factors=factors,
        pv_fcfs=pvs,
        terminal_value=terminal_value,
        pv_terminal_value=pv_tv,
        enterprise_value=ev,
        equity_value=equity,
        value_per_share=equity / a.shares_outstanding,
    )


def sensitivity_grid(
    a: Assumptions,
    waccs: list[float],
    terminal_growths: list[float],
) -> list[list[float | None]]:
    """Value per share for each (WACC row, terminal-growth column) pair.

    Cells where WACC <= g are returned as None instead of raising, so the grid
    still prints the way an Excel data table would.
    """
    grid: list[list[float | None]] = []
    for w in waccs:
        row: list[float | None] = []
        for g in terminal_growths:
            if w <= g:
                row.append(None)
                continue
            row.append(run_dcf(replace(a, wacc=w, terminal_growth=g)).value_per_share)
        grid.append(row)
    return grid


def implied_growth(
    a: Assumptions,
    market_price: float,
    low: float = -0.5,
    high: float = 1.5,
    tol: float = 1e-7,
    max_iter: int = 200,
) -> float:
    """Reverse DCF: find the single, flat annual revenue growth rate (applied to
    every forecast year) that makes the model's value equal the market price.

    Uses bisection, which is what Goal Seek is doing in spirit, but deterministic.
    """

    def value_at(g: float) -> float:
        flat = [g] * len(a.revenue_growth)
        return run_dcf(replace(a, revenue_growth=flat)).value_per_share - market_price

    f_low, f_high = value_at(low), value_at(high)
    if f_low * f_high > 0:
        raise ValueError(
            f"Market price {market_price:,.2f} is outside the range the model can reach "
            f"with growth between {low:.0%} and {high:.0%}."
        )
    for _ in range(max_iter):
        mid = (low + high) / 2
        f_mid = value_at(mid)
        if abs(f_mid) < tol or (high - low) / 2 < tol:
            return mid
        if f_low * f_mid < 0:
            high = mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2
