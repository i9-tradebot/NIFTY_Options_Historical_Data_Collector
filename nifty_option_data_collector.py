import pandas as pd
# from kiteconnect import KiteConnect
import os,copy,yaml,re
from time import sleep
import time as time_module  # to avoid confusion with datetime.time
from kiteext_2024 import KiteExt
import sqlite3
from datetime import datetime, timedelta, date,datetime as dt, time as dttime

# ------------------- CONFIG -------------------
with open('live_data.yaml') as f:
    cfg = yaml.safe_load(f)
UserID = cfg['userid']
enctoken = cfg['enctoken']

kite = KiteExt()
kite.login_using_enctoken(userid= UserID, enctoken=enctoken, public_token=None) 
        
# ------------------- INSTRUMENTS -------------------
INS_FILE = "pk11.feather"
Initial_Subscribr_TokenList = [256265]

def Zerodha_Token(file_name):
    global Initial_Subscribr_TokenList
    if os.path.exists(file_name):
        creation_time = os.path.getmtime(file_name)
        if datetime.fromtimestamp(
                creation_time).date() == datetime.now().date():
            print("Using cached instruments")
            ins_df = pd.read_feather(file_name)
        else:
            print("Downloading fresh instruments...")
            instruments = kite.instruments()
            ins_df = pd.DataFrame(instruments)
            ins_df["expiry"] = pd.to_datetime(ins_df["expiry"])
            ins_df.to_feather(file_name)
    else:
        print("Downloading instruments...")
        instruments = kite.instruments()
        ins_df = pd.DataFrame(instruments)
        ins_df["expiry"] = pd.to_datetime(ins_df["expiry"])
        ins_df.to_feather(file_name)
    mcx = ins_df[(ins_df.segment == 'MCX-FUT') & (
        ins_df.name.isin(['CRUDEOIL', 'GOLDPETAL', 'NATURALGAS', 'SILVERM']))]
    Initial_Subscribr_TokenList.extend(mcx['instrument_token'].tolist())
    return ins_df

ins_df = Zerodha_Token(INS_FILE)

def GetToken(symbols):
    tokens = []
    for i in symbols:
        if not i or i == 'None':
            tokens.append(0)
            continue
        try:
            exchange, tradingsymbol = i.split(':')
            token = ins_df[(ins_df.exchange == exchange)
                           & (ins_df.tradingsymbol == tradingsymbol
                              )].iloc[0]['instrument_token']
            tokens.append(int(token))
        except:
            print(f"Token not found: {i}")
            tokens.append(0)
    return tokens

def GetTokenDF(symbols, ins_df):
    """
    Returns a DataFrame with TradingSymbol and instrument_token
    
    symbols: list of strings like 'BFO:ADANIGREEN26MARFUT' or 'BSE:ADANIGREEN'
    ins_df: dataframe containing columns ['exchange', 'tradingsymbol', 'instrument_token']
    """
    data = []

    for sym in symbols:
        if not sym or sym == 'None':
            data.append({'TradingSymbol': sym, 'instrument_token': 0})
            continue
        try:
            exchange, tradingsymbol = sym.split(':')
            token = ins_df[
                (ins_df.exchange == exchange) & (ins_df.tradingsymbol == tradingsymbol)
            ].iloc[0]['instrument_token']
            data.append({'TradingSymbol': sym, 'instrument_token': int(token)})
        except:
            print(f"Token not found: {sym}")
            data.append({'TradingSymbol': sym, 'instrument_token': 0})

    df = pd.DataFrame(data)
    return df

def GetToken_2(tradingsymbol):
    global ins_df

    exchange = tradingsymbol[:3]
    symbol_clean = tradingsymbol[4:]

    # try exact match first
    row = ins_df[(ins_df.tradingsymbol == symbol_clean) &
        (ins_df.exchange == exchange)]

    if not row.empty:
        return int(row.iloc[0]['instrument_token'])

    # try adding suffixes
    suffixes = ["-EQ", "-BE", "-BZ"]
    for suffix in suffixes:
        alt_symbol = f"{symbol_clean}{suffix}"

        row = ins_df[(ins_df.tradingsymbol == alt_symbol) &
            (ins_df.exchange == exchange)]

        if not row.empty:
            print(f"✅ Found token for {tradingsymbol} as {alt_symbol}")
            return int(row.iloc[0]['instrument_token'])

    # if nothing works
    raise ValueError(f"Token not found for {tradingsymbol}")


symbols_list = []

# Filter exchange
exchange = ins_df[ins_df['exchange'] == 'NFO']
# exchange.to_csv('exchange.csv')
# Work on single dataframe
nifty_df = exchange[exchange["segment"] == 'NFO-FUT'].copy()

# Use existing expiry column
nifty_df["expiry"] = pd.to_datetime(nifty_df["expiry"])

