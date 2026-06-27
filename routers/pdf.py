# Copyright (c) 2026 Damian Migała / StockFlow

"""
Router: /pdf
  GET /pdf/{ticker}  — generuje raport PDF dla instrumentu

Używa fpdf2 (ten sam co w Streamlit). Endpoint zwraca plik PDF
z nagłówkiem Content-Disposition: attachment.
"""

from __future__ import annotations

import io
import os
import sys
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from stock_analyzer import analyze_ticker
from backend.core.security import OptionalCurrentUser

router = APIRouter(prefix="/pdf", tags=["reports"])


def _build_pdf(ticker: str, result: dict) -> bytes:
    """Generuje PDF z wynikami analizy. Zwraca bytes."""
    try:
        from fpdf import FPDF
    except ImportError:
        raise RuntimeError("fpdf2 nie jest zainstalowane: pip install fpdf2")

    score    = result.get("total_score", 0)
    score_st = result.get("score_st")
    name     = result.get("name", ticker)
    price    = result.get("price", 0)
    currency = result.get("currency", "USD")
    sector   = result.get("sector") or "—"
    comps    = result.get("components", [])
    flags    = result.get("red_flags") or []
    now      = datetime.now().strftime("%d.%m.%Y %H:%M")

    def score_label(s: float) -> str:
        return "Pozytywny" if s >= 60 else "Neutralny" if s >= 40 else "Negatywny"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # ── Nagłówek ──────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(34, 197, 94)      # brand green
    pdf.cell(0, 10, "StockFlow", ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)    # muted
    pdf.cell(0, 5, f"Raport analizy  ·  {now}", ln=True)
    pdf.ln(4)

    # ── Tytuł instrumentu ─────────────────────────────────────────────
    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(0.8)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(248, 250, 252)
    pdf.cell(0, 10, f"{name} ({ticker})", ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, f"Sektor: {sector}  ·  Cena: {price:.2f} {currency}", ln=True)
    pdf.ln(5)

    # ── Score boxy ────────────────────────────────────────────────────
    def draw_score_box(x: float, y: float, label: str, score_val: float, w: float = 80):
        clr = (34, 197, 94) if score_val >= 60 else (245, 158, 11) if score_val >= 40 else (239, 68, 68)
        pdf.set_xy(x, y)
        pdf.set_fill_color(30, 41, 59)
        pdf.set_draw_color(*clr)
        pdf.set_line_width(0.5)
        pdf.rect(x, y, w, 22, style="FD")
        pdf.set_xy(x + 2, y + 2)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(w - 4, 5, label.upper(), ln=True)
        pdf.set_xy(x + 2, y + 8)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*clr)
        pdf.cell(w // 2, 10, f"{score_val:.0f}/100")
        pdf.set_xy(x + 2 + w // 2, y + 11)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*clr)
        pdf.cell(w // 2 - 4, 7, score_label(score_val))

    y0 = pdf.get_y()
    draw_score_box(20, y0, "Wynik Długoterminowy (DT)", score, 82)
    if score_st is not None:
        draw_score_box(108, y0, "Wynik Krótkoterminowy (ST)", score_st, 82)

    pdf.set_y(y0 + 28)
    pdf.ln(3)

    # ── Składowe ──────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(248, 250, 252)
    pdf.cell(0, 8, "Składowe wyniku DT", ln=True)
    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(0.4)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)

    col_widths = [80, 25, 25, 40]
    headers    = ["Wskaźnik", "Wynik", "Waga", "Sygnał"]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(100, 116, 139)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 6, h)
    pdf.ln()

    pdf.set_line_width(0.2)
    pdf.set_draw_color(30, 41, 59)

    for comp in comps:
        s     = comp.get("score", 0) if isinstance(comp, dict) else getattr(comp, "score", 0)
        k     = comp.get("key", "") if isinstance(comp, dict) else getattr(comp, "key", "")
        w_pct = comp.get("weight", 0) if isinstance(comp, dict) else getattr(comp, "weight", 0)
        note  = comp.get("note", "") if isinstance(comp, dict) else getattr(comp, "note", "")
        clr   = (34, 197, 94) if s >= 60 else (245, 158, 11) if s >= 40 else (239, 68, 68)

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(248, 250, 252)
        pdf.cell(col_widths[0], 6, str(k)[:38])

        pdf.set_text_color(*clr)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_widths[1], 6, f"{s:.0f}")

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(col_widths[2], 6, f"{w_pct * 100:.0f}%")
        pdf.cell(col_widths[3], 6, str(note)[:22])
        pdf.ln()
        pdf.set_draw_color(30, 41, 59)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())

    pdf.ln(5)

    # ── Red flags ─────────────────────────────────────────────────────
    if flags:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(248, 250, 252)
        pdf.cell(0, 8, "Ostrzeżenia (Red Flags)", ln=True)
        pdf.set_draw_color(239, 68, 68)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(239, 68, 68)
        for flag in flags:
            pdf.cell(5, 6, "⚠")
            pdf.set_text_color(248, 250, 252)
            pdf.cell(0, 6, str(flag)[:90], ln=True)
            pdf.set_text_color(239, 68, 68)
        pdf.ln(3)

    # ── Stopka ────────────────────────────────────────────────────────
    pdf.set_y(-25)
    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(0.4)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, "StockFlow  ·  Narzędzie edukacyjne  ·  Nie stanowi porady inwestycyjnej", ln=True, align="C")
    pdf.cell(0, 5, f"Wygenerowano: {now}", align="C")

    return pdf.output()


@router.get(
    "/{ticker}",
    summary="Generate PDF report",
    description="Generuje raport PDF dla instrumentu. Zwraca plik do pobrania.",
    response_class=StreamingResponse,
)
async def generate_pdf(
    ticker: str,
    _user:  OptionalCurrentUser = None,
) -> StreamingResponse:
    """
    Endpoint publiczny — nie wymaga JWT.
    Generuje ten sam raport co Streamlit.
    """
    ticker = ticker.strip().upper()

    try:
        result = analyze_ticker(ticker)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Analysis failed: {e}")

    if "error" in result:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    try:
        pdf_bytes = _build_pdf(ticker, result)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    filename = f"StockFlow_{ticker}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type = "application/pdf",
        headers    = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length":      str(len(pdf_bytes)),
        },
    )
