"""A4 invoice PDF (Arabic RTL / English LTR) rendered from the document built by invoice_doc.build_document.

Fully offline: the Cairo font is bundled (app/assets/fonts), Arabic letters are shaped locally (arabic-reshaper + python-bidi),
the QR code is drawn by reportlab. No external service or hosted font is used."""
import io
import re
import unicodedata
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, Image, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas as rl_canvas

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
BRAND = colors.HexColor("#14306f")
SOFT = colors.HexColor("#e3ecff")
GRID = colors.HexColor("#cbd5e1")
AR = re.compile("[؀-ۿݐ-ݿ]")
_ready = False
_shaper = arabic_reshaper.ArabicReshaper({"delete_harakat": True, "support_ligatures": True})


def _fonts() -> None:
    global _ready
    if not _ready:
        pdfmetrics.registerFont(TTFont("Cairo", str(FONT_DIR / "Cairo-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Cairo-Bold", str(FONT_DIR / "Cairo-Bold.ttf")))
        pdfmetrics.registerFontFamily("Cairo", normal="Cairo", bold="Cairo-Bold", italic="Cairo", boldItalic="Cairo-Bold")
        _ready = True


def _use_base_letters(text: str) -> str:
    """The bundled Cairo draws some isolated letter forms (alef, teh marbuta, reh, waw...) from the plain letter, not from the
    'Arabic presentation form' code point the shaper emits; swap those so no letter ever renders as an empty box."""
    _fonts()
    have = pdfmetrics.getFont("Cairo").face.charToGlyph
    out = []
    for ch in text:
        if 0xFB50 <= ord(ch) <= 0xFEFC and ord(ch) not in have:
            dec = unicodedata.decomposition(ch).split()
            if len(dec) == 2 and dec[0].startswith("<"):
                ch = chr(int(dec[1], 16))
        out.append(ch)
    return "".join(out)


def shape(text, rtl: bool) -> str:
    """Arabic needs letter joining + visual reordering because the PDF writes glyphs left to right."""
    text = "" if text is None else str(text)
    if AR.search(text):
        return _use_base_letters(get_display(_shaper.reshape(text), base_dir="R" if rtl else "L"))
    return text


def fmt(amount, currency: str) -> str:
    return f"{Decimal(str(amount)):,.2f} {currency}"


class _Numbered(rl_canvas.Canvas):
    """Two-pass canvas so every page can say 'Page x of y'."""

    def __init__(self, *a, footer=None, **kw):
        super().__init__(*a, **kw)
        self._saved, self._footer = [], footer

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            if self._footer:
                self._footer(self, self._pageNumber, total)
            super().showPage()
        super().save()


def render_pdf(doc: dict, logo: Path | None = None) -> bytes:
    _fonts()
    rtl, L, cur = doc["rtl"], doc["labels"], doc["invoice"]["currency"]
    align = TA_RIGHT if rtl else TA_LEFT
    S = lambda size=10, bold=False, al=None, color=colors.black, lead=None: ParagraphStyle(  # noqa: E731
        "s", fontName="Cairo-Bold" if bold else "Cairo", fontSize=size, leading=lead or size * 1.45, alignment=al if al is not None else align, textColor=color)

    def P(text, **kw):
        return Paragraph(escape(shape(text, rtl)), S(**kw))

    def order(row):  # RTL documents mirror the column order
        return list(reversed(row)) if rtl else row

    story = []
    ws, inv = doc["workshop"], doc["invoice"]

    # --- letterhead ---------------------------------------------------------------
    head_left = [P(ws["name"], size=17, bold=True, color=BRAND)]
    for line in (ws["address"], " · ".join(x for x in (ws["phone"], ws["email"]) if x), f'{L["tax_no"]}: {ws["tax_number"]}' if ws["tax_number"] else ""):
        if line:
            head_left.append(P(line, size=9, color=colors.HexColor("#475569")))
    cells = [head_left]
    widths = [None]
    if logo and logo.is_file():
        try:
            img = Image(str(logo))
            ratio = min(22 * mm / img.imageWidth, 22 * mm / img.imageHeight)
            img.drawWidth, img.drawHeight = img.imageWidth * ratio, img.imageHeight * ratio
            cells.append(img)
            widths.append(26 * mm)
        except Exception:  # noqa: BLE001 - an unreadable logo must never block printing an invoice
            pass
    row = order(cells)
    cw = order(widths)
    head = Table([row], colWidths=[(170 * mm - sum(w for w in cw if w)) if w is None else w for w in cw])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 1.5, BRAND), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                              ("ALIGN", (0, 0), (-1, -1), "RIGHT" if rtl else "LEFT")]))
    story += [head, Spacer(1, 6 * mm)]

    # --- title + meta + QR -----------------------------------------------------------
    note = L["detailed_note"] if doc["mode"] == "detailed" else L["summary_note"]
    flag = L["draft"] if inv["status"] == "draft" else L["cancelled"] if inv["status"] == "cancelled" else ""
    meta = [P(f'{L["title"]}  {inv["number"]}', size=15, bold=True), P(note, size=9, color=colors.HexColor("#64748b"))]
    if flag:
        meta.append(P(flag, size=13, bold=True, color=colors.HexColor("#b91c1c")))
    meta += [P(f'{L["date"]}: {inv["date"] or "—"}', size=10), P(f'{L["job"]}: {inv["job_no"]}', size=10)]
    block = [meta]
    bw = [None]
    if doc.get("qr"):
        d = Drawing(26 * mm, 26 * mm)
        q = QrCodeWidget(doc["qr"])
        b = q.getBounds()
        d.add(q)
        d.scale(26 * mm / (b[2] - b[0]), 26 * mm / (b[3] - b[1]))
        d.width = d.height = 26 * mm
        block.append(d)
        bw.append(30 * mm)
    t = Table([order(block)], colWidths=[(170 * mm - sum(w for w in order(bw) if w)) if w is None else w for w in order(bw)])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [t, Spacer(1, 4 * mm)]

    # --- customer / vehicle ----------------------------------------------------------
    c, v, vis = doc["customer"], doc["vehicle"], doc["visit"]
    cust = [P(L["customer"], size=9, bold=True, color=BRAND), P(c["name"], size=11, bold=True), P(f'{L["mobile"]}: {c["mobile"]}', size=9)]
    veh = [P(L["vehicle"], size=9, bold=True, color=BRAND), P(f'{v["make"]} {v["model"]}', size=11, bold=True),
           P(f'{L["plate"]}: {v["plate"] or "—"}', size=9)]
    if v.get("vin"):
        veh.append(P(f'{L["vin"]}: {v["vin"]}', size=9))
    if v.get("mileage") is not None:
        veh.append(P(f'{L["mileage"]}: {v["mileage"]:,} {L["km"]}', size=9))
    if vis.get("completed_at"):
        veh.append(P(f'{L["completed"]}: {vis["completed_at"]}', size=9))
    if vis.get("delivered_at"):
        veh.append(P(f'{L["delivered"]}: {vis["delivered_at"]}', size=9))
    box = Table([order([cust, veh])], colWidths=[85 * mm, 85 * mm])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, GRID), ("INNERGRID", (0, 0), (-1, -1), 0.7, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [box, Spacer(1, 5 * mm)]

    # --- charges -----------------------------------------------------------------
    num = lambda text, bold=False: P(text, size=9, bold=bold, al=TA_LEFT)  # noqa: E731 - figures always read left-to-right
    if doc["mode"] == "detailed":
        hdr = [L["desc"], L["part_no"], L["qty"], L["unit"], L["total"]]
        data = [order([P(h, size=9, bold=True, color=colors.white, al=TA_CENTER) for h in hdr])]
        spans, subheads = [], []
        for kind, title in (("part", L["parts"]), ("labor", L["labor"]), ("other", L["other"])):
            group = [x for x in doc["lines"] if x["kind"] == kind]
            if not group:
                continue
            data.append([P(title, size=9, bold=True, color=BRAND)] + [""] * 4)
            subheads.append(len(data) - 1)
            for x in group:
                qty = x["quantity"].rstrip("0").rstrip(".") if "." in x["quantity"] else x["quantity"]
                unit = fmt(x["rate"] or x["unit_price"], cur)
                desc = x["description"] + (f' ({qty} {L["hours"]})' if x["kind"] == "labor" and x["hours"] else "")
                data.append(order([P(desc, size=9), P(x["part_number"] or "", size=9, al=TA_CENTER), num(qty), num(unit), num(fmt(x["amount"], cur))]))
        widths = [68 * mm, 28 * mm, 16 * mm, 30 * mm, 28 * mm]
        tbl = Table(data, colWidths=order(widths), repeatRows=1, splitByRow=1)
        style = [("BACKGROUND", (0, 0), (-1, 0), BRAND), ("GRID", (0, 0), (-1, -1), 0.5, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                 ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
        for r in subheads:
            style += [("SPAN", (0, r), (-1, r)), ("BACKGROUND", (0, r), (-1, r), SOFT)]
        tbl.setStyle(TableStyle(style))
        story += [tbl, Spacer(1, 5 * mm)]
    else:
        g = doc["groups"]
        rows = [[P(L["parts"], size=10), num(fmt(g["parts"], cur))], [P(L["labor"], size=10), num(fmt(g["labor"], cur))]]
        if True:  # the brief lists "total additional charges" even when it is zero
            rows.append([P(L["other"], size=10), num(fmt(g["other"], cur))])
        tbl = Table([order(r) for r in rows], colWidths=order([110 * mm, 60 * mm]))
        tbl.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, GRID), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story += [tbl, Spacer(1, 5 * mm)]

    # --- totals ------------------------------------------------------------------
    T = doc["totals"]
    rows = [(L["subtotal"], T["subtotal"], False)]
    if Decimal(T["discount"]):
        rows.append((L["discount"], "-" + T["discount"], False))
    if Decimal(T["tax_amount"]) or Decimal(T["tax_rate"]):
        rows.append((f'{L["tax"]} ({Decimal(T["tax_rate"]):g}%)', T["tax_amount"], False))
    rows.append((L["grand_total"], T["total"], True))
    if Decimal(T["credit_total"]):
        rows.append((L["credit"], "-" + T["credit_total"], False))
    rows.append((L["paid"], T["paid"], False))
    if Decimal(T["refunded"]):
        rows.append((L["refunded"], T["refunded"], False))
    rows.append((L["outstanding"], T["outstanding"], True))
    tot = Table([order([P(lbl, size=10, bold=b), num(fmt(val, cur) if not val.startswith("-") else "-" + fmt(val[1:], cur), bold=b)]) for lbl, val, b in rows],
                colWidths=order([60 * mm, 40 * mm]), hAlign="RIGHT" if rtl else "LEFT")
    ts = [("LINEBELOW", (0, 0), (-1, -1), 0.4, GRID), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    for i, (_, _, b) in enumerate(rows):
        if b:
            ts.append(("BACKGROUND", (0, i), (-1, i), SOFT))
    tot.setStyle(TableStyle(ts))
    flow = [tot]
    if doc["payments"]:
        flow += [Spacer(1, 4 * mm), P(L["payments"], size=10, bold=True, color=BRAND)]
        prow = [order([P(x["date"] or "", size=9, al=TA_LEFT), P(x["method"], size=9), num(fmt(x["amount"], cur))]) for x in doc["payments"]]
        pt = Table(prow, colWidths=order([32 * mm, 70 * mm, 40 * mm]), hAlign="RIGHT" if rtl else "LEFT")
        pt.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, GRID)]))
        flow.append(pt)
    story.append(KeepTogether(flow))
    story += [Spacer(1, 8 * mm), P(L["thanks"], size=9, al=TA_CENTER, color=colors.HexColor("#64748b"))]

    # --- page furniture ----------------------------------------------------------------
    def footer(cv, page, total):
        cv.saveState()
        cv.setFont("Cairo", 8)
        cv.setFillColor(colors.HexColor("#64748b"))
        left = f'{inv["number"]}  ·  {ws["name"]}'
        right = f'{L["page"]} {page} {L["of"]} {total}'
        if rtl:
            cv.drawRightString(A4[0] - 20 * mm, 10 * mm, shape(left, True))
            cv.drawString(20 * mm, 10 * mm, shape(right, True))
        else:
            cv.drawString(20 * mm, 10 * mm, shape(left, False))
            cv.drawRightString(A4[0] - 20 * mm, 10 * mm, shape(right, False))
        cv.setStrokeColor(GRID)
        cv.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
        cv.restoreState()

    def later_header(cv, _):
        cv.saveState()
        cv.setFont("Cairo-Bold", 9)
        cv.setFillColor(BRAND)
        text = shape(f'{ws["name"]} — {L["title"]} {inv["number"]}', rtl)
        (cv.drawRightString if rtl else cv.drawString)(A4[0] - 20 * mm if rtl else 20 * mm, A4[1] - 12 * mm, text)
        cv.restoreState()

    buf = io.BytesIO()
    d = BaseDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=15 * mm, bottomMargin=20 * mm,
                        title=f'{L["title"]} {inv["number"]}', author=ws["name"], creator="AutoCare Pro")
    first = Frame(d.leftMargin, d.bottomMargin, d.width, d.height, id="first", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    later = Frame(d.leftMargin, d.bottomMargin, d.width, d.height - 8 * mm, id="later", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    d.addPageTemplates([PageTemplate(id="first", frames=[first]), PageTemplate(id="later", frames=[later], onPage=later_header)])
    from reportlab.platypus import NextPageTemplate
    story.insert(0, NextPageTemplate("later"))
    d.build(story, canvasmaker=lambda *a, **kw: _Numbered(*a, footer=footer, **kw))
    return buf.getvalue()
