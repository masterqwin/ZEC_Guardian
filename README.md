# ZEC Guardian

ZEC Guardian is a 24-hour ZEC monitoring assistant for GitHub Actions and Telegram alerts. It does not connect to an exchange account, does not place real orders, and does not auto buy or sell. It only analyzes public market data, creates trade plans, sends selected alerts, and records JSON state.

## What It Does

- Pulls public ZEC/USDT and BTC/USDT market data from Binance.
- Calculates RSI14, EMA20, EMA50, EMA200 when enough data exists, ATR14, average volume, price change %, and trend state.
- Scores the market from 0 to 100 and classifies signals:
  - `A`: entry candidate / good dip
  - `B`: wait
  - `C`: do not enter / risk alert
- Builds a manual trade plan from local JSON position state.
- Sends Telegram alerts only for important events with deduplication.
- Stores state, manual trade logs, and signal history in JSON files that can later migrate to SQLite.

## Safety Rules

- No exchange private API is used.
- No order endpoint exists in this project.
- No token is hardcoded.
- Signal `A` is blocked when data is incomplete or market data cannot be fetched.
- Alerts are deduplicated so GitHub Actions does not spam every 5 minutes.

## Setup

1. Create a GitHub repository and push this project.
2. Copy `.env.example` to `.env` for local testing only.
3. Add GitHub Secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Enable GitHub Actions in the repository.
5. Run the workflow manually once from the Actions tab, or wait for the 5-minute schedule.

## Local Run

```bash
pip install -r requirements.txt
python src/main.py --dry-run
python -m pytest
```

`--dry-run` prints the message payload and writes local JSON state, but it does not send Telegram messages.

## Telegram Test

1. Create a bot with BotFather and copy the bot token.
2. Send one message to your bot from the target Telegram account or group.
3. Find your chat ID.
4. Put both values in `.env` locally or GitHub Secrets in Actions.
5. Run:

```bash
python src/main.py --dry-run
```

Remove `--dry-run` only after checking the generated message.

## Manual Mode

ZEC Guardian does not trade. You manually update `data/state.json` after real-world actions.

## V2 Manual CLI

ZEC Guardian V2 records manual actions only. It never sends exchange orders.

```bash
python src/main.py --dry-run
python src/main.py --buy --zec 1 --price-thb 17000 --price-usdt 532.7
python src/main.py --sell-percent 50 --price-thb 17850 --price-usdt 560.0
python src/main.py --sell-zec 0.5 --price-thb 17850 --price-usdt 560.0
python src/main.py --sell-all --price-thb 18200 --price-usdt 570.0
```

After every manual command the system updates `data/state.json`, appends `data/trades.json`, recalculates average cost, prints a terminal summary, and sends a Telegram position update only when Telegram secrets are configured.

Core formula:

```text
total_zec = sum(lot.remaining_zec)
total_cost_thb = sum(lot.remaining_zec * lot.entry_price_thb)
average_cost_thb = total_cost_thb / total_zec if total_zec > 0 else 0
```

V2 state uses FIFO lot reduction for sells. Example:

```text
Buy 1 ZEC at 17,000 THB
Sell 50%
Buy 1 ZEC at 16,000 THB

total_zec = 1.5
total_cost_thb = 24,500
average_cost_thb = 16,333.33
```

### Record First Buy

Edit `data/state.json`:

```json
{
  "schema_version": 1,
  "position": {
    "legs": [
      {
        "leg": 1,
        "quantity_zec": 1,
        "entry_price_usdt": 420,
        "entry_price_thb": 15330,
        "opened_at": "2026-06-15T10:00:00+00:00",
        "status": "open"
      }
    ],
    "closed_quantity_zec": 0
  },
  "alerts": {},
  "daily_summary": {}
}
```

Then add a matching manual log to `data/trades.json`.

### Record TP50

Set the partial sell in `data/trades.json`:

```json
{
  "id": "manual-20260615-tp50",
  "timestamp": "2026-06-15T12:00:00+00:00",
  "side": "sell",
  "quantity_zec": 0.5,
  "price_usdt": 445,
  "note": "Manual TP50"
}
```

Update `closed_quantity_zec` in `data/state.json` if you want the dashboard calculation to reflect the partial close.

### Record TP100

Add another sell log and mark the related leg `status` as `closed`, or clear `position.legs` if the whole position is closed.

## Configuration

Defaults are in `src/config.py` and can be overridden by environment variables:

- `CAPITAL_THB=50000`
- `RESERVE_PERCENT=25`
- `ZEC_PER_LEG=1`
- `FIRST_LEG_TP50_PERCENT=5`
- `FIRST_LEG_TP100_PERCENT=7`
- `SECOND_LEG_TP50_PERCENT=7`
- `SECOND_LEG_TP100_PERCENT=9`
- `THIRD_LEG_TP50_PERCENT=9`
- `THIRD_LEG_TP100_PERCENT=11`
- `USD_THB_RATE=32.5`

`USD_THB_RATE` is only a fallback. Live runs try `https://open.er-api.com/v6/latest/USD` first and show both `FX Rate` and `FX Source` in Telegram previews.

## GitHub Actions

The workflow at `.github/workflows/zec_guardian.yml` runs every 5 minutes and supports manual execution. It installs dependencies, runs `python src/main.py`, and commits changes under `data/*.json` only.

`.env` is ignored and must never be committed.
