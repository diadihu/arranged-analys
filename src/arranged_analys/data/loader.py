from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {"draw_date", "lottery_type", "issue"}
DIGIT_COLUMNS = ["d1", "d2", "d3", "d4", "d5"]


def load_draw_history(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    for column in DIGIT_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    df["draw_date"] = pd.to_datetime(df["draw_date"])
    df["lottery_type"] = df["lottery_type"].astype(str).str.lower()
    df["issue"] = df["issue"].astype(str)

    for column in DIGIT_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df.sort_values(["lottery_type", "draw_date", "issue"]).reset_index(drop=True)


def filter_lottery_type(df: pd.DataFrame, lottery_type: str) -> pd.DataFrame:
    lottery_type = lottery_type.lower()
    filtered = df.loc[df["lottery_type"] == lottery_type].copy()
    if filtered.empty:
        raise ValueError(f"No records found for lottery_type={lottery_type!r}")
    return filtered.reset_index(drop=True)
