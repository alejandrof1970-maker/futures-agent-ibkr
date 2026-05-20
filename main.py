"""
Futures Trading Agent — Interactive Brokers
Conexión  : ib_insync (socket directo a IB Gateway)
Instrumentos: MES + MNQ (Micro E-mini)
Modo      : Paper Trading (puerto 4002)
"""

import os
import time
import logging
import warnings
import pandas as pd
import numpy as np
import openai
from datetime import datetime, timezone
from ib_insync import IB, Future, MarketOrder, util

warnings.filterwarnings("ignore")

# ── Config ──────────────────────────────────────────────────────
IBKR_HOST  = os.environ.get("IBKR_HOST", "localhost")
IBKR_PORT  = int(os.environ.get("IBKR_PORT", "4002"))   # 4002 = paper
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
openai.api_key = OPENAI_KEY

RISK = {
    "max_contracts":  1,
    "max_positions":  2,
    "cycle_seconds":  300,
}
INSTRUMENTS = ["MES", "MNQ"]

# ── Logging ──────────────────────────────────────────────────────
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


# ── Indicadores ──────────────────────────────────────────────────
def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff().dropna()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - 100 / (1 + rs)
    return round(float(rsi.iloc[-1]), 2) if not rsi.empty else 50.0


def get_indicators(ib: IB, contract) -> dict | None:
    bars = ib.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr="1 D",
        barSizeSetting="5 mins",
        whatToShow="TRADES",
        useRTH=True,
        formatDate=1,
    )
    if not bars or len(bars) < 20:
        return None
    df    = util.df(bars)
    close = df["close"]
    rsi   = compute_rsi(close)
    ema9  = float(close.ewm(span=9).mean().iloc[-1])
    ema21 = float(close.ewm(span=21).mean().iloc[-1])
    price = float(close.iloc[-1])
    trend = "BULLISH" if ema9 > ema21 else "BEARISH"
    return {"price": price, "rsi": rsi, "ema9": ema9, "ema21": ema21, "trend": trend}


# ── Decisión AI ──────────────────────────────────────────────────
def ai_decision(symbol: str, ind: dict) -> str:
    prompt = f"""
Eres un trader algorítmico de futuros. Decidí ahora.
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

Respondé SOLO con: BUY, SELL o HOLD
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


# ── Contratos front-month ─────────────────────────────────────────
def get_contract(ib: IB, symbol: str):
    c = Future(symbol=symbol, exchange="CME", currency="USD")
    qualified = ib.qualifyContracts(c)
    return qualified[0] if qualified else None


# ── Ciclo principal ───────────────────────────────────────────────
def run_cycle(ib: IB, contracts: dict):
    log.info(f"── Ciclo {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC ──")

    positions = {p.contract.symbol for p in ib.positions() if p.position != 0}
    if len(positions) >= RISK["max_positions"]:
        log.info(f"Posiciones abiertas: {len(positions)} — sin nuevas entradas")
        return

    for symbol, contract in contracts.items():
        if symbol in positions:
            continue
        ind = get_indicators(ib, contract)
        if not ind:
            continue
        decision = ai_decision(symbol, ind)
        log.info(f"{symbol:<6} │ {ind['price']:<10} │ RSI={ind['rsi']:<6} │ {ind['trend']:<8} │ {decision}")

        if decision in ("BUY", "SELL"):
            order = MarketOrder(decision, RISK["max_contracts"])
            trade = ib.placeOrder(contract, order)
            log.info(f"✅ Orden {decision} enviada → {trade.orderStatus.status}")


# ── Entry point ───────────────────────────────────────────────────
def main():
    log.info("=" * 55)
    log.info("🤖 Futures Agent | MES + MNQ | PAPER TRADING")
    log.info(f"Conectando a IB Gateway → {IBKR_HOST}:{IBKR_PORT}")
    log.info("=" * 55)

    ib = IB()
    for attempt in range(15):
        try:
            ib.connect(IBKR_HOST, IBKR_PORT, clientId=1)
            log.info("✅ Conectado a IB Gateway")
            break
        except Exception as e:
            log.warning(f"Intento {attempt+1}/15: {e}")
            time.sleep(20)
    else:
        log.error("No se pudo conectar. Verificá credenciales y TRADING_MODE.")
        return

    log.info(f"Cuenta: {ib.managedAccounts()}")

    contracts = {}
    for symbol in INSTRUMENTS:
        c = get_contract(ib, symbol)
        if c:
            contracts[symbol] = c
            log.info(f"  {symbol} → {c.localSymbol} (conid={c.conId})")
        else:
            log.warning(f"  {symbol} → no encontrado")

    if not contracts:
        log.error("Sin contratos. Verificá la conexión con IBKR.")
        ib.disconnect()
        return

    while True:
        try:
            run_cycle(ib, contracts)
            ib.sleep(RISK["cycle_seconds"])
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"Error en ciclo: {e}", exc_info=True)
            time.sleep(60)

    ib.disconnect()
    log.info("Agente detenido.")


if __name__ == "__main__":
    main()
