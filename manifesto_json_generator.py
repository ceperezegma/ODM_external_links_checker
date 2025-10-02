"""
A utility for converting an Excel file containing hierarchical tabular data into a structured JSON format.

The script reads Excel data, processes specific columns based on matching criteria,
and outputs the structured hierarchy into a JSON file. The input Excel file is expected
to contain columns such as tab/category names, hierarchical levels, and external links.
The JSON output maintains the tab order in which it appeared within the Excel file.

Functions
---------
- excel_to_json: Converts the specified Excel file into a structured JSON file.

Raises
------
RuntimeError: If no link column is found in the input Excel file.
"""

import json
import re

import pandas as pd


def excel_to_json(input_excel: str, output_json: str):
    """
    Convert an Excel file containing external links into a structured JSON file.

    Args:
        input_excel (str): Path to the input Excel file.
        output_json (str): Path where the output JSON file will be saved.

    Raises:
        RuntimeError: If no link column is found in the Excel file.

    Notes:
        - The function reads the first sheet of the Excel file and treats all cells
          as strings, stripping whitespace.
        - Columns are located heuristically using possible names:
            * Tab/Section/Category → determines the tab name.
            * Level/Tier/Depth → optional, determines the level for each link.
            * External link/Link/URL/Href → identifies the URLs.
        - Cells containing multiple URLs separated by spaces, commas, or semicolons
          are split into separate entries.
        - Only strings starting with "http://" or "https://" are considered valid URLs.
        - The resulting JSON structure is a dictionary mapping tab names to lists of
          dictionaries, each containing:
              - "level": the level string (may be empty)
              - "url": the external link
        - Tab order in the JSON preserves the order found in the Excel file.
        - The function prints a confirmation message when the JSON file is saved.
    """
    # Load Excel
    df = pd.read_excel(input_excel, sheet_name=0, dtype=str)

    # Strip all cells safely
    def sstrip(x):
        if x is None:
            return ""
        return str(x).strip()

    df = df.applymap(sstrip)

    # Helper to locate a column by name
    def find_col(possible_names):
        lower_map = {c.lower().strip(): c for c in df.columns}
        for name in possible_names:
            key = name.lower().strip()
            if key in lower_map:
                return lower_map[key]
        for c in df.columns:
            cl = c.lower()
            for name in possible_names:
                if name.lower() in cl:
                    return c
        return None

    tab_col = find_col(["Tab", "Section", "Category"])
    level_col = find_col(["Level", "Tier", "Depth"])
    link_col = find_col(["External link", "Link", "URL", "Href"])

    if not link_col:
        raise RuntimeError("No link column found in the Excel file.")

    url_pattern = re.compile(r"^https?://", re.IGNORECASE)

    nested = {}
    tab_order = []

    for _, row in df.iterrows():
        tab = row.get(tab_col, "Unknown") if tab_col else "Unknown"
        level = row.get(level_col, "") if level_col else ""
        cell = row.get(link_col, "")
        if not isinstance(cell, str) or not cell:
            continue

        if tab not in nested:
            nested[tab] = []
            tab_order.append(tab)

        parts = [p.strip() for p in re.split(r"[\s,;]+", cell) if url_pattern.match(p.strip())]
        for url in parts:
            nested[tab].append({"level": level, "url": url})

    # Preserve tab order as in Excel
    nested_in_order = {tab: nested[tab] for tab in tab_order}

    # Save to JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(nested_in_order, f, ensure_ascii=False, indent=2)

    print(f"JSON saved to {output_json}")


if __name__ == "__main__":
    excel_file = "ODM external links manifesto.xlsx"   # Input Excel filename
    json_file = "ODM_external_links_manifesto.json"     # Output JSON filename
    excel_to_json(excel_file, json_file)
