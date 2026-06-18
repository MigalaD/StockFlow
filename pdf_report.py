"""
Raporty PDF
=============
Generuje raport PDF z analizą spółki: podstawowe dane, wynik ogólny,
rozbicie na wskaźniki, wykres ceny, ostrzeżenia (red flags) i disclaimer.

Wymaga: pip install reportlab matplotlib
"""

from __future__ import annotations

import os
import tempfile

import matplotlib
matplotlib.use("Agg")  # backend bez GUI - wymagany na serwerach/Streamlit
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

from stock_analyzer import INDICATOR_NAMES, WEIGHTS, interpret_score


def _score_color(score: float):
    if score >= 60:
        return colors.HexColor("#1a9850")
    if score >= 40:
        return colors.HexColor("#999999")
    return colors.HexColor("#d73027")


def _make_price_chart(df, ticker: str) -> str:
    """Tworzy wykres ceny + MA50/MA200 jako PNG, zwraca ścieżkę do pliku tymczasowego."""
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(df.index, df["Close"], label="Cena", color="#2563eb", linewidth=1.5)
    if "MA50" in df.columns:
        ax.plot(df.index, df["MA50"], label="MA50", color="#f59e0b", linewidth=1, linestyle="--")
    if "MA200" in df.columns:
        ax.plot(df.index, df["MA200"], label="MA200", color="#7c3aed", linewidth=1, linestyle="--")
    ax.set_title(f"Cena {ticker}")
    ax.legend(fontsize=8)
    ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmp.name, dpi=140)
    plt.close(fig)
    return tmp.name


def _make_score_chart(components: dict) -> str:
    """Tworzy wykres słupkowy rozbicia score jako PNG, zwraca ścieżkę do pliku tymczasowego."""
    names = [INDICATOR_NAMES.get(k, k) for k in components.keys()]
    values = [v[0] for v in components.values()]
    colors_list = ["#1a9850" if v >= 60 else "#999999" if v >= 40 else "#d73027" for v in values]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.barh(names, values, color=colors_list)
    ax.set_xlim(0, 100)
    ax.axvline(50, color="#888", linestyle="--", linewidth=1)
    ax.set_xlabel("Punkty (0-100)")
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmp.name, dpi=140)
    plt.close(fig)
    return tmp.name


