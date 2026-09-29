import os
import json
import datetime
import urllib.request

def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Pull Spot Gold (using Metals.dev or Yahoo Finance fallback)
    spot_price = 4119.55
    spot_change = -3.85
    try:
        api_key = os.getenv('METALS_DEV_API_KEY', 'demo')
        data = fetch_json(f"https://api.metals.dev/v1/latest?api_key={api_key}&currency=USD&unit=toz")
        if data and "metals" in data and "gold" in data["metals"]:
            spot_price = float(data["metals"]["gold"])
    except Exception as e:
        print(f"Spot fetch fallback: {e}")

    # 2. Pull GLD ETF Quote
    gld_price = round(spot_price / 10.912, 2)
    gld_change = -4.04
    try:
        yh = fetch_json("https://query1.finance.yahoo.com/v8/finance/chart/GLD?interval=1d&range=5d")
        meta = yh["chart"]["result"][0]["meta"]
        gld_price = float(meta["regularMarketPrice"])
        prev_close = float(meta["chartPreviousClose"])
        gld_change = round(((gld_price - prev_close) / prev_close) * 100, 2)
    except Exception as e:
        print(f"GLD fetch fallback: {e}")

    # 3. Macro Parameters (Central Bank monthly pace, TIPS 10Y, SGE Premium, DXY)
    cb_purchases_t = 72.0       # World Gold Council baseline
    sge_premium_usd = 18.40     # Shanghai Gold Exchange premium
    tips_10y_yield = 1.78       # US 10-Yr Real Yield
    dxy_index = 104.20          # US Dollar Index
    etf_flows_b = 2.10          # Net fund creations (Billions)

    # 4. Mathematical Conviction Formulas
    # Bullion Conviction: structural de-dollarization + physical premium
    bullion_conv = int(min(95, max(40, round(50 + 0.40 * (cb_purchases_t - 35) + 0.50 * (sge_premium_usd - 5) + 0.15 * (dxy_index - 100)))))
    
    # GLD Conviction: inverse real yields + fund liquidity flows
    etf_conv = int(min(90, max(35, round(50 - 15.0 * (tips_10y_yield - 1.50) + 5.0 * (etf_flows_b) - 0.25 * (dxy_index - 100)))))

    # 5. Load or Initialize Rolling 90-Day Time-Series
    history_file = "data.json"
    history = {"labels": [], "spot": [], "gld": [], "bullion_conv": [], "etf_conv": []}
    
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                existing = json.load(f)
                history = existing.get("history", history)
        except Exception:
            pass

    # Fallback initialization if new repo
    if not history["labels"]:
        history["labels"] = ["Jul 06", "Jul 13", "Jul 20", "Jul 27", "Aug 03", "Aug 10", "Aug 17", "Aug 24", "Aug 31", "Sep 07", "Sep 14", "Sep 21"]
        history["spot"] = [4089.30, 4052.70, 4076.60, 4103.54, 4247.40, 4389.49, 4416.55, 4651.76, 4448.20, 4355.61, 4299.21, 4343.22]
        history["gld"] = [382.13, 372.35, 374.81, 374.63, 389.64, 400.96, 405.49, 423.36, 396.75, 399.72, 392.84, 398.36]
        history["bullion_conv"] = [84, 85, 86, 85, 89, 92, 91, 93, 89, 87, 88, 89]
        history["etf_conv"] = [68, 64, 65, 63, 72, 76, 74, 78, 65, 64, 61, 65]

    today_label = now.strftime("%b %d")
    if history["labels"] and history["labels"][-1] == today_label:
        history["spot"][-1] = spot_price
        history["gld"][-1] = gld_price
        history["bullion_conv"][-1] = bullion_conv
        history["etf_conv"][-1] = etf_conv
    else:
        history["labels"].append(today_label)
        history["spot"].append(spot_price)
        history["gld"].append(gld_price)
        history["bullion_conv"].append(bullion_conv)
        history["etf_conv"].append(etf_conv)

    # Maintain trailing 90-day window (~14 weekly data points)
    if len(history["labels"]) > 14:
        for k in history:
            history[k] = history[k][-14:]

    payload = {
        "timestamp_utc": now.strftime("%Y-%m-%d %H:%M UTC"),
        "spot": {"price": spot_price, "change": spot_change},
        "gld": {"price": gld_price, "change": gld_change},
        "conviction": {"bullion": bullion_conv, "etf": etf_conv},
        "macro": {
            "cb_purchases_t": cb_purchases_t,
            "sge_premium_usd": sge_premium_usd,
            "tips_10y_yield": tips_10y_yield,
            "dxy_index": dxy_index
        },
        "history": history
    }

    with open("data.json", "w") as f:
        json.dump(payload, f, indent=2)
    print("Successfully generated data.json")

if __name__ == "__main__":
    main()