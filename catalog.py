"""Curated watchlist, not a guarantee of data availability or tradability."""
CRYPTO = ["BTC","ETH","SOL","XRP","ADA","DOGE","AVAX","LINK","DOT","LTC","BCH","XLM","ATOM","UNI","AAVE","ETC","FIL","NEAR","ICP","ALGO","HBAR","SUI","APT","ARB","OP","INJ","RENDER","GRT","CRV","COMP","MKR","SNX","LDO","IMX","SAND","MANA","AXS","CHZ","ENJ","BAT","ZEC","DASH","XTZ","EOS","KAVA","FLOW","MINA","ZIL","1INCH","YFI"]
MEMECOINS = ["DOGE","SHIB","PEPE","BONK","WIF","FLOKI","PENGU","FARTCOIN","POPCAT","BRETT","TURBO","MOG","BOME","PNUT","MEW","NEIRO"]
CRYPTO = list(dict.fromkeys(CRYPTO + MEMECOINS))
STOCKS = ["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AMD","INTC","NFLX","ORCL","CRM","ADBE","IBM","CSCO","QCOM","TXN","AVGO","MU","AMAT","LRCX","KLAC","ASML","TSM","SHOP","UBER","ABNB","PYPL","SQ","COIN","HOOD","JPM","BAC","WFC","GS","MS","V","MA","AXP","C","BRK-B","JNJ","PFE","MRK","ABBV","LLY","UNH","CVS","AMGN","GILD","REGN","ISRG","MDT","TMO","DHR","ABT","PG","KO","PEP","COST","WMT","TGT","HD","LOW","MCD","SBUX","NKE","DIS","CMCSA","VZ","T","XOM","CVX","COP","SLB","CAT","DE","GE","BA","LMT"]
EXTRA_STOCKS = ["O","SOFI","PLTR","RBLX","SNOW","DDOG","NET","CRWD","PANW","NOW","INTU","BKNG","MAR","CMG","YUM","DPZ","NVO","NEM","F","GM"]
STOCKS = list(dict.fromkeys(STOCKS + EXTRA_STOCKS))
ETFS = ["SPY","QQQ","VTI","VOO","IWM","DIA","EFA","EEM","VEA","VWO","XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","GLD","SLV"]
WATCHLIST = (
    [{"symbol": x + "-USD", "category": "Cripto", "segment": "Memecoin" if x in MEMECOINS else "Cripto"} for x in CRYPTO] +
    [{"symbol": x, "category": "Ações"} for x in STOCKS] +
    [{"symbol": x, "category": "ETF"} for x in ETFS]
)
