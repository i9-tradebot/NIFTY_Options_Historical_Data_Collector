# NIFTY Options Historical Data Collector

A Python-based data collection system that downloads 1-minute historical candles for all NIFTY option contracts of the nearest expiry from Zerodha Kite and stores them in a SQLite database.

## Features

* Login using Zerodha `enctoken`
* Downloads and caches Zerodha instrument master
* Automatically identifies the nearest NIFTY option expiry
* Fetches 1-minute OHLCV + Open Interest (OI) data
* Stores data in SQLite database
* Prevents duplicate candle insertion
* Incremental updates every 3 minutes
* Supports long-term historical data retention

## Project Structure

```text
.
├── main.py
├── live_data.yaml
├── pk11.feather
├── historical_data_1minute_nifty.db
├── README.md
└── requirements.txt
```

## Requirements

* Python 3.10+
* Zerodha Trading Account
* Valid `enctoken`
* SQLite (included with Python)

## Configuration

Create a file named `live_data.yaml`:

```yaml
userid: YOUR_USER_ID
enctoken: YOUR_ENCTOKEN
```

Example:

```yaml
userid: AB1234
enctoken: xxxxxxxxxxxxxxxxxxxxxxxxx
```

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/nifty-options-data-collector.git
cd nifty-options-data-collector
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Script

```bash
python main.py
```

The script will:

1. Login to Zerodha.
2. Download instrument data (or use cached data).
3. Find the nearest NIFTY option expiry.
4. Create a SQLite database if it does not exist.
5. Continuously fetch historical 1-minute candles.
6. Store new candles into the database.

## Database Schema

Table: `candles`

| Column       | Type     |
| ------------ | -------- |
| symbol       | TEXT     |
| candle_start | DATETIME |
| open         | REAL     |
| high         | REAL     |
| low          | REAL     |
| close        | REAL     |
| volume       | INTEGER  |
| oi           | INTEGER  |
| source       | TEXT     |

Primary Key:

```sql
(symbol, candle_start)
```

## Data Retention

The script keeps data according to:

```python
DAYS_TO_KEEP_IN_FILE = 1000
```

Older records are ignored during insertion.

## Cached Instrument File

The Zerodha instrument dump is cached locally:

```text
pk11.feather
```

A fresh download is automatically performed once per day.

## Notes

* The script uses Zerodha historical APIs.
* Open Interest (OI) data is enabled.
* Duplicate candles are automatically skipped.
* Suitable for option-chain analytics, backtesting, and OI studies.

## Security

Do not commit:

* `live_data.yaml`
* SQLite database files
* Cached instrument files
* API tokens

Add them to `.gitignore`.

## Disclaimer

This project is intended for educational and research purposes. Ensure compliance with Zerodha's API usage policies and rate limits.
