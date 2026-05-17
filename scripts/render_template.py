"""
MARKET MACHINE — render_template.py
template.html + data.json → index.html
디자인 변경 없이 숫자/텍스트 값만 교체
"""

import json
import re
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

KST = timezone(timedelta(hours=9))

# ─────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────
def safe(data, *keys, default="—"):
    v = data
    for k in keys:
        if not isinstance(v, dict):
            return default
        v = v.get(k)
        if v is None:
            return default
    return v

def fmt_price(v, decimals=0, prefix="", suffix=""):
    if v is None:
        return "—"
    try:
        v = float(v)
        if decimals == 0:
            return f"{prefix}{v:,.0f}{suffix}"
        return f"{prefix}{v:,.{decimals}f}{suffix}"
    except Exception:
        return str(v)

def fmt_chg(pct, decimals=2):
    """등락률 문자열 + CSS 클래스 반환"""
    if pct is None:
        return "→", "neutral"
    try:
        pct = float(pct)
        if pct >= 0:
            return f"▲ +{pct:.{decimals}f}%", "up"
        return f"▼ {pct:.{decimals}f}%", "dn"
    except Exception:
        return "→", "neutral"

def fmt_chg_simple(pct, decimals=2):
    if pct is None:
        return "—"
    try:
        pct = float(pct)
        if pct >= 0:
            return f"+{pct:.{decimals}f}%"
        return f"{pct:.{decimals}f}%"
    except Exception:
        return "—"

def mcap_fmt(v):
    if v is None:
        return "—"
    try:
        v = float(v)
        if v >= 1e12:
            return f"${v/1e12:.2f}T"
        if v >= 1e9:
            return f"${v/1e9:.1f}B"
        return f"${v:,.0f}"
    except Exception:
        return "—"

