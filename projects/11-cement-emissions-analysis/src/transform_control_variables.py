import argparse
from pathlib import Path

import pandas as pd


def reshape_control_variables(input_path: Path, sheet_name: str = "Dataset") -> pd.DataFrame:
    workbook = pd.read_excel(input_path, sheet_name=sheet_name)
    years_row = workbook.iloc[0]
    data_rows = workbook.iloc[1:].reset_index(drop=True)

    identifiers = data_rows.iloc[:, :3].copy()
    identifiers.columns = ["Kennziffer", "Raumeinheit", "Code"]

    variable_blocks: dict[str, list[tuple[int, int]]] = {}
    current_variable = None

    for index in range(3, len(workbook.columns)):
        column_name = workbook.columns[index]
        year_value = years_row.iloc[index]

        if not str(column_name).startswith("Unnamed"):
            current_variable = str(column_name)
            variable_blocks[current_variable] = []

        if pd.notna(year_value) and current_variable:
            try:
                year = int(float(year_value))
            except ValueError:
                continue
            variable_blocks[current_variable].append((index, year))

    reshaped_rows = []
    years = sorted({year for pairs in variable_blocks.values() for _, year in pairs})

    for region_index in range(len(identifiers)):
        region_info = identifiers.iloc[region_index]
        for year in years:
            row = {
                "Kennziffer": region_info["Kennziffer"],
                "Raumeinheit": region_info["Raumeinheit"],
                "Code": region_info["Code"],
                "Year": year,
            }
            for variable_name, year_columns in variable_blocks.items():
                value = None
                for column_index, column_year in year_columns:
                    if column_year == year:
                        value = data_rows.iloc[region_index, column_index]
                        break
                row[variable_name] = value
            reshaped_rows.append(row)

    return pd.DataFrame(reshaped_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reshape wide-format control variables into panel format.")
    parser.add_argument("input_path", type=Path, help="Path to the source Excel workbook.")
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("data/ml_ready_dataset_transformed.xlsx"),
        help="Where to save the transformed Excel file.",
    )
    parser.add_argument("--sheet-name", default="Dataset")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = args.output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    transformed = reshape_control_variables(args.input_path.resolve(), sheet_name=args.sheet_name)
    transformed.to_excel(output_path, index=False, sheet_name="ML_Data")
    print(f"Saved transformed dataset to: {output_path}")


if __name__ == "__main__":
    main()
