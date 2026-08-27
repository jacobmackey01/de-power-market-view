"""The single compact figure used by the generated market view."""

from __future__ import annotations

from pathlib import Path

import numpy as np


def _percent(value: float) -> str:
    return f"{value:.1%}" if np.isfinite(value) else "n/a"


def plot_market_view(result: dict, output_path: Path) -> None:
    """Save rates, seasonality and the latest setup in one reviewable figure."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    quartiles = result["residual_quartiles"]
    hours = result["hourly_rates"]
    months = result["monthly_rates"]
    daily = result["daily"]
    latest = result["latest_day"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    fig.suptitle(
        "DE-LU day-ahead negative-price risk — historical observed conditions",
        fontsize=15,
        fontweight="bold",
    )

    ax = axes[0, 0]
    x = np.arange(len(quartiles))
    rates = quartiles["negative_rate"].to_numpy(dtype=float)
    errors = np.vstack(
        [
            rates - quartiles["ci_low"].to_numpy(dtype=float),
            quartiles["ci_high"].to_numpy(dtype=float) - rates,
        ]
    )
    ax.bar(
        x,
        rates,
        color=["#176b87", "#4d94a8", "#9cc3cc", "#d7e8ea"],
        edgecolor="#17324d",
    )
    ax.errorbar(
        x,
        rates,
        yerr=errors,
        fmt="none",
        ecolor="#17324d",
        capsize=4,
        lw=1.2,
    )
    ax.set_xticks(x, ["Q1\nlowest", "Q2", "Q3", "Q4\nhighest"])
    ax.set_ylabel("Negative-price rate")
    ax.set_title("Risk by observed residual-load quartile")
    ax.grid(axis="y", alpha=0.25)
    for index, row in quartiles.iterrows():
        ax.text(
            index,
            min(0.98, row["ci_high"] + 0.012),
            f"{_percent(row['negative_rate'])}\n(n={int(row['n_hours']):,})",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    ax = axes[0, 1]
    ax.plot(
        hours["group"].astype(int),
        hours["negative_rate"],
        marker="o",
        color="#d95f02",
        lw=2,
    )
    ax.fill_between(
        hours["group"].astype(int),
        hours["ci_low"],
        hours["ci_high"],
        color="#d95f02",
        alpha=0.15,
        linewidth=0,
    )
    ax.set_xlabel("Local delivery hour")
    ax.set_ylabel("Negative-price rate")
    ax.set_title("Intraday pattern, with Wilson 95% interval")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(alpha=0.25)

    ax = axes[1, 0]
    ax.plot(
        months["group"].astype(int),
        months["negative_rate"],
        marker="o",
        color="#2a9d8f",
        lw=2,
    )
    ax.fill_between(
        months["group"].astype(int),
        months["ci_low"],
        months["ci_high"],
        color="#2a9d8f",
        alpha=0.15,
        linewidth=0,
    )
    ax.set_xlabel("Local month")
    ax.set_ylabel("Negative-price rate")
    ax.set_title("Seasonality, with Wilson 95% interval")
    ax.set_xticks(range(1, 13))
    ax.grid(alpha=0.25)

    for rate_axis in (axes[0, 0], axes[0, 1], axes[1, 0]):
        rate_axis.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))

    ax = axes[1, 1]
    ax.hist(
        daily["mean_residual_load_mw"],
        bins=20,
        color="#c7d7e5",
        edgecolor="white",
        label="Prior complete days",
    )
    ax.axvline(
        latest["mean_residual_load_mw"],
        color="#b2182b",
        lw=2.5,
        label=f"Latest day: {latest['local_date']}",
    )
    ax.set_xlabel("Mean residual load (MW)")
    ax.set_ylabel("Complete local days")
    ax.set_title("Latest observed setup in historical context")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.25)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
