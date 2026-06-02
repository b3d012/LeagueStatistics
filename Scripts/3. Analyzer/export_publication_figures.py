from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "outputs_publication_analysis"
FIGURE_DIR = OUTPUT_DIR / "figures"


def load_csv(name: str) -> pd.DataFrame | None:
    path = OUTPUT_DIR / name
    if not path.exists():
        print(f"Skipping missing table: {path.name}")
        return None
    return pd.read_csv(path)


def prepare_figure_dir() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def save_current_figure(filename: str) -> None:
    path = FIGURE_DIR / filename
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    print(f"Saved figure: {path}")


def plot_rank_variance() -> None:
    df = load_csv("summary_rank_variance.csv")
    if df is None or df.empty:
        return

    plt.figure(figsize=(7, 4.5))
    plt.bar(df["region"], df["average_match_rank_variance"], color=["#2563eb", "#0f766e"])
    plt.ylabel("Average match rank variance")
    plt.title("Rank Variance by Region")
    plt.grid(axis="y", alpha=0.25)
    save_current_figure("rank_variance_by_region.png")


def plot_autofill_rate() -> None:
    df = load_csv("summary_autofill.csv")
    if df is None or df.empty:
        return

    plt.figure(figsize=(7, 4.5))
    plt.bar(df["region"], df["global_autofill_rate_percent"], color=["#7c3aed", "#dc2626"])
    plt.ylabel("Autofill rate (%)")
    plt.title("Autofill Rate by Region")
    plt.ylim(0, max(df["global_autofill_rate_percent"]) * 1.2)
    plt.grid(axis="y", alpha=0.25)
    save_current_figure("autofill_rate_by_region.png")


def plot_prediction_accuracy() -> None:
    df = load_csv("summary_predictability.csv")
    if df is None or df.empty:
        return

    plt.figure(figsize=(7, 4.5))
    plt.bar(df["region"], df["rank_based_win_prediction_accuracy_percent"], color=["#0ea5e9", "#16a34a"])
    plt.ylabel("Prediction accuracy (%)")
    plt.title("Rank-Based Win Prediction Accuracy")
    plt.ylim(0, max(df["rank_based_win_prediction_accuracy_percent"]) * 1.2)
    plt.grid(axis="y", alpha=0.25)
    save_current_figure("prediction_accuracy_by_region.png")


def plot_temporal_variance() -> None:
    df = load_csv("summary_temporal_hourly.csv")
    if df is None or df.empty:
        return

    plt.figure(figsize=(10, 5.2))
    for region, group in df.groupby("region"):
        group = group.sort_values("hour")
        plt.plot(group["hour"], group["avg_variance"], marker="o", linewidth=2, label=region)

    plt.xticks(range(24))
    plt.xlabel("Hour of day (GST)")
    plt.ylabel("Average rank variance")
    plt.title("Hourly Rank Variance Trend")
    plt.grid(axis="y", alpha=0.25)
    plt.legend(frameon=False)
    save_current_figure("temporal_rank_variance_by_hour.png")


def plot_smurf_gap() -> None:
    df = load_csv("summary_smurf_gap.csv")
    if df is None or df.empty:
        return

    plt.figure(figsize=(7.2, 4.5))
    plt.bar(df["region"], df["smurf_gap_levels"], color=["#f59e0b", "#ef4444"])
    plt.ylabel("Smurf gap (levels)")
    plt.title("Smurf Gap by Region")
    plt.grid(axis="y", alpha=0.25)
    save_current_figure("smurf_gap_by_region.png")


def plot_correlation() -> None:
    df = load_csv("summary_correlation.csv")
    if df is None or df.empty:
        return

    plt.figure(figsize=(7.2, 4.5))
    plt.axhline(0, color="black", linewidth=0.8)
    plt.bar(df["region"], df["correlation_coefficient"], color=["#6366f1", "#14b8a6"])
    plt.ylabel("Correlation coefficient")
    plt.title("Rank vs. Win Correlation")
    plt.grid(axis="y", alpha=0.25)
    save_current_figure("rank_win_correlation_by_region.png")


def main() -> None:
    prepare_figure_dir()
    plot_rank_variance()
    plot_autofill_rate()
    plot_prediction_accuracy()
    plot_temporal_variance()
    plot_smurf_gap()
    plot_correlation()
    print(f"Figures written to {FIGURE_DIR.resolve()}")


if __name__ == "__main__":
    main()
