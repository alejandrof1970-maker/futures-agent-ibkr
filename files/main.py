"""
Futures Trading Agent — Interactive Brokers
Instrumentos : MES (Micro E-mini S&P 500) + MNQ (Micro E-mini Nasdaq)
API          : IBKR Client Portal (via IBeam)
Estrategia   : RSI + EMA + decisión AI (GPT-4o-mini)
Riesgo       : Moderado — 1 contrato por señal
"""

import os
import sys
import time
import logging
import warnings
import requests
import pandas as pd
import numpy as np
import openai
from datetime import datetime, timezone

warnings.filterwarnings("ignore")  # SSL warnings de localhost

# ── Config ─────────────────────────────────────────────────────
GATEWAY_URL = os.environ.get("IBEAM_GATEWAY_URL", "https://localhost:5000")
OPENAI_KEY  = os.environ.get("OPENAI_API_KEY", "").strip()
ACCOUNT_ID  = os.environ.get("IB_ACCOUNT_ID", "").strip()

openai.api_key = OPENAI_KEY

RISK = {
    "stop_loss_pct":    0.005,   # 0.5% stop-loss
    "take_profit_pct":  0.010,   # 1.0% take-profit
    "max_contracts":    1,       # 1 micro contrato por posición
    "max_positions":    2,       # máx 2 posiciones abiertas
    "cycle_seconds":    300,     # ciclo cada 5 minutos
}

INSTRUMENTS = ["MES", "MNQ"]

