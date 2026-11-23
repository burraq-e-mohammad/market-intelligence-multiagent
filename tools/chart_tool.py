"""
Deterministic Financial Chart Data Extractor & FPDF2 Pure-Vector Chart Renderer.
- Extracts 1Y daily price history + 50-day SMA, multi-year annual Revenue vs. Net Income,
  and profitability margin profiles directly from yfinance (100% free, zero scraping).
- Renders crisp, infinite-DPI vector charts directly into FPDF2 PDFs in memory (0 disk files).
- All outputs are pure Python JSON-safe primitives (dict/list/str/float/None).
"""
from typing import Dict, Any, List, Optional
import math


def _format_compact_currency(val: float, currency: str = "USD") -> str:
    """Format large numbers compactly for chart axes and bar labels (e.g. $478.8B, EUR 6.8B)."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return "N/A"
    sign = "-" if val < 0 else ""
    av = abs(float(val))
    prefix = "$" if currency == "USD" else f"{currency} "
    if av >= 1e12:
        return f"{sign}{prefix}{av / 1e12:.1f}T"
    if av >= 1e9:
        return f"{sign}{prefix}{av / 1e9:.1f}B"
    if av >= 1e6:
        return f"{sign}{prefix}{av / 1e6:.1f}M"
    if av >= 1e3:
        return f"{sign}{prefix}{av / 1e3:.1f}K"
    return f"{sign}{prefix}{av:,.2f}"


def _format_price_axis(val: float, currency: str = "USD") -> str:
    """Format price Y-axis ticks cleanly without clutter."""
    prefix = "$" if currency == "USD" else ""
    av = abs(val)
    if av >= 10000:
        return f"{prefix}{val:,.0f}"
    if av >= 100:
        return f"{prefix}{val:,.0f}"
    return f"{prefix}{val:,.2f}"


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def extract_chart_data(ticker_obj: Any, info: Dict[str, Any], currency: str = "USD") -> Dict[str, Any]:
    """
    Safely extract JSON-serializable chart datasets from a yfinance Ticker object and info dict.
    Never raises; returns partial datasets cleanly if any individual feed is unavailable.
    """
    chart_data: Dict[str, Any] = {
        "currency": currency or "USD",
        "price_history": [],
        "price_summary": {},
        "annual_financials": [],
        "margins": []
    }

    # 1. 1-Year Daily Stock Price History + 50-Day Moving Average
    try:
        hist = ticker_obj.history(period="1y", interval="1d", auto_adjust=True)
        if hist is not None and not hist.empty and "Close" in hist.columns:
            closes = hist["Close"].dropna()
            if len(closes) >= 5:
                sma50 = closes.rolling(window=50, min_periods=15).mean()
                points: List[Dict[str, Any]] = []
                for dt_idx, close_val in closes.items():
                    c_f = _safe_float(close_val)
                    if c_f is None:
                        continue
                    s_f = _safe_float(sma50.get(dt_idx)) if dt_idx in sma50.index else None
                    date_str = dt_idx.strftime("%Y-%m-%d") if hasattr(dt_idx, "strftime") else str(dt_idx)[:10]
                    points.append({
                        "date": date_str,
                        "close": round(c_f, 4),
                        "sma50": round(s_f, 4) if s_f is not None else None
                    })

                if points:
                    first_c = points[0]["close"]
                    last_c = points[-1]["close"]
                    all_c = [p["close"] for p in points]
                    ret_pct = ((last_c - first_c) / first_c * 100.0) if first_c > 0 else 0.0
                    chart_data["price_history"] = points
                    chart_data["price_summary"] = {
                        "start_date": points[0]["date"],
                        "end_date": points[-1]["date"],
                        "latest_close": last_c,
                        "high_1y": max(all_c),
                        "low_1y": min(all_c),
                        "return_1y_pct": round(ret_pct, 2)
                    }
    except Exception:
        pass

    # 2. Multi-Year Annual Revenue vs. Net Income (up to 4 most recent fiscal years)
    try:
        inc = getattr(ticker_obj, "income_stmt", None)
        if inc is None or (hasattr(inc, "empty") and inc.empty):
            inc = getattr(ticker_obj, "financials", None)
        if inc is not None and not inc.empty:
            rev_row_keys = ["Total Revenue", "Operating Revenue", "Revenue"]
            ni_row_keys = [
                "Net Income",
                "Net Income Common Stockholders",
                "Net Income Including Noncontrolling Interests",
                "Net Income Continuous Operations"
            ]
            rev_row = next((k for k in rev_row_keys if k in inc.index), None)
            ni_row = next((k for k in ni_row_keys if k in inc.index), None)

            if rev_row is not None:
                annual_rows: List[Dict[str, Any]] = []
                for col in inc.columns:
                    rev_v = _safe_float(inc.loc[rev_row, col])
                    ni_v = _safe_float(inc.loc[ni_row, col]) if ni_row is not None else None
                    if rev_v is None or rev_v <= 0:
                        continue
                    yr_num = col.year if hasattr(col, "year") else int(str(col)[:4])
                    annual_rows.append({
                        "year_num": yr_num,
                        "year": f"FY{yr_num}",
                        "revenue": rev_v,
                        "net_income": ni_v
                    })
                # Sort chronologically ascending, keep up to 4 most recent years
                annual_rows.sort(key=lambda r: r["year_num"])
                # Deduplicate same fiscal year (keep latest entry)
                dedup: Dict[int, Dict[str, Any]] = {}
                for r in annual_rows:
                    dedup[r["year_num"]] = r
                sorted_rows = [dedup[k] for k in sorted(dedup.keys())][-4:]
                for r in sorted_rows:
                    r.pop("year_num", None)
                chart_data["annual_financials"] = sorted_rows
    except Exception:
        pass

    # 3. Profitability Margin Profile (Gross, Operating, Net Margin)
    try:
        margin_specs = [
            ("Gross Margin", info.get("grossMargins")),
            ("Operating Margin", info.get("operatingMargins")),
            ("Net Profit Margin", info.get("profitMargins")),
        ]
        margins_list = []
        for label, raw_v in margin_specs:
            f_v = _safe_float(raw_v)
            if f_v is not None:
                margins_list.append({
                    "label": label,
                    "value": round(f_v * 100.0, 2)
                })
        chart_data["margins"] = margins_list
    except Exception:
        pass

    # 3b. Real-time direct zero-auth API integration for historical price closes
    if len(chart_data["price_history"]) < 5:
        try:
            sym_lookup = getattr(ticker_obj, "ticker", "") if hasattr(ticker_obj, "ticker") else (info.get("symbol") or "")
            if sym_lookup:
                from tools.finance_tool import fetch_live_chart_direct
                direct_res = fetch_live_chart_direct(sym_lookup)
                if direct_res and direct_res.get("closes"):
                    cls = direct_res["closes"]
                    if len(cls) >= 5:
                        pts = []
                        for i_c, c_val in enumerate(cls):
                            w_win = cls[max(0, i_c - 49): i_c + 1]
                            s_ma = round(sum(w_win) / len(w_win), 4) if len(w_win) >= 15 else None
                            pts.append({"date": f"D-{len(cls)-i_c}", "close": c_val, "sma50": s_ma})
                        chart_data["price_history"] = pts
                        first_pt = pts[0]["close"]
                        last_pt = pts[-1]["close"]
                        chart_data["price_summary"] = {
                            "start_date": pts[0]["date"],
                            "end_date": pts[-1]["date"],
                            "latest_close": last_pt,
                            "high_1y": max(cls),
                            "low_1y": min(cls),
                            "return_1y_pct": round(((last_pt - first_pt) / first_pt * 100.0), 2) if first_pt > 0 else 0.0
                        }
        except Exception:
            pass

    return chart_data


def _ensure_pdf_space(pdf: Any, needed_height_mm: float):
    """Add a new page cleanly if the chart card won't fit before page_break_trigger."""
    if pdf.get_y() + needed_height_mm > pdf.page_break_trigger:
        pdf.add_page()


