"""
MARKET MACHINE — fetch_data.py
무료 데이터 소스에서 P.01~P.10 전체 데이터 수집 → data.json 저장
"""

import json
import os
import requests
import time
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

# ─────────────────────────────────────────────
# 1. yfinance 수집
# ─────────────────────────────────────────────
def fetch_yf():
    import yfinance as yf

    TICKERS = {
        # 지수
        "^GSPC":   "sp500",
        "^IXIC":   "nasdaq",
        "^DJI":    "dow",
        "^KS11":   "kospi",
        "^KQ11":   "kosdaq",
        "^N225":   "nikkei",
        "^TOPX":   "topix",
        "^VIX":    "vix",
        # 환율
        "KRW=X":   "usdkrw",
        "JPY=X":   "usdjpy",
        "EURUSD=X":"eurusd",
        "DX-Y.NYB":"dxy",
        # 원자재
        "GC=F":    "gold",
        "CL=F":    "wti",
        "BZ=F":    "brent",
        "HG=F":    "copper",
        "NG=F":    "natgas",
        "ALI=F":   "aluminum",
        # 채권
        "^TNX":    "us10y",
        # 한국 주식
        "005930.KS": "kr_samsung",
        "000660.KS": "kr_skhynix",
        "005380.KS": "kr_hyundai",
        "012450.KS": "kr_hanwha",
        "373220.KS": "kr_lgenergy",
        "035720.KS": "kr_kakao",
        "035420.KS": "kr_naver",
        "068270.KS": "kr_celltrion",
        "259960.KS": "kr_krafton",
        "047810.KS": "kr_lignexone",
        "005490.KS": "kr_posco",
        # 미국 주식
        "NVDA":  "us_nvda",
        "AAPL":  "us_aapl",
        "TSLA":  "us_tsla",
        "META":  "us_meta",
        "MSFT":  "us_msft",
        "AMZN":  "us_amzn",
        "MSTR":  "us_mstr",
        "PLTR":  "us_pltr",
        "COIN":  "us_coin",
        # 일본 주식
        "9984.T": "jp_softbank",
        "7203.T": "jp_toyota",
        "6758.T": "jp_sony",
        "6861.T": "jp_keyence",
        "8306.T": "jp_mufg",
        "6367.T": "jp_daikin",
        # 코인
        "BTC-USD":  "btc",
        "ETH-USD":  "eth",
        "BNB-USD":  "bnb",
        "XRP-USD":  "xrp",
        "SOL-USD":  "sol",
        "ADA-USD":  "ada",
        "AVAX-USD": "avax",
        "DOGE-USD": "doge",
        "DOT-USD":  "dot",
        "MATIC-USD":"matic",
    }

    result = {}
    tickers_str = " ".join(TICKERS.keys())
    print(f"[yfinance] {len(TICKERS)}개 티커 일괄 수집...")

    try:
        data = yf.download(tickers_str, period="2d", interval="1d",
                           group_by="ticker", auto_adjust=True, progress=False)
    except Exception as e:
        print(f"[yfinance ERROR] {e}")
        return result

    for ticker, key in TICKERS.items():
        try:
            if len(TICKERS) == 1:
                df = data
            else:
                df = data[ticker]

            if df.empty or len(df) < 1:
                print(f"[WARN] {ticker}: 데이터 없음")
                result[key] = {"price": None, "prev": None, "chg": None, "chg_pct": None}
                continue

            latest = df.iloc[-1]
            prev   = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]

            price    = float(latest["Close"])
            prev_p   = float(prev["Close"])
            chg      = price - prev_p
            chg_pct  = (chg / prev_p * 100) if prev_p else 0

            result[key] = {
                "price":   round(price, 4),
                "prev":    round(prev_p, 4),
                "chg":     round(chg, 4),
                "chg_pct": round(chg_pct, 2),
            }
            print(f"  {key:20s} {price:>12.2f}  ({chg_pct:+.2f}%)")

        except Exception as e:
            print(f"[WARN] {ticker} ({key}): {e}")
            result[key] = {"price": None, "prev": None, "chg": None, "chg_pct": None}

    return result


# ─────────────────────────────────────────────
# 2. CoinGecko 무료 API
# ─────────────────────────────────────────────
COINGECKO_IDS = [
    "bitcoin","ethereum","binancecoin","ripple","solana",
    "cardano","dogecoin","avalanche-2","polkadot","matic-network",
    "sui","bittensor","arbitrum","uniswap","aave",
]

