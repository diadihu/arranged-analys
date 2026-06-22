from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arranged_analys.data.loader import filter_lottery_type, load_draw_history
from arranged_analys.features.engineering import build_basic_features
from arranged_analys.models.baseline import predict_by_recent_frequency


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a baseline prediction experiment.")
    parser.add_argument("--file", required=True, help="Path to the input CSV file.")
    parser.add_argument("--type", required=True, choices=["p3", "p5"], help="Lottery type.")
    parser.add_argument("--window-size", type=int, default=200, help="Recent record count for frequency baseline.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    digit_count = 3 if args.type == "p3" else 5

    df = load_draw_history(args.file)
    df = filter_lottery_type(df, args.type)
    feature_df = build_basic_features(df, digit_count=digit_count)
    prediction = predict_by_recent_frequency(
        feature_df,
        lottery_type=args.type,
        digit_count=digit_count,
        window_size=args.window_size,
    )

    payload = {
        "lottery_type": prediction.lottery_type,
        "window_size": prediction.window_size,
        "predicted_digits": prediction.predicted_digits,
        "digit_frequencies": prediction.digit_frequencies,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