def _draw_price_history_chart(
    pdf: Any,
    price_history: List[Dict[str, Any]],
    price_summary: Dict[str, Any],
    currency: str,
    company_name: str,
    ticker: str
):
    """Draw a crisp vector 1-Year Stock Price & 50-Day SMA chart card in FPDF2."""
    if len(price_history) < 5:
        return

    card_w = 190.0
    card_h = 66.0
    _ensure_pdf_space(pdf, card_h + 6)

    x0 = pdf.l_margin
    y0 = pdf.get_y() + 2.0

    # Card container
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_line_width(0.3)
    pdf.rect(x0, y0, card_w, card_h, style="DF")

    # Header bar
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(x0, y0, card_w, 9.5, style="F")
    pdf.set_draw_color(226, 232, 240)
    pdf.line(x0, y0 + 9.5, x0 + card_w, y0 + 9.5)

    # Chart Title
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(15, 23, 42)
    title_str = f"1-Year Stock Price & 50-Day Moving Average ({ticker}, {currency})"
    pdf.set_xy(x0 + 3.5, y0 + 2.2)
    pdf.cell(115, 5, title_str[:72])

    # Right summary badge (1Y return)
    ret_pct = price_summary.get("return_1y_pct", 0.0)
    ret_sign = "+" if ret_pct >= 0 else ""
    if ret_pct >= 0:
        pdf.set_text_color(5, 150, 105)
    else:
        pdf.set_text_color(220, 38, 38)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(x0 + card_w - 68, y0 + 2.2)
    pdf.cell(64.5, 5, f"1Y Return: {ret_sign}{ret_pct:.1f}%", align="R")

    # Plot area bounds
    px = x0 + 18.0
    py = y0 + 14.5
    pw = card_w - 23.0
    ph = 37.5

    closes = [p["close"] for p in price_history]
    smas = [p["sma50"] for p in price_history if p.get("sma50") is not None]
    all_vals = closes + smas
    v_min = min(all_vals)
    v_max = max(all_vals)
    span = v_max - v_min
    if span <= 0:
        span = max(v_max * 0.1, 1.0)
    y_low = max(0.0, v_min - span * 0.08)
    y_high = v_max + span * 0.08
    y_span = y_high - y_low

    def map_x(idx: int) -> float:
        if len(price_history) <= 1:
            return px
        return px + (idx / (len(price_history) - 1)) * pw

    def map_y(val: float) -> float:
        return py + ph - ((val - y_low) / y_span) * ph

    # Horizontal gridlines & Y-axis labels (4 steps)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(100, 116, 139)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.2)
    for step in range(5):
        frac = step / 4.0
        gy = py + ph - frac * ph
        gv = y_low + frac * y_span
        pdf.line(px, gy, px + pw, gy)
        lbl = _format_price_axis(gv, currency)
        pdf.set_xy(x0 + 1.5, gy - 2.0)
        pdf.cell(15.5, 4, lbl[:11], align="R")

    # Soft shaded area polygon under closing price line
    poly_pts = [(map_x(0), py + ph)]
    for i, p in enumerate(price_history):
        poly_pts.append((map_x(i), map_y(p["close"])))
    poly_pts.append((map_x(len(price_history) - 1), py + ph))
    pdf.set_fill_color(239, 246, 255)
    pdf.polygon(poly_pts, style="F")

    # Close price curve (primary blue)
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.5)
    for i in range(1, len(price_history)):
        pdf.line(
            map_x(i - 1), map_y(price_history[i - 1]["close"]),
            map_x(i), map_y(price_history[i]["close"])
        )

    # 50-Day SMA curve (amber dashed)
    pdf.set_draw_color(217, 119, 6)
    pdf.set_line_width(0.38)
    pdf.set_dash_pattern(dash=1.4, gap=1.0)
    prev_sma_pt = None
    for i, p in enumerate(price_history):
        s_val = p.get("sma50")
        if s_val is not None:
            cur_pt = (map_x(i), map_y(s_val))
            if prev_sma_pt is not None:
                pdf.line(prev_sma_pt[0], prev_sma_pt[1], cur_pt[0], cur_pt[1])
            prev_sma_pt = cur_pt
        else:
            prev_sma_pt = None
    pdf.set_dash_pattern()  # reset dash

    # Highlight latest point dot
    last_x = map_x(len(price_history) - 1)
    last_y = map_y(price_history[-1]["close"])
    pdf.set_fill_color(37, 99, 235)
    pdf.circle(last_x, last_y, 1.0, style="F")

    # X-axis baseline & 5 evenly-spaced date labels
    pdf.set_draw_color(148, 163, 184)
    pdf.set_line_width(0.25)
    pdf.line(px, py + ph, px + pw, py + ph)

    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(100, 116, 139)
    n = len(price_history)
    tick_indices = sorted(set([0, n // 4, n // 2, (3 * n) // 4, n - 1]))
    for idx in tick_indices:
        tx = map_x(idx)
        d_raw = price_history[idx]["date"]
        # Format YYYY-MM-DD -> Mon 'YY
        try:
            from datetime import datetime
            d_lbl = datetime.strptime(d_raw, "%Y-%m-%d").strftime("%b '%y")
        except Exception:
            d_lbl = d_raw[:7]
        align = "L" if idx == 0 else ("R" if idx == n - 1 else "C")
        box_x = tx if idx == 0 else (tx - 18 if idx == n - 1 else tx - 9)
        pdf.set_xy(box_x, py + ph + 1.2)
        pdf.cell(18, 3.8, d_lbl, align=align)

    # Bottom Legend + 1Y High/Low stats
    ly = y0 + card_h - 6.8
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.6)
    pdf.line(x0 + 4.0, ly + 2.0, x0 + 9.0, ly + 2.0)
    pdf.set_font("Helvetica", "", 7.2)
    pdf.set_text_color(51, 65, 85)
    pdf.set_xy(x0 + 10.2, ly)
    pdf.cell(26, 4, "Close Price")

    pdf.set_draw_color(217, 119, 6)
    pdf.set_dash_pattern(dash=1.2, gap=0.8)
    pdf.line(x0 + 36.0, ly + 2.0, x0 + 41.0, ly + 2.0)
    pdf.set_dash_pattern()
    pdf.set_xy(x0 + 42.2, ly)
    pdf.cell(30, 4, "50-Day SMA")

    hi_s = _format_price_axis(price_summary.get("high_1y", v_max), currency)
    lo_s = _format_price_axis(price_summary.get("low_1y", v_min), currency)
    cur_s = _format_price_axis(price_summary.get("latest_close", closes[-1]), currency)
    pdf.set_xy(x0 + 76.0, ly)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(110.5, 4, f"Latest: {cur_s} {currency}   |   1Y Range: {lo_s} - {hi_s} {currency}", align="R")

    pdf.set_line_width(0.2)
    pdf.set_y(y0 + card_h + 3.5)


def _draw_annual_financials_chart(
    pdf: Any,
    annual_financials: List[Dict[str, Any]],
    currency: str,
    ticker: str
):
    """Draw a crisp vector Multi-Year Annual Revenue vs. Net Income grouped bar chart in FPDF2."""
    if len(annual_financials) < 2:
        return

    card_w = 190.0
    card_h = 62.0
    _ensure_pdf_space(pdf, card_h + 6)

    x0 = pdf.l_margin
    y0 = pdf.get_y() + 2.0

    # Card container
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_line_width(0.3)
    pdf.rect(x0, y0, card_w, card_h, style="DF")

    # Header bar
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(x0, y0, card_w, 9.5, style="F")
    pdf.set_draw_color(226, 232, 240)
    pdf.line(x0, y0 + 9.5, x0 + card_w, y0 + 9.5)

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(15, 23, 42)
    pdf.set_xy(x0 + 3.5, y0 + 2.2)
    pdf.cell(110, 5, f"Annual Revenue vs. Net Income ({ticker}, {currency})")

    # Top-right Legend inside header
    pdf.set_fill_color(30, 64, 175)
    pdf.rect(x0 + card_w - 58, y0 + 3.2, 3.0, 3.0, style="F")
    pdf.set_font("Helvetica", "", 7.2)
    pdf.set_text_color(51, 65, 85)
    pdf.set_xy(x0 + card_w - 54.2, y0 + 2.5)
    pdf.cell(20, 4.5, "Revenue")

    pdf.set_fill_color(16, 185, 129)
    pdf.rect(x0 + card_w - 31, y0 + 3.2, 3.0, 3.0, style="F")
    pdf.set_xy(x0 + card_w - 27.2, y0 + 2.5)
    pdf.cell(24, 4.5, "Net Income")

    # Plot bounds
    px = x0 + 22.0
    py = y0 + 15.5
    pw = card_w - 28.0
    ph = 35.5

    vals = []
    for r in annual_financials:
        if r.get("revenue") is not None:
            vals.append(r["revenue"])
        if r.get("net_income") is not None:
            vals.append(r["net_income"])
    v_max = max(max(vals), 1.0) * 1.15
    v_min = min(min(vals), 0.0)
    if v_min < 0:
        v_min *= 1.15
    v_span = v_max - v_min

    def map_y(val: float) -> float:
        return py + ph - ((val - v_min) / v_span) * ph

    zero_y = map_y(0.0)

    # Gridlines & Y labels
    pdf.set_font("Helvetica", "", 6.8)
    pdf.set_text_color(100, 116, 139)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.2)
    for step in range(4):
        frac = step / 3.0
        gy = py + ph - frac * ph
        gv = v_min + frac * v_span
        pdf.line(px, gy, px + pw, gy)
        lbl = _format_compact_currency(gv, currency)
        pdf.set_xy(x0 + 1.5, gy - 2.0)
        pdf.cell(19.5, 4, lbl[:14], align="R")

    # Grouped bars
    n_groups = len(annual_financials)
    group_w = pw / n_groups
    bar_w = min(14.0, group_w * 0.30)
    gap = 2.0

    for idx, row in enumerate(annual_financials):
        cx = px + group_w * (idx + 0.5)
        rev = row.get("revenue")
        ni = row.get("net_income")

        # Revenue bar (Navy)
        if rev is not None:
            bx = cx - bar_w - gap / 2.0
            by = map_y(rev)
            bh = abs(zero_y - by)
            pdf.set_fill_color(30, 64, 175)
            pdf.rect(bx, min(by, zero_y), bar_w, max(bh, 0.5), style="F")
            # Label above bar
            pdf.set_font("Helvetica", "B", 6.6)
            pdf.set_text_color(30, 58, 138)
            pdf.set_xy(bx - 4.0, min(by, zero_y) - 4.0)
            pdf.cell(bar_w + 8.0, 3.6, _format_compact_currency(rev, currency), align="C")

        # Net Income bar (Emerald if >=0 else Coral Red)
        if ni is not None:
            bx2 = cx + gap / 2.0
            by2 = map_y(ni)
            bh2 = abs(zero_y - by2)
            if ni >= 0:
                pdf.set_fill_color(16, 185, 129)
                pdf.set_text_color(5, 150, 105)
                lbl_y = min(by2, zero_y) - 4.0
            else:
                pdf.set_fill_color(239, 68, 68)
                pdf.set_text_color(220, 38, 38)
                lbl_y = max(by2, zero_y) + 0.6
            pdf.rect(bx2, min(by2, zero_y), bar_w, max(bh2, 0.5), style="F")
            pdf.set_font("Helvetica", "B", 6.6)
            pdf.set_xy(bx2 - 4.0, lbl_y)
            pdf.cell(bar_w + 8.0, 3.6, _format_compact_currency(ni, currency), align="C")

        # Fiscal Year X label
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(51, 65, 85)
        pdf.set_xy(cx - 12.0, py + ph + 2.2)
        pdf.cell(24.0, 4.2, str(row.get("year", "")), align="C")

    # Zero axis line
    pdf.set_draw_color(148, 163, 184)
    pdf.set_line_width(0.3)
    pdf.line(px, zero_y, px + pw, zero_y)

    pdf.set_line_width(0.2)
    pdf.set_y(y0 + card_h + 3.5)


def _draw_margins_chart(pdf: Any, margins: List[Dict[str, Any]], ticker: str):
    """Draw a compact vector Profitability Margin Profile horizontal bar card in FPDF2."""
    if not margins:
        return

    card_w = 190.0
    row_h = 8.5
    card_h = 13.5 + len(margins) * row_h
    _ensure_pdf_space(pdf, card_h + 6)

    x0 = pdf.l_margin
    y0 = pdf.get_y() + 2.0

    # Card container
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_line_width(0.3)
    pdf.rect(x0, y0, card_w, card_h, style="DF")

    # Header bar
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(x0, y0, card_w, 9.0, style="F")
    pdf.set_draw_color(226, 232, 240)
    pdf.line(x0, y0 + 9.0, x0 + card_w, y0 + 9.0)

    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(15, 23, 42)
    pdf.set_xy(x0 + 3.5, y0 + 2.0)
    pdf.cell(160, 5, f"Profitability Margin Profile ({ticker})")

    bar_x = x0 + 42.0
    bar_max_w = 122.0
    colors = [(37, 99, 235), (8, 145, 178), (16, 185, 129)]

    max_scale = max(100.0, max(abs(m["value"]) for m in margins))

    for i, m in enumerate(margins):
        ry = y0 + 11.5 + i * row_h
        val = float(m["value"])
        lbl = str(m["label"])

        pdf.set_font("Helvetica", "B", 7.8)
        pdf.set_text_color(51, 65, 85)
        pdf.set_xy(x0 + 3.5, ry + 0.5)
        pdf.cell(37.0, 5.0, lbl)

        # Background track
        pdf.set_fill_color(241, 245, 249)
        pdf.rect(bar_x, ry + 1.0, bar_max_w, 4.2, style="F")

        # Value fill
        fill_w = min(bar_max_w, max(1.2, (abs(val) / max_scale) * bar_max_w))
        if val < 0:
            pdf.set_fill_color(239, 68, 68)
            pdf.set_text_color(220, 38, 38)
        else:
            r, g, b = colors[i % len(colors)]
            pdf.set_fill_color(r, g, b)
            pdf.set_text_color(15, 23, 42)
        pdf.rect(bar_x, ry + 1.0, fill_w, 4.2, style="F")

        # Percentage readout
        pdf.set_font("Helvetica", "B", 8.0)
        pdf.set_xy(bar_x + bar_max_w + 2.5, ry + 0.5)
        pdf.cell(21.0, 5.0, f"{val:.2f}%", align="R")

    pdf.set_line_width(0.2)
    pdf.set_y(y0 + card_h + 3.5)


def render_financial_charts_to_pdf(
    pdf: Any,
    chart_data: Optional[Dict[str, Any]],
    company_name: str,
    ticker: str
) -> int:
    """
    Render all available financial vector charts into the FPDF2 document cleanly in memory.
    Returns the number of charts rendered.
    """
    if not chart_data or not isinstance(chart_data, dict):
        return 0

    currency = chart_data.get("currency") or "USD"
    price_history = chart_data.get("price_history") or []
    price_summary = chart_data.get("price_summary") or {}
    annual_financials = chart_data.get("annual_financials") or []
    margins = chart_data.get("margins") or []

    has_any = len(price_history) >= 5 or len(annual_financials) >= 2 or len(margins) >= 1
    if not has_any:
        return 0

    pdf.sub_section_title("Visual Market Performance & Financial Charts")
    rendered = 0
    try:
        if len(price_history) >= 5:
            _draw_price_history_chart(pdf, price_history, price_summary, currency, company_name, ticker)
            rendered += 1
    except Exception:
        pass
    try:
        if len(annual_financials) >= 2:
            _draw_annual_financials_chart(pdf, annual_financials, currency, ticker)
            rendered += 1
    except Exception:
        pass
    try:
        if len(margins) >= 1:
            _draw_margins_chart(pdf, margins, ticker)
            rendered += 1
    except Exception:
        pass
    return rendered