# Sort + get unique expiries
unique_expiries = (nifty_df.sort_values("expiry").drop_duplicates(subset="expiry"))
# print(unique_expiries)
# Get first three expiries
first_expiry = unique_expiries.iloc[0]["expiry"]
second_expiry = unique_expiries.iloc[1]["expiry"]
third_expiry = unique_expiries.iloc[2]["expiry"]
print(first_expiry)
opt_df = exchange[exchange["segment"] == 'NFO-OPT'].copy()

# Use existing expiry column
opt_df["expiry"] = pd.to_datetime(opt_df["expiry"])
# Sort + get unique expiries
unique_expiries = (opt_df.sort_values("expiry").drop_duplicates(subset="expiry"))
# print(unique_expiries)
# Get first three expiries
first_expiry = unique_expiries.iloc[0]["expiry"]
second_expiry = unique_expiries.iloc[1]["expiry"]
third_expiry = unique_expiries.iloc[2]["expiry"]
print(first_expiry)
filtered_df = opt_df[
    (opt_df["expiry"] == first_expiry) &
    (opt_df["name"] == "NIFTY")
]

file_name = f"NIFTY_{first_expiry.strftime('%Y-%m-%d')}.feather"

filtered_df.reset_index(drop=True).to_feather(file_name)

print(filtered_df.head())

sensex_df = pd.read_feather(file_name)



# ------------------- SQLite helpers -------------------
DAYS_TO_KEEP_IN_FILE = 1000  # retention period

# Load symbols and tokens
df = sensex_df
# print(df)
# sys.exit()
# Use full path for Windows
db_path = r"D:\histdata\historical_data_1minute_nifty.db"
conn = sqlite3.connect(db_path)

def get_last_saved_timestamp(sym, conn):
    query = "SELECT MAX(candle_start) FROM candles WHERE symbol = ?"
    result = conn.execute(query, (sym,)).fetchone()
    return pd.to_datetime(result[0]) if result[0] is not None else None

def create_candles_table(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS candles (
        symbol TEXT,
        candle_start DATETIME,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        oi INTEGER,
        source TEXT,
        PRIMARY KEY(symbol, candle_start)
    )
    """)
    conn.commit()


# Ensure candles table exists
create_candles_table(conn)

def append_candles(sym, df, conn):
    if df.empty:
        return

    df = df.copy()
    print(df)
    df['candle_start'] = pd.to_datetime(df['date']).dt.tz_localize(None)

    last_ts = get_last_saved_timestamp(sym, conn)

    if last_ts is None:
        df_to_save = df.copy()
    else:
        cutoff = date.today() - timedelta(days=DAYS_TO_KEEP_IN_FILE - 1)
        df_to_save = df[df['candle_start'].dt.date >= cutoff]
        df_to_save = df_to_save[df_to_save['candle_start'] > last_ts]

    if df_to_save.empty:
        return

    df_to_save = df_to_save[['candle_start','open','high','low','close','volume','oi']].copy()
    df_to_save['symbol'] = sym
    df_to_save['source'] = 'kite'

    df_to_save.to_sql('candles', conn, if_exists='append', index=False)
    print(f"Saved {len(df_to_save)} candles → {sym}")

# Today and 3 previous days (last 4 days)
end_date = datetime.now().date()
start_date = end_date - timedelta(days=3)  # last 4 calendar days


# ---------------------------------------------------
# DATE RANGE
# ---------------------------------------------------
end_date = datetime.now().date()
start_date = end_date - timedelta(days=10)

# ---------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------
candle_start_time = dt.combine(dt.today(), dttime(9, 15))

time_frame = 3

intervals_passed = (
    dt.now() - candle_start_time
).total_seconds() // (time_frame * 60)

next_candle_close = candle_start_time + timedelta(
    minutes=(intervals_passed + 1) * time_frame
)

while True:

    sleep(5)

    currt_time = dt.now()

    try:

        if currt_time >= next_candle_close:

            conn = sqlite3.connect(db_path)

            intervals_passed = (
                currt_time - candle_start_time
            ).total_seconds() // (time_frame * 60)

            next_candle_close = candle_start_time + timedelta(
                minutes=(intervals_passed + 1) * time_frame
            )

            for _, row in df.iterrows():
                sym = row['tradingsymbol']
                tk = row['instrument_token']

                # Skip invalid tokens or non-NFO symbols if desired
                if not tk:
                    continue

                try:
                    # Fetch last 4 days
                    hist = kite.historical_data(
                        tk,
                        start_date,
                        end_date,
                        'minute',
                        oi=True
                    )

                    if hist:
                        hist_df = pd.DataFrame(hist)
                        append_candles(sym, hist_df, conn)  # append only missing/new candles

                except Exception as e:
                    print(f"Error fetching {sym}: {e}")

            conn.close()
        else:
            if currt_time.time() >= dttime(22, 30):
                print_and_log('Market closed.')
                sleep(5)
                break
            print(f"Waiting for next candle close: {next_candle_close.strftime('%H:%M:%S')} | Now: {currt_time.strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"Error fetching {sym}: {e}")