def generate_stock_report(wynik: dict, df, output_path: str,
                           strategy_result: dict | None = None) -> str:
    """
    Generuje raport PDF dla jednej spółki.

    wynik: wynik z stock_analyzer.analyze_ticker()
    df: DataFrame z historią cen i wskaźnikami (Close, MA50, MA200, ...)
    output_path: gdzie zapisać PDF
    strategy_result: opcjonalny wynik strategies.evaluate_strategy()

    Zwraca output_path.
    """
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h2 = styles["Heading2"]
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=8, textColor=colors.grey)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )
    story = []

    ticker = wynik["ticker"]
    score = wynik["total_score"]

    # --- Naglowek ---
    asset_type = wynik.get("asset_type", "stock")
    story.append(Paragraph(
        f"{wynik['name']} ({ticker}) - {wynik.get('asset_type_label', 'Akcja')}",
        title_style,
    ))
    if asset_type == "stock":
        meta_line = (
            f"Cena: {wynik['price']} {wynik['currency']} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Sektor: {wynik.get('sector', 'Nieznany')} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Branza: {wynik.get('industry', 'Nieznana')}"
        )
    elif asset_type in ("etf", "etf_commodity"):
        meta_line = (
            f"Cena: {wynik['price']} {wynik['currency']} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Kategoria: {wynik.get('category') or 'Nieznana'} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Dostawca: {wynik.get('fund_family') or 'Nieznany'}"
        )
    else:
        meta_line = f"Cena: {wynik['price']} {wynik['currency']}"

    story.append(Paragraph(meta_line, normal))
    story.append(Spacer(1, 6))

    # --- Wynik ogolny ---
    score_table = Table(
        [[f"WYNIK OGOLNY: {score:.0f} / 100", interpret_score(score)]],
        colWidths=[6 * cm, 9 * cm],
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _score_color(score)),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 12))

    # --- Wykres ceny ---
    price_chart_path = _make_price_chart(df, ticker)
    story.append(Image(price_chart_path, width=16 * cm, height=6.8 * cm))
    story.append(Spacer(1, 6))

    # --- Wykres rozbicia score ---
    score_chart_path = _make_score_chart(wynik["components"])
    story.append(Image(score_chart_path, width=16 * cm, height=8 * cm))
    story.append(Spacer(1, 12))

    # --- Tabela szczegolow ---
    story.append(Paragraph("Szczegoly wskaznikow", h2))
    table_data = [["Wskaznik", "Wynik", "Waga", "Szczegoly"]]
    report_weights = wynik.get("weights", WEIGHTS)
    for key, (val, note) in wynik["components"].items():
        table_data.append([
            INDICATOR_NAMES.get(key, key),
            f"{val:.0f}/100",
            f"{report_weights.get(key, WEIGHTS.get(key, 0)):.0%}",
            Paragraph(note, small),
        ])
    details_table = Table(table_data, colWidths=[4.5 * cm, 1.8 * cm, 1.5 * cm, 8.2 * cm])
    details_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 12))

    # --- Dodatkowy kontekst (sektor / beta) ---
    extra_lines = []
    if wynik.get("sector_pe_comparison"):
        extra_lines.append(wynik["sector_pe_comparison"])
    beta_info = wynik.get("beta_info")
    if beta_info:
        idx_name = "WIG20" if beta_info["index"] == "^WIG20" else "S&P 500"
        extra_lines.append(
            f"Beta={beta_info['beta']:.2f}, korelacja={beta_info['correlation']:.2f} z {idx_name}"
        )
    if extra_lines:
        story.append(Paragraph("Dodatkowy kontekst", h2))
        for line in extra_lines:
            story.append(Paragraph(f"- {line}", normal))
        story.append(Spacer(1, 12))

    # --- Red flags ---
    red_flags = wynik.get("red_flags") or []
    if red_flags:
        story.append(Paragraph("Na co zwrocic uwage", h2))
        for flag in red_flags:
            # usuń emoji na początku - czcionki bazowe ich nie obsługują
            parts = flag.split(" ", 1)
            clean = parts[1] if len(parts) > 1 else flag
            story.append(Paragraph(f"- {clean}", normal))
        story.append(Spacer(1, 12))

    # --- Strategia (opcjonalnie) ---
    if strategy_result:
        story.append(PageBreak())
        story.append(Paragraph(f"Strategia: {strategy_result['nazwa']}", h2))
        story.append(Paragraph(strategy_result["opis"], normal))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"Zgodnosc: {strategy_result['met']} / {strategy_result['total']} "
            f"warunkow ({strategy_result['match_pct']:.0f}%)",
            normal,
        ))
        story.append(Spacer(1, 6))
        for opis_warunku, spelniony, szczegoly in strategy_result["conditions"]:
            znak = "[OK]" if spelniony else "[--]"
            story.append(Paragraph(f"{znak} {opis_warunku} - {szczegoly}", small))

    # --- Disclaimer ---
    story.append(Spacer(1, 18))
    story.append(Paragraph(
        "Disclaimer: Ten raport ma charakter edukacyjny/analityczny i nie "
        "stanowi porady inwestycyjnej w rozumieniu przepisow. Dane pochodza "
        "z Yahoo Finance i moga byc nieaktualne lub niedokladne. Wynik "
        "ogolny opisuje wylacznie obecna sytuacje na podstawie danych "
        "historycznych i nie przewiduje przyszlych cen. Decyzje "
        "inwestycyjne podejmujesz na wlasna odpowiedzialnosc.",
        small,
    ))

    doc.build(story)

    for p in (price_chart_path, score_chart_path):
        try:
            os.remove(p)
        except OSError:
            pass

    return output_path
