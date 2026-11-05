"""
Exports of the interactive tool (decisions #136, #142, #144): CSV, Excel (one sheet per table), chart HTML and one analysis package (ZIP).
Charts can also be saved as PNG with the camera button of every chart (browser, no extra package).
"""
import io
import re
import zipfile
from datetime import date

import pandas as pd
import plotly.io as pio


def safe_name(text, limit=60):
    """A file-name-safe version of a title."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")[:limit] or "table"


def csv_bytes(df, index=False):
    return df.to_csv(index=index).encode("utf-8")


def chart_html(fig, title):
    """A small interactive HTML file; the Plotly library is loaded from the internet when the file is opened (#144)."""
    fig = fig.to_dict()
    import plotly.graph_objects as go
    figure = go.Figure(fig)
    figure.update_layout(title=dict(text=title, x=0.01), margin=dict(t=70))
    return pio.to_html(figure, include_plotlyjs="cdn", full_html=True).encode("utf-8")


def readme_text(analysis, filters_text, n_accidents, extra=""):
    return (f"Analysis package of the road accident analysis tool\n"
            f"Date: {date.today().isoformat()}\n"
            f"Analysis: {analysis}\n"
            f"Accidents in the selection: {n_accidents:,}\n"
            f"Filters: {filters_text}\n\n"
            "What is in this package\n"
            "- tables/*.csv: the statistical tables of this analysis\n"
            "- charts/*.html: the charts as interactive pages (they load the Plotly library from the internet, so open them online)\n"
            "- filtered_accidents.csv (if included): the accidents that pass the filters\n\n"
            "How to read the numbers\n"
            "- An accident counts for a road-user group if that group is road user 1 or road user 2.\n"
            "- Severe = accident class 1, 2 or 3 (fatal, fatally injured, seriously injured). The class belongs to the whole accident, not to one road user.\n"
            "- Shares come with 95% Wilson intervals. Shares are not shown for fewer than 30 accidents and flagged as unstable under 100.\n"
            "- These are counts and shares, not rates per amount of traffic; the data contains no traffic or population figures.\n"
            "- Data: Belgian road accident open data 2017-2024, translated to English. Municipality outlines: Statbel, CC BY 4.0.\n" + (("\n" + extra + "\n") if extra else ""))


def excel_bytes(tables, filters_text, analysis):
    """One Excel workbook: a sheet with the filters, then one sheet per table (sheet names are cut to 31 characters)."""
    buffer = io.BytesIO()
    used = set()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"item": ["analysis", "date", "filters"], "value": [analysis, date.today().isoformat(), filters_text]}).to_excel(writer, sheet_name="Filters", index=False)
        for title, df in tables.items():
            name = re.sub(r"[\[\]\*\?/\\:]", "", title)[:31] or "table"
            base, i = name, 2
            while name in used or name == "Filters":
                name = f"{base[:28]}_{i}"; i += 1
            used.add(name)
            df.to_excel(writer, sheet_name=name, index=False)
    return buffer.getvalue()


def zip_bytes(tables, figs, readme, data_csv=None):
    """The analysis package: README, tables as CSV, charts as HTML, and optionally the filtered accidents."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", readme)
        for title, df in tables.items():
            z.writestr(f"tables/{safe_name(title)}.csv", csv_bytes(df))
        for title, fig in figs.items():
            z.writestr(f"charts/{safe_name(title)}.html", chart_html(fig, title))
        if data_csv is not None:
            z.writestr("filtered_accidents.csv", data_csv)
    return buffer.getvalue()
