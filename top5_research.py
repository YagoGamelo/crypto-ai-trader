"""Screen all configured assets; estimates are experimental, not calibrated.
Historical predictions use chronological holdout with an embargo.
No broker access, real trades, opinions, or video sentiment are implied.
"""
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss
from catalog import WATCHLIST

def evaluate(close, horizon=5):
    c = close.astype(float).dropna()
    ret = c.pct_change()
    x = pd.DataFrame({"r1":ret,"r5":c.pct_change(5),"r20":c.pct_change(20),
                      "vol":ret.rolling(20).std(),"ma20":c/c.rolling(20).mean()-1,
                      "ma50":c/c.rolling(50).mean()-1})
    future = c.shift(-horizon)/c-1
    labeled = x.iloc[:-horizon].copy()
    labeled["target"] = (future.iloc[:-horizon] > 0).astype(int)
    labeled = labeled.replace([np.inf,-np.inf],np.nan).dropna()
    if len(labeled)<160: return None
    split=int(len(labeled)*.7)
    train=labeled.iloc[:split-horizon]; test=labeled.iloc[split:]
    if train.target.nunique()<2 or test.target.nunique()<2: return None
    features=["r1","r5","r20","vol","ma20","ma50"]
    clf=make_pipeline(StandardScaler(),LogisticRegression(max_iter=500))
    clf.fit(train[features],train.target)
    pred=clf.predict_proba(test[features])[:,1]
    brier=float(brier_score_loss(test.target,pred))
    baseline=float(brier_score_loss(test.target,np.full(len(test),train.target.mean())))
    accuracy=float(((pred>=.5)==test.target.to_numpy()).mean())
    recent=x.iloc[[-1]][features].replace([np.inf,-np.inf],np.nan)
    if recent.isna().any().any(): return None
    clf.fit(labeled[features],labeled.target)
    up=float(clf.predict_proba(recent)[0,1])
    return {"Prob. subir (estimada)":round(up*100,1),
            "Prob. descer (estimada)":round((1-up)*100,1),
            "Acerto teste %":round(accuracy*100,1),
            "Brier":round(brier,4),"Brier referência":round(baseline,4),
            "Validação":"Supera referência" if brier<baseline else "Não supera referência",
            "Amostras teste":len(test)}

def scan_all(progress=None, categories=None):
    rows=[]
    assets = WATCHLIST if categories is None else [a for a in WATCHLIST if a['category'] in categories]
    total=len(assets)
    for start in range(0,total,12):
        group=assets[start:start+12]; names=[a["symbol"] for a in group]
        try:
            data=yf.download(names,period="2y",interval="1d",group_by="ticker",
                             auto_adjust=True,progress=False,threads=True,timeout=15)
        except Exception:
            data=pd.DataFrame()
        for asset in group:
            name=asset["symbol"]
            try:
                if data.empty: continue
                sub=data[name] if isinstance(data.columns,pd.MultiIndex) else data
                close=sub["Close"].dropna()
                if len(close)<180: continue
                result=evaluate(close)
                if result is None: continue
                r1=float(close.iloc[-1]/close.iloc[-2]-1)*100
                rows.append({"Ativo":name,"Mercado":asset["category"],
                             "Último fecho":round(float(close.iloc[-1]),4),
                             "Variação diária %":round(r1,2),
                             "Data":str(close.index[-1].date()),**result})
            except Exception:
                continue
        if progress is not None: progress(min(start+len(group),total),total)
    return pd.DataFrame(rows)
