"""
Stock data utility.
Primary: yfinance (real market data)
Fallback: mock data (for demo/offline mode)
"""
import random
from datetime import datetime

# Mock price seeds — realistic base prices
MOCK_STOCKS = {
    'AAPL':  {'name': 'Apple Inc.',             'base': 189.50, 'sector': 'Technology'},
    'GOOGL': {'name': 'Alphabet Inc.',           'base': 175.20, 'sector': 'Technology'},
    'MSFT':  {'name': 'Microsoft Corporation',   'base': 415.30, 'sector': 'Technology'},
    'TSLA':  {'name': 'Tesla Inc.',              'base': 248.90, 'sector': 'Automotive'},
    'AMZN':  {'name': 'Amazon.com Inc.',         'base': 192.60, 'sector': 'E-Commerce'},
    'NVDA':  {'name': 'NVIDIA Corporation',      'base': 875.40, 'sector': 'Technology'},
    'META':  {'name': 'Meta Platforms Inc.',     'base': 512.80, 'sector': 'Social Media'},
    'NFLX':  {'name': 'Netflix Inc.',            'base': 635.10, 'sector': 'Entertainment'},
    'AMD':   {'name': 'Advanced Micro Devices',  'base': 168.20, 'sector': 'Technology'},
    'INTC':  {'name': 'Intel Corporation',       'base': 42.30,  'sector': 'Technology'},
    'JPM':   {'name': 'JPMorgan Chase & Co.',    'base': 198.50, 'sector': 'Finance'},
    'BAC':   {'name': 'Bank of America Corp.',   'base': 38.90,  'sector': 'Finance'},
    'V':     {'name': 'Visa Inc.',               'base': 278.40, 'sector': 'Finance'},
    'JNJ':   {'name': 'Johnson & Johnson',       'base': 152.10, 'sector': 'Healthcare'},
    'WMT':   {'name': 'Walmart Inc.',            'base': 67.20,  'sector': 'Retail'},
    'DIS':   {'name': 'The Walt Disney Company', 'base': 112.30, 'sector': 'Entertainment'},
    'PYPL':  {'name': 'PayPal Holdings Inc.',    'base': 63.80,  'sector': 'Finance'},
    'UBER':  {'name': 'Uber Technologies Inc.',  'base': 71.40,  'sector': 'Transportation'},
    'SPOT':  {'name': 'Spotify Technology S.A.', 'base': 312.60, 'sector': 'Entertainment'},
    'COIN':  {'name': 'Coinbase Global Inc.',    'base': 225.30, 'sector': 'Crypto/Finance'},
}


def _mock_price(symbol: str) -> float:
    """Generate a deterministic-ish fluctuating mock price."""
    info = MOCK_STOCKS.get(symbol.upper())
    if not info:
        # Unknown stock — random price between 10–500
        random.seed(hash(symbol) % 1000)
        base = random.uniform(10, 500)
    else:
        base = info['base']

    # Simulate small daily fluctuation using current minute as seed
    seed = int(datetime.utcnow().strftime('%Y%m%d%H%M')) + hash(symbol)
    random.seed(seed)
    change_pct = random.uniform(-0.025, 0.025)  # ±2.5%
    return round(base * (1 + change_pct), 2)


def _mock_full(symbol: str) -> dict:
    symbol = symbol.upper()
    info = MOCK_STOCKS.get(symbol, {
        'name': symbol, 'base': 100.0, 'sector': 'Unknown'
    })
    price = _mock_price(symbol)
    base = info['base']

    random.seed(hash(symbol + datetime.utcnow().strftime('%Y%m%d')))
    prev_close = round(base * random.uniform(0.975, 1.025), 2)
    change = round(price - prev_close, 2)
    change_pct = round((change / prev_close) * 100, 2)

    return {
        'symbol': symbol,
        'name': info['name'],
        'price': price,
        'prev_close': prev_close,
        'change': change,
        'change_pct': change_pct,
        'open': round(prev_close * random.uniform(0.99, 1.01), 2),
        'high': round(price * random.uniform(1.001, 1.02), 2),
        'low': round(price * random.uniform(0.98, 0.999), 2),
        'volume': random.randint(5_000_000, 80_000_000),
        'market_cap': f"${round(price * random.randint(1_000_000, 3_000_000_000) / 1e12, 2)}T",
        'sector': info['sector'],
        'pe_ratio': round(random.uniform(15, 45), 1),
        '52w_high': round(price * random.uniform(1.05, 1.30), 2),
        '52w_low': round(price * random.uniform(0.70, 0.95), 2),
        'source': 'mock',
    }


def get_stock_price(symbol: str, full: bool = False):
    """Return price (float) or full dict if full=True."""
    symbol = symbol.upper()
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='2d')
        if hist.empty:
            raise ValueError("No data")
        price = round(float(hist['Close'].iloc[-1]), 2)
        if not full:
            return price

        info = ticker.info or {}
        prev_close = round(float(hist['Close'].iloc[-2]) if len(hist) > 1 else price, 2)
        change = round(price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

        return {
            'symbol': symbol,
            'name': info.get('longName', symbol),
            'price': price,
            'prev_close': prev_close,
            'change': change,
            'change_pct': change_pct,
            'open': round(float(info.get('open', price)), 2),
            'high': round(float(info.get('dayHigh', price)), 2),
            'low': round(float(info.get('dayLow', price)), 2),
            'volume': info.get('volume', 0),
            'market_cap': info.get('marketCap', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A'),
            '52w_high': info.get('fiftyTwoWeekHigh', 'N/A'),
            '52w_low': info.get('fiftyTwoWeekLow', 'N/A'),
            'source': 'live',
        }
    except Exception:
        if full:
            return _mock_full(symbol)
        return _mock_price(symbol)


def get_market_data() -> list:
    """Return market overview for top stocks."""
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META', 'NFLX']
    result = []
    for sym in symbols:
        try:
            data = get_stock_price(sym, full=True)
            result.append(data)
        except Exception:
            pass
    return result


def search_stocks(query: str) -> list:
    """Search stocks by symbol or name."""
    query = query.upper()
    results = []
    for sym, info in MOCK_STOCKS.items():
        if query in sym or query in info['name'].upper():
            results.append({'symbol': sym, 'name': info['name'], 'sector': info['sector']})
    return results[:8]
