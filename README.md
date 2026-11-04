# dcf-toolkit

[![CI](https://github.com/Jaimelee3/dcf-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Jaimelee3/dcf-toolkit/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

A small, readable DCF engine in plain Python. It does what my Excel models do, and I can test it:

- **Forward DCF**: five-year (or N-year) unlevered FCF build, Gordon-growth terminal value, EV to equity bridge, value per share
- **Sensitivity grid**: WACC × terminal growth, laid out like an Excel data table
- **Reverse DCF**: solves for the revenue growth the current share price already assumes

I wrote it after building a DCF and reverse DCF for a semiconductor foundry in Excel. The useful question turned out to be the reverse one: *what growth does the market already expect, and for how long?* Here that question becomes a function you can test.

## Quick start

No installs needed, just Python 3.10+.

```bash
git clone https://github.com/Jaimelee3/dcf-toolkit
cd dcf-toolkit
python -m dcf examples/semis_example.json --price 250
```

```text
Year     Growth       Revenue         FCF    PV of FCF
1         24.0%       111,600      33,480       30,575
...
PV of terminal value          669,514  (78% of EV)
Value per share                176.24

Sensitivity: value per share (rows = WACC, cols = terminal growth)
              2.0%      2.5%      3.0%      3.5%      4.0%
    9.5%    157.94    166.43    176.24    187.67    201.19
...
Reverse DCF: a price of 250.00 implies ~29.9% revenue growth per year for 5 years at a 30% FCF margin.
```

> The example inputs are round, **hypothetical** numbers in the shape of a large foundry. They are not a forecast or a recommendation.

## Use it from Python

```python
from dcf import Assumptions, run_dcf, implied_growth

a = Assumptions(
    base_revenue=90_000, revenue_growth=[0.24, 0.22, 0.20, 0.18, 0.15],
    fcf_margin=0.30, wacc=0.095, terminal_growth=0.03,
    net_cash=60_000, shares_outstanding=5_186,
)
print(run_dcf(a).value_per_share)
print(implied_growth(a, market_price=250))
```

## How it works

| Step | Formula |
|---|---|
| Revenue | `Rₜ = Rₜ₋₁ × (1 + gₜ)` |
| Free cash flow | `FCFₜ = Rₜ × margin` |
| Discount factor | `1 / (1 + WACC)ᵗ` |
| Terminal value | `FCFₙ × (1 + g∞) / (WACC − g∞)` |
| Equity value | `Σ PV(FCF) + PV(TV) + net cash` |
| Reverse DCF | Bisection on a flat growth rate until model value equals price |

The report also prints the **terminal value's share of EV**. When that number is around 80%, most of the valuation depends on the long-run assumptions, so it's worth calling out in any write-up.

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests check a hand-calculated two-year case to the cent, sensitivity grid edge cases (WACC ≤ g), and a reverse DCF round trip (value at 15% growth → solve → 15%).

## Roadmap

- [ ] Mid-year discounting convention
- [ ] Margin ramp instead of a flat FCF margin
- [ ] Export the sensitivity grid to `.xlsx`

## License

MIT