def fetch_coingecko():
    result = {}
    try:
        ids_str = ",".join(COINGECKO_IDS)
        url = (
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={ids_str}"
            f"&vs_currencies=usd"
            f"&include_24hr_change=true"
            f"&include_market_cap=true"
        )
        r = requests.get(url, timeout=15,
                         headers={"User-Agent": "MarketMachine/1.0"})
        r.raise_for_status()
        d = r.json()

        ID_MAP = {
            "bitcoin":       "cg_btc",
            "ethereum":      "cg_eth",
            "binancecoin":   "cg_bnb",
            "ripple":        "cg_xrp",
            "solana":        "cg_sol",
            "cardano":       "cg_ada",
            "dogecoin":      "cg_doge",
            "avalanche-2":   "cg_avax",
            "polkadot":      "cg_dot",
            "matic-network": "cg_matic",
            "sui":           "cg_sui",
            "bittensor":     "cg_tao",
            "arbitrum":      "cg_arb",
            "uniswap":       "cg_uni",
            "aave":          "cg_aave",
        }
        for cg_id, key in ID_MAP.items():
            if cg_id in d:
                result[key] = {
                    "price":   d[cg_id].get("usd"),
                    "chg_pct": d[cg_id].get("usd_24h_change"),
                    "mcap":    d[cg_id].get("usd_market_cap"),
                }

        # Global market data
        g = requests.get(
            "https://api.coingecko.com/api/v3/global",
            timeout=15, headers={"User-Agent": "MarketMachine/1.0"}
        ).json().get("data", {})
        result["cg_global"] = {
            "total_mcap_usd":   g.get("total_market_cap", {}).get("usd"),
            "total_mcap_chg":   g.get("market_cap_change_percentage_24h_usd"),
            "btc_dominance":    g.get("market_cap_percentage", {}).get("btc"),
        }
        print(f"[CoinGecko] 수집 완료 — {len(result)}개 항목")

    except Exception as e:
        print(f"[CoinGecko ERROR] {e}")

    return result


# ─────────────────────────────────────────────
# 3. 공포탐욕지수 (alternative.me)
# ─────────────────────────────────────────────
def fetch_fear_greed():
    try:
        r = requests.get(
            "https://api.alternative.me/fng/?limit=7",
            timeout=10, headers={"User-Agent": "MarketMachine/1.0"}
        )
        r.raise_for_status()
        items = r.json().get("data", [])
        if not items:
            return {}

        LABELS_KO = {
            "Extreme Fear": "극도 공포",
            "Fear": "공포",
            "Neutral": "중립",
            "Greed": "탐욕",
            "Extreme Greed": "극도 탐욕",
        }

        def parse(item):
            score = int(item["value"])
            label_en = item["value_classification"]
            label_ko = LABELS_KO.get(label_en, label_en)
            return {"score": score, "label_ko": label_ko, "label_en": label_en}

        result = {
            "fg_today":    parse(items[0]),
            "fg_yesterday": parse(items[1]) if len(items) > 1 else None,
            "fg_last_week": parse(items[6]) if len(items) > 6 else None,
        }
        print(f"[FearGreed] 오늘: {result['fg_today']['score']} ({result['fg_today']['label_ko']})")
        return result

    except Exception as e:
        print(f"[FearGreed ERROR] {e}")
        return {}


# ─────────────────────────────────────────────
# 4. 철강 (Google Sheets CSV)
# ─────────────────────────────────────────────
STEEL_SHEET_URL = os.environ.get(
    "STEEL_SHEET_URL",
    ""  # GitHub Secret으로 주입: STEEL_SHEET_URL
)

def fetch_steel():
    if not STEEL_SHEET_URL:
        print("[Steel] STEEL_SHEET_URL 미설정 — fallback 사용")
        return {
            "ss400": {"price": "—", "chg": "→", "chg_cls": "neutral"},
            "20c":   {"price": "—", "chg": "→", "chg_cls": "neutral"},
            "45c":   {"price": "—", "chg": "→", "chg_cls": "neutral"},
        }

    try:
        import csv
        import io
        r = requests.get(STEEL_SHEET_URL, timeout=10)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        result = {}
        for row in reader:
            item = row.get("item", "").strip().upper()
            price = row.get("price", "—").strip()
            chg   = row.get("change", "→").strip()
            chg_cls = "up" if "+" in chg else ("dn" if "-" in chg else "neutral")
            result[item.lower().replace("-","_").replace(" ","_")] = {
                "price": price, "chg": chg, "chg_cls": chg_cls
            }
        print(f"[Steel] 수집 완료: {list(result.keys())}")
        return result

    except Exception as e:
        print(f"[Steel ERROR] {e}")
        return {
            "ss400": {"price": "—", "chg": "→", "chg_cls": "neutral"},
            "20c":   {"price": "—", "chg": "→", "chg_cls": "neutral"},
            "45c":   {"price": "—", "chg": "→", "chg_cls": "neutral"},
        }


# ─────────────────────────────────────────────
# 5. 메인
# ─────────────────────────────────────────────
def main():
    now = datetime.now(KST)
    print(f"\n{'='*50}")
    print(f"MARKET MACHINE 데이터 수집 — {now.strftime('%Y.%m.%d %H:%M KST')}")
    print(f"{'='*50}")

    data = {
        "meta": {
            "updated_at": now.isoformat(),
            "date_str":   now.strftime("%Y.%m.%d"),
            "weekday":    ["MON","TUE","WED","THU","FRI","SAT","SUN"][now.weekday()],
        }
    }

    # yfinance
    yf_data = fetch_yf()
    data.update(yf_data)

    # CoinGecko
    time.sleep(2)
    cg_data = fetch_coingecko()
    data.update(cg_data)

    # Fear & Greed
    time.sleep(1)
    fg_data = fetch_fear_greed()
    data.update(fg_data)

    # Steel
    steel_data = fetch_steel()
    data["steel"] = steel_data

    # 저장
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[완료] data.json 저장 — {len(data)}개 키")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