# ── Logging ─────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)s │ %(message)s",
    handlers=[
        logging.FileHandler("logs/futures.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── Sesión IBKR (Client Portal API) ────────────────────────────
session = requests.Session()
session.verify = False


def ibkr_get(endpoint: str, params: dict = None):
    try:
        r = session.get(f"{GATEWAY_URL}/v1/api{endpoint}", params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        log.debug(f"GET {endpoint} → {r.status_code}: {r.text[:200]}")
        return None
    except Exception as e:
        log.debug(f"GET {endpoint} error: {e}")
        return None


def ibkr_post(endpoint: str, payload: dict):
    try:
        r = session.post(f"{GATEWAY_URL}/v1/api{endpoint}", json=payload, timeout=10)
        if r.status_code in (200, 201):
            return r.json()
        log.warning(f"POST {endpoint} → {r.status_code}: {r.text[:300]}")
        return None
    except Exception as e:
        log.error(f"POST {endpoint} error: {e}")
        return None


def is_gateway_ready() -> bool:
    result = ibkr_get("/iserver/auth/status")
    return bool(result and result.get("authenticated"))


def get_account_id() -> str | None:
    if ACCOUNT_ID:
        return ACCOUNT_ID
    accounts = ibkr_get("/iserver/accounts")
    if accounts and "accounts" in accounts:
        return accounts["accounts"][0]
    return None


def get_portfolio_value(account: str) -> float:
    data = ibkr_get(f"/portfolio/{account}/summary")
    if data and "netliquidation" in data:
        return float(data["netliquidation"]["amount"])
    return 0.0


# ── Búsqueda de contratos front-month ──────────────────────────
def get_front_month_conid(symbol: str) -> int | None:
    results = ibkr_get("/iserver/secdef/search", params={"symbol": symbol, "secType": "FUT"})
    if not results:
        return None
    for item in results:
        if item.get("symbol") == symbol:
            sections = item.get("sections", [])
            for sec in sections:
                if sec.get("secType") == "FUT":
                    conids = sec.get("conid", "").split(";")
                    if conids:
                        return int(conids[0])
    return None


# ── Datos de mercado e indicadores ──────────────────────────────
def get_market_data(conid: int) -> dict | None:
    fields = "31,84,86,88"  # last, bid, ask, volume
    data = ibkr_get(f"/iserver/marketdata/snapshot", params={"conids": conid, "fields": fields})
    if data and len(data) > 0:
        return data[0]
    return None


def get_historical_bars(conid: int, period: str = "1d", bar: str = "5mins") -> pd.DataFrame:
    data = ibkr_get(
        f"/iserver/marketdata/history",
        params={"conid": conid, "period": period, "bar": bar, "outsideRth": False},
    )
    if not data or "data" not in data:
        return pd.DataFrame()
    df = pd.DataFrame(data["data"])
    df["close"] = pd.to_numeric(df["c"], errors="coerce")
    df["high"]  = pd.to_numeric(df["h"], errors="coerce")
    df["low"]   = pd.to_numeric(df["l"], errors="coerce")
    df["volume"]= pd.to_numeric(df["v"], errors="coerce")
    return df.dropna(subset=["close"])


def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff().dropna()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - 100 / (1 + rs)
    return round(float(rsi.iloc[-1]), 2) if not rsi.empty else 50.0


def get_indicators(conid: int) -> dict | None:
    df = get_historical_bars(conid)
    if df.empty or len(df) < 20:
        return None
    close = df["close"]
    rsi   = compute_rsi(close)
    ema9  = float(close.ewm(span=9).mean().iloc[-1])
    ema21 = float(close.ewm(span=21).mean().iloc[-1])
    price = float(close.iloc[-1])
    trend = "BULLISH" if ema9 > ema21 else "BEARISH"
    return {"price": price, "rsi": rsi, "ema9": ema9, "ema21": ema21, "trend": trend}


# ── Decisión AI ─────────────────────────────────────────────────
def ai_decision(symbol: str, ind: dict) -> str:
    prompt = f"""
Eres un trader algorítmico de futuros. Analizá este instrumento y decidí.

Instrumento : {symbol}
Precio      : {ind['price']}
RSI (14)    : {ind['rsi']}
EMA 9       : {ind['ema9']:.2f}
EMA 21      : {ind['ema21']:.2f}
Tendencia   : {ind['trend']}

Reglas:
- RSI < 35 + BULLISH → BUY
- RSI > 65 + BEARISH → SELL
- RSI entre 40-60    → HOLD
- Tendencia contraria al RSI → HOLD

Respondé SOLO con una palabra: BUY, SELL o HOLD.
"""
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0,
        )
        return resp.choices[0].message.content.strip().upper()
    except Exception as e:
        log.error(f"AI error: {e}")
        return "HOLD"


# ── Posiciones abiertas ─────────────────────────────────────────
def get_open_positions(account: str) -> dict:
    data = ibkr_get(f"/portfolio/{account}/positions/0")
    if not data:
        return {}
    positions = {}
    for pos in data:
        if pos.get("position", 0) != 0:
            positions[pos["contractDesc"].split()[0]] = pos
    return positions


# ── Órdenes ─────────────────────────────────────────────────────
def place_order(account: str, conid: int, side: str, qty: int) -> bool:
    payload = {
        "orders": [{
            "conid":     conid,
            "orderType": "MKT",
            "side":      side,
            "quantity":  qty,
            "tif":       "DAY",
        }]
    }
    result = ibkr_post(f"/iserver/account/{account}/orders", payload)
    if result:
        log.info(f"✅ Orden {side} {qty}x conid={conid} enviada")
        return True
    log.warning(f"❌ Orden {side} falló")
    return False


# ── Ciclo principal ─────────────────────────────────────────────
def run_cycle(account: str, conids: dict):
    now = datetime.now(timezone.utc)
    log.info(f"── Ciclo {now.strftime('%H:%M:%S')} UTC ──────────────────")

    # Keepalive (evitar timeout del gateway)
    ibkr_get("/tickle")

    positions = get_open_positions(account)
    if len(positions) >= RISK["max_positions"]:
        log.info(f"Posiciones abiertas: {len(positions)} — sin nuevas entradas")
        return

    for symbol, conid in conids.items():
        if symbol in positions:
            continue

        ind = get_indicators(conid)
        if not ind:
            log.debug(f"{symbol}: sin datos")
            continue

        decision = ai_decision(symbol, ind)
        log.info(
            f"{symbol:<6} │ {ind['price']:<10} │ "
            f"RSI={ind['rsi']:<6} │ {ind['trend']:<8} │ {decision}"
        )

        if decision == "BUY":
            place_order(account, conid, "BUY", RISK["max_contracts"])
        elif decision == "SELL":
            place_order(account, conid, "SELL", RISK["max_contracts"])


# ── Entry point ─────────────────────────────────────────────────
def main():
    log.info("=" * 55)
    log.info("🤖 Futures Agent | MES + MNQ | PAPER TRADING")
    log.info(f"Stop-loss: {RISK['stop_loss_pct']:.1%} | Take-profit: {RISK['take_profit_pct']:.1%}")
    log.info("=" * 55)

    log.info("Esperando IB Gateway (IBeam)...")
    for _ in range(30):
        if is_gateway_ready():
            log.info("✅ IB Gateway autenticado")
            break
        time.sleep(10)
    else:
        log.error("IB Gateway no respondió. Verificá credenciales de IBeam.")
        sys.exit(1)

    account = get_account_id()
    if not account:
        log.error("No se pudo obtener el ID de cuenta de IBKR.")
        sys.exit(1)
    log.info(f"Cuenta IBKR: {account}")

    log.info("Buscando contratos front-month...")
    conids = {}
    for symbol in INSTRUMENTS:
        conid = get_front_month_conid(symbol)
        if conid:
            conids[symbol] = conid
            log.info(f"  {symbol} → conid={conid}")
        else:
            log.warning(f"  {symbol} → contrato no encontrado")

    if not conids:
        log.error("No se encontraron contratos. Verificá la conexión con IBKR.")
        sys.exit(1)

    while True:
        try:
            run_cycle(account, conids)
        except KeyboardInterrupt:
            log.info("Agente detenido.")
            break
        except Exception as e:
            log.error(f"Error en ciclo: {e}", exc_info=True)
        time.sleep(RISK["cycle_seconds"])


if __name__ == "__main__":
    main()