# ─────────────────────────────────────────────
# 클래스 기반 교체기
# ─────────────────────────────────────────────
class Renderer:
    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, "lxml")

    # ── P.01 스냅카드 ──────────────────────────
    def snap_card(self, field, price_str, chg_str, chg_cls):
        card = self.soup.find(attrs={"data-mcp-field": field})
        if not card:
            return
        val_div = card.find(class_="p01-snap-value")
        chg_div = card.find(class_="p01-snap-change")
        if val_div:
            val_div.string = price_str
        if chg_div:
            chg_div.string = chg_str
            chg_div["class"] = ["p01-snap-change", chg_cls]

    # ── P.01 data-mcp-field 텍스트 교체 ────────
    def mcp_text(self, field, text):
        el = self.soup.find(attrs={"data-mcp-field": field})
        if el:
            el.string = text

    # ── P.01 KPI 바 ─────────────────────────────
    def kpi_item(self, name, val_str, chg_str, chg_cls):
        for item in self.soup.find_all(class_="kpi-item"):
            n = item.find(class_="kpi-name")
            if n and n.get_text(strip=True) == name:
                v = item.find(class_="kpi-val")
                c = item.find(class_="kpi-chg")
                if v:
                    v.string = val_str
                if c:
                    c.string = chg_str
                    c["class"] = ["kpi-chg", chg_cls]
                return

    # ── P.02 지수 배지 ───────────────────────────
    def idx_badge(self, name, val_str, chg_str, chg_cls):
        for badge in self.soup.find_all(class_="idx-badge"):
            n = badge.find(class_="idx-name")
            if n and n.get_text(strip=True) == name:
                v = badge.find(class_="idx-val")
                c = badge.find(class_="idx-chg")
                if v:
                    v.string = val_str
                if c:
                    c.string = chg_str
                    c["class"] = ["idx-chg", chg_cls]
                return

    # ── P.02 종목 테이블 ─────────────────────────
    def stock_row_price(self, ticker_keyword, price_str, chg_str, chg_cls):
        """data-table tbody의 tr을 티커 키워드로 찾아 가격/등락 교체"""
        for tr in self.soup.select("table.data-table tbody tr"):
            first_td = tr.find("td")
            if first_td and ticker_keyword in first_td.get_text():
                tds = tr.find_all("td")
                if len(tds) >= 3:
                    tds[1].string = price_str
                    tds[2].string = chg_str
                    tds[2]["class"] = [chg_cls]
                return

    # ── P.05 oc-card ────────────────────────────
    def oc_card(self, label, val_str, sub_str=None):
        for card in self.soup.find_all(class_="oc-card"):
            lbl = card.find(class_="oc-label")
            if lbl and lbl.get_text(strip=True) == label:
                v = card.find(class_="oc-val")
                s = card.find(class_="oc-sub")
                if v:
                    v.string = val_str
                if s and sub_str:
                    s.string = sub_str
                return

    # ── P.05 공포탐욕 ────────────────────────────
    def fear_greed(self, score, label_ko, label_en, prev, prev_week):
        fg = self.soup.find(class_="fg-score")
        if fg:
            fg.string = str(score)
        lm = self.soup.find(class_="fg-label-main")
        if lm:
            lm.string = label_ko
        le = self.soup.find(class_="fg-label-en")
        if le:
            le.string = f"{label_en} · {score}/100"

        stats = self.soup.find_all(class_="fg-stat")
        for stat in stats:
            lbl = stat.find(class_="fg-stat-label")
            val = stat.find(class_="fg-stat-val")
            if not lbl or not val:
                continue
            lbl_txt = lbl.get_text(strip=True)
            if lbl_txt == "전일" and prev is not None:
                val.string = str(prev)
            elif lbl_txt == "전주" and prev_week is not None:
                val.string = str(prev_week)

    # ── P.05 TOP10 코인 테이블 ───────────────────
    def top10_coin(self, symbol, price_str, chg_str, chg_cls, mcap_str):
        for tr in self.soup.select("table.top10-table tbody tr"):
            tds = tr.find_all("td")
            if len(tds) >= 5:
                sym_td = tds[1].find("strong")
                if sym_td and sym_td.get_text(strip=True) == symbol:
                    tds[2].string = price_str
                    tds[3].string = chg_str
                    tds[3]["class"] = [chg_cls]
                    tds[4].string = mcap_str
                    return

    # ── P.08 매크로 지표 테이블 ─────────────────
    def macro_table_row(self, label, val_str, chg_str=None, chg_cls=None):
        for tr in self.soup.select("section#p08 table tbody tr"):
            tds = tr.find_all("td")
            if len(tds) >= 2:
                if label in tds[0].get_text():
                    tds[1].string = val_str
                    if chg_str and len(tds) >= 3 and chg_cls:
                        tds[2].string = chg_str
                        tds[2]["class"] = [chg_cls]
                    return

    # ── P.08 밸류에이션 카드 ────────────────────
    def val_card(self, name_keyword, current_str, bar_pct, bar_color):
        for card in self.soup.find_all(class_="val-card"):
            n = card.find(class_="val-name")
            if n and name_keyword in n.get_text():
                c = card.find(class_="val-current")
                if c:
                    c.string = current_str
                    c["style"] = f"color:{bar_color};"
                # 슬라이더 바
                fill = card.find(class_="val-slider-fill")
                marker = card.find(class_="val-slider-marker")
                if fill:
                    fill["style"] = (
                        f"width:{bar_pct}%;background:{bar_color};"
                        f"height:100%;border-radius:4px;"
                    )
                if marker:
                    marker["style"] = (
                        f"left:{bar_pct}%;background:{bar_color};"
                    )
                return

    # ── P.08 VIX 차트 현재값 레이블 ────────────
    def vix_label(self, val_str):
        # SVG 내 rect+text 레이블 교체 (정규식)
        # BeautifulSoup은 SVG 텍스트도 처리 가능
        for text_el in self.soup.select("section#p08 svg text"):
            if text_el.get_text(strip=True).replace(".","").replace(",","").isdigit():
                parent = text_el.parent
                # rect 레이블 바로 뒤 text 노드인지 확인
                if parent and parent.name == "g":
                    continue
                # 13.4 같은 VIX 값 패턴
                txt = text_el.get_text(strip=True)
                try:
                    v = float(txt)
                    if 5 <= v <= 80:  # VIX 범위
                        text_el.string = val_str
                        return
                except Exception:
                    pass

    # ── P.09 코인 감시 카드 ─────────────────────
    def cwl_card(self, symbol, price_str, chg_str, chg_cls):
        for card in self.soup.find_all(class_="cwl-card"):
            sym = card.find(class_="cwl-symbol")
            if sym and sym.get_text(strip=True) == symbol:
                p = card.find(class_="cwl-price")
                c = card.find(class_="cwl-chg")
                if p:
                    p.string = price_str
                if c:
                    c.string = chg_str
                    c["class"] = ["cwl-chg", chg_cls]
                return

    # ── P.04 워치리스트 테이블 ─────────────────
    def wl_row(self, ticker_keyword, price_str, chg_str, chg_cls):
        for tr in self.soup.select(".wl-panel table.data-table tbody tr"):
            first = tr.find("td")
            if first and ticker_keyword in first.get_text():
                tds = tr.find_all("td")
                if len(tds) >= 3:
                    tds[1].string = price_str
                    tds[2].string = chg_str
                    tds[2]["class"] = [chg_cls]
                return

    # ── 날짜 ────────────────────────────────────
    def update_dates(self, date_str):
        el = self.soup.find(id="navDate")
        if el:
            el.string = date_str
        for pid in ["p01","p02","p03","p04","p05","p06","p07","p08","p09","p10"]:
            el = self.soup.find(id=f"{pid}-date")
            if el:
                el.string = date_str
        el = self.soup.find(id="editor-date")
        if el:
            el.string = date_str[:10]
        el = self.soup.find(id="editor-date-top")
        if el:
            el.string = date_str

    def html(self):
        return str(self.soup)


# ─────────────────────────────────────────────
# 메인 렌더링
# ─────────────────────────────────────────────
def render(data):
    with open("template.html", "r", encoding="utf-8") as f:
        html = f.read()

    r = Renderer(html)

    # ── 날짜 ─────────────────────────────────────
    now = datetime.now(KST)
    days = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    date_str = now.strftime(f"%Y.%m.%d ({days[now.weekday()]})")
    r.update_dates(date_str)

    # ─────────────────────────────────────────────
    # P.01 스냅카드
    # ─────────────────────────────────────────────
    def snap(field, key, prefix="", decimals=0):
        price = safe(data, key, "price")
        pct   = safe(data, key, "chg_pct")
        r.snap_card(
            field,
            fmt_price(price, decimals, prefix),
            *fmt_chg(pct)
        )

    snap("snapshot.sp500",  "sp500",   decimals=0)
    snap("snapshot.nasdaq", "nasdaq",  decimals=0)
    snap("snapshot.btc",    "btc",     prefix="", decimals=0)
    snap("snapshot.usdkrw", "usdkrw",  decimals=2)

    # ─────────────────────────────────────────────
    # P.01 KPI 바
    # ─────────────────────────────────────────────
    def kpi(name, key, prefix="", decimals=0):
        price = safe(data, key, "price")
        pct   = safe(data, key, "chg_pct")
        chg_str, chg_cls = fmt_chg(pct)
        r.kpi_item(name, fmt_price(price, decimals, prefix), chg_str, chg_cls)

    kpi("KOSPI",    "kospi")
    kpi("KOSDAQ",   "kosdaq")
    kpi("S&P 500",  "sp500")
    kpi("NASDAQ",   "nasdaq")
    kpi("닛케이225","nikkei")
    kpi("USD/KRW",  "usdkrw",  decimals=1)
    kpi("USD/JPY",  "usdjpy",  decimals=1)
    kpi("WTI 유가", "wti",  prefix="$", decimals=1)
    kpi("GOLD",     "gold", prefix="$", decimals=0)

    # ─────────────────────────────────────────────
    # P.01 철강
    # ─────────────────────────────────────────────
    steel = data.get("steel", {})
    mcp_steel = r.soup.find(attrs={"data-mcp-field": "steel.price_table"})
    if mcp_steel:
        rows = mcp_steel.find_all(class_="p01-steel-row")
        if not rows:
            rows = mcp_steel.find_all("div", recursive=True)
        # steel.price_table 구조는 HTML 원본 유지, 값만 교체
        # 각 강종별 price 셀 탐색
        for div in mcp_steel.find_all("div"):
            txt = div.get_text(strip=True)
            for grade, key in [("SS400","ss400"),("20C","20c"),("45C","45c")]:
                if txt == grade:
                    # 다음 형제에서 price 찾기
                    sib = div.find_next_sibling()
                    while sib:
                        if sib.get_text(strip=True):
                            item = steel.get(key, {})
                            sib.string = item.get("price", "—")
                            break
                        sib = sib.find_next_sibling()

    # ─────────────────────────────────────────────
    # P.02 지수 배지
    # ─────────────────────────────────────────────
    def badge(name, key, prefix="", decimals=0):
        price = safe(data, key, "price")
        pct   = safe(data, key, "chg_pct")
        chg_str, chg_cls = fmt_chg(pct)
        r.idx_badge(name, fmt_price(price, decimals, prefix), chg_str, chg_cls)

    # Korea
    badge("KOSPI",       "kospi")
    badge("KOSDAQ",      "kosdaq")
    badge("원달러",      "usdkrw", decimals=1)
    # US
    badge("S&P 500",     "sp500")
    badge("NASDAQ",      "nasdaq")
    badge("DOW",         "dow")
    badge("10Y 국채",    "us10y", decimals=2)
    # Japan
    badge("닛케이225",   "nikkei")
    badge("TOPIX",       "topix")
    badge("USD/JPY",     "usdjpy", decimals=1)

    # ─────────────────────────────────────────────
    # P.02 종목 테이블 — 한국
    # ─────────────────────────────────────────────
    KR_STOCKS = [
        ("005930",  "kr_samsung",  "₩"),
        ("000660",  "kr_skhynix",  "₩"),
        ("005380",  "kr_hyundai",  "₩"),
        ("012450",  "kr_hanwha",   "₩"),
        ("373220",  "kr_lgenergy", "₩"),
        ("035720",  "kr_kakao",    "₩"),
        ("035420",  "kr_naver",    "₩"),
        ("068270",  "kr_celltrion","₩"),
        ("259960",  "kr_krafton",  "₩"),
        ("047810",  "kr_lignexone","₩"),
        ("005490",  "kr_posco",    "₩"),
    ]
    for ticker_kw, key, pfx in KR_STOCKS:
        price = safe(data, key, "price")
        pct   = safe(data, key, "chg_pct")
        chg_str, chg_cls = fmt_chg(pct)
        if price:
            price_str = f"{pfx}{price:,.0f}"
        else:
            price_str = "—"
        r.stock_row_price(ticker_kw, price_str, chg_str, chg_cls)

    # P.02 종목 테이블 — 미국
    US_STOCKS = [
        ("NVDA", "us_nvda",  "$"),
        ("AAPL", "us_aapl",  "$"),
        ("TSLA", "us_tsla",  "$"),
        ("META", "us_meta",  "$"),
        ("MSFT", "us_msft",  "$"),
        ("AMZN", "us_amzn",  "$"),
        ("MSTR", "us_mstr",  "$"),
        ("PLTR", "us_pltr",  "$"),
        ("COIN", "us_coin",  "$"),
    ]
    for ticker_kw, key, pfx in US_STOCKS:
        price = safe(data, key, "price")
        pct   = safe(data, key, "chg_pct")
        chg_str, chg_cls = fmt_chg(pct)
        price_str = fmt_price(price, 2, pfx) if price else "—"
        r.stock_row_price(ticker_kw, price_str, chg_str, chg_cls)

    # P.02 종목 테이블 — 일본
    JP_STOCKS = [
        ("9984", "jp_softbank", "¥"),
        ("7203", "jp_toyota",   "¥"),
        ("6758", "jp_sony",     "¥"),
        ("6861", "jp_keyence",  "¥"),
        ("8306", "jp_mufg",     "¥"),
        ("6367", "jp_daikin",   "¥"),
    ]
    for ticker_kw, key, pfx in JP_STOCKS:
        price = safe(data, key, "price")
        pct   = safe(data, key, "chg_pct")
        chg_str, chg_cls = fmt_chg(pct)
        if price:
            price_str = f"{pfx}{price:,.0f}"
        else:
            price_str = "—"
        r.stock_row_price(ticker_kw, price_str, chg_str, chg_cls)

    # ─────────────────────────────────────────────
    # P.04 워치리스트
    # ─────────────────────────────────────────────
    for ticker_kw, key, pfx in KR_STOCKS:
        price = safe(data, key, "price")
        pct   = safe(data, key, "chg_pct")
        chg_str, chg_cls = fmt_chg(pct)
        price_str = f"{pfx}{price:,.0f}" if price else "—"
        r.wl_row(ticker_kw, price_str, chg_str, chg_cls)

    for ticker_kw, key, pfx in US_STOCKS:
        price = safe(data, key, "price")
        pct   = safe(data, key, "chg_pct")
        chg_str, chg_cls = fmt_chg(pct)
        price_str = fmt_price(price, 2, pfx) if price else "—"
        r.wl_row(ticker_kw, price_str, chg_str, chg_cls)

    for ticker_kw, key, pfx in JP_STOCKS:
        price = safe(data, key, "price")
        pct   = safe(data, key, "chg_pct")
        chg_str, chg_cls = fmt_chg(pct)
        price_str = f"{pfx}{price:,.0f}" if price else "—"
        r.wl_row(ticker_kw, price_str, chg_str, chg_cls)

    # ─────────────────────────────────────────────
    # P.05 공포탐욕
    # ─────────────────────────────────────────────
    fg = data.get("fg_today", {})
    fg_prev = data.get("fg_yesterday", {})
    fg_week = data.get("fg_last_week", {})
    if fg:
        r.fear_greed(
            fg.get("score", 50),
            fg.get("label_ko", "중립"),
            fg.get("label_en", "Neutral"),
            fg_prev.get("score") if fg_prev else None,
            fg_week.get("score") if fg_week else None,
        )

    # P.05 OC 카드
    cg_global = data.get("cg_global", {})
    btc_dom = cg_global.get("btc_dominance")
    total_mcap = cg_global.get("total_mcap_usd")
    total_mcap_chg = cg_global.get("total_mcap_chg")

    r.oc_card(
        "BTC 도미넌스",
        f"{btc_dom:.1f}%" if btc_dom else "—",
        "알트 상승 주의" if btc_dom and btc_dom > 55 else "알트 동반 강세"
    )
    r.oc_card(
        "전체 시총",
        mcap_fmt(total_mcap),
        f"▲ +{total_mcap_chg:.1f}%" if total_mcap_chg and total_mcap_chg >= 0
        else f"▼ {total_mcap_chg:.1f}%" if total_mcap_chg else "—"
    )

    # P.05 TOP10 코인 테이블
    TOP10 = [
        ("BTC",  "cg_btc"),
        ("ETH",  "cg_eth"),
        ("BNB",  "cg_bnb"),
        ("XRP",  "cg_xrp"),
        ("SOL",  "cg_sol"),
        ("ADA",  "cg_ada"),
        ("DOGE", "cg_doge"),
        ("AVAX", "cg_avax"),
        ("DOT",  "cg_dot"),
        ("MATIC","cg_matic"),
    ]
    for sym, key in TOP10:
        d = data.get(key, {})
        price = d.get("price")
        pct   = d.get("chg_pct")
        mcap  = d.get("mcap")
        price_str = fmt_price(price, 2, "$") if price else "—"
        chg_str   = fmt_chg_simple(pct)
        chg_cls   = "up" if (pct or 0) >= 0 else "dn"
        r.top10_coin(sym, price_str, chg_str, chg_cls, mcap_fmt(mcap))

    # ─────────────────────────────────────────────
    # P.08 매크로
    # ─────────────────────────────────────────────
    def m_row(label, key, prefix="", suffix="", decimals=2):
        price = safe(data, key, "price")
        pct   = safe(data, key, "chg_pct")
        chg_str, chg_cls = fmt_chg(pct)
        r.macro_table_row(label, fmt_price(price, decimals, prefix, suffix),
                          chg_str, chg_cls)

    m_row("Fed Fund Rate",  "us10y",  suffix="%", decimals=2)
    m_row("미 10년물 국채", "us10y",  suffix="%", decimals=2)
    m_row("한국 기준금리",  "usdkrw", decimals=1)
    m_row("USD/KRW",        "usdkrw", decimals=2)
    m_row("USD/JPY",        "usdjpy", decimals=1)
    m_row("EUR/USD",        "eurusd", decimals=4)
    m_row("DXY 달러지수",   "dxy",    decimals=1)
    m_row("VIX 공포지수",   "vix",    decimals=1)
    m_row("금 (Gold)",      "gold",   prefix="$", decimals=0)
    m_row("WTI 유가",       "wti",    prefix="$", decimals=1)
    m_row("브렌트유",       "brent",  prefix="$", decimals=1)
    m_row("구리 (Copper)",  "copper", prefix="$", decimals=2)
    m_row("천연가스",       "natgas", prefix="$", decimals=2)

    # VIX 차트 레이블
    vix_price = safe(data, "vix", "price")
    if vix_price:
        r.vix_label(f"{float(vix_price):.1f}")

    # ─────────────────────────────────────────────
    # P.08 밸류에이션 카드
    # ─────────────────────────────────────────────
    # S&P500 P/E 기준 고평가/저평가 판단
    VAL_DATA = [
        ("S&P 500 P/E",    "22.4x", 75, "#E63329"),
        ("S&P 500 P/B",    "4.6x",  85, "#E63329"),
        ("NASDAQ P/E",     "31.2x", 80, "#E63329"),
        ("Shiller CAPE",   "34.8x", 88, "#E63329"),
        ("KOSPI P/E",      "10.8x", 30, "#43A047"),
        ("KOSPI P/B",      "0.92x", 35, "#43A047"),
        ("KOSDAQ P/E",     "38.4x", 60, "#E63329"),
        ("닛케이 P/E",     "16.2x", 52, "#888888"),
    ]
    for name, val_str, bar_pct, color in VAL_DATA:
        r.val_card(name, val_str, bar_pct, color)

    # ─────────────────────────────────────────────
    # P.09 코인 감시 카드
    # ─────────────────────────────────────────────
    COIN_WL = [
        ("BTC",  "cg_btc"),
        ("ETH",  "cg_eth"),
        ("BNB",  "cg_bnb"),
        ("XRP",  "cg_xrp"),
        ("SOL",  "cg_sol"),
        ("ADA",  "cg_ada"),
        ("AVAX", "cg_avax"),
        ("DOT",  "cg_dot"),
        ("LINK", None),
        ("ARB",  "cg_arb"),
        ("OP",   None),
        ("UNI",  "cg_uni"),
        ("AAVE", "cg_aave"),
        ("SUI",  "cg_sui"),
        ("TAO",  "cg_tao"),
    ]
    for sym, key in COIN_WL:
        if not key:
            continue
        d = data.get(key, {})
        price = d.get("price")
        pct   = d.get("chg_pct")
        price_str = fmt_price(price, 2, "$") if price and float(price) >= 1 else \
                    (f"${price:.6f}" if price else "—")
        chg_str   = fmt_chg_simple(pct)
        chg_cls   = "up" if (pct or 0) >= 0 else "dn"
        chg_arrow = f"▲ {chg_str}" if (pct or 0) >= 0 else f"▼ {chg_str}"
        r.cwl_card(sym, price_str, chg_arrow, chg_cls)

    return r.html()


# ─────────────────────────────────────────────
def main():
    print("=== render_template.py 시작 ===")
    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    html = render(data)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[완료] index.html 생성 ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
