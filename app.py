"""Streamlit dashboard: paper trading ONLY."""
import streamlit as st
import pandas as pd
from market import candles
from model import fit_and_score, latest_signal
from paper import connect, snapshot, step, history

st.set_page_config(page_title="Crypto AI Trader | PAPER", page_icon="📈", layout="wide")
st.title("📈 Crypto AI Trader")
st.warning("SIMULAÇÃO — dinheiro virtual. Nenhuma compra ou venda real é efetuada.")
symbol = st.selectbox("Mercado", ["BTC/USD", "ETH/USD"])
threshold = st.slider("Probabilidade mínima estimada", 0.50, 0.95, 0.70, 0.05)
enabled = st.toggle("Autorizar operações virtuais neste ciclo", value=False)
st.caption("O botão abaixo executa apenas UM ciclo. O site não opera sozinho quando está fechado.")
if st.button("Atualizar análise e executar ciclo virtual", type="primary"):
    try:
        with st.spinner("A obter velas e avaliar o modelo..."):
            df = candles(symbol)
            _, _, _, report = fit_and_score(df)
            prob = latest_signal(df)
            price = float(df.close.iloc[-1])
            db = connect("paper_btc.db" if symbol == "BTC/USD" else "paper_eth.db")
            result = step(db, price, prob, threshold, enabled)
            s = snapshot(db, price)
        a, b, c = st.columns(3)
        a.metric("Saldo virtual nominal (USD)", f"{s['equity']:.2f}")
        b.metric("Probabilidade estimada", f"{prob:.1%}")
        c.metric("Preço de referência (USD)", f"{price:,.2f}")
        st.info(result)
        st.write("Diagnóstico fora da amostra (30% final):", report)
        st.line_chart(df.set_index("timestamp")["close"])
        st.dataframe(pd.DataFrame(history(db), columns=["Data UTC", "Ação", "Preço USD", "Unidades", "Comissão USD", "Motivo"]), use_container_width=True)
        st.caption("Protótipo: saldo e preços em USD virtuais; NÃO são euros reais. Não há conversão cambial.")
    except Exception as e:
        st.error(f"Falha na análise: {e}")
st.caption("Protótipo educativo. O limiar 70% não está calibrado nem garante lucro. Dados e execução aproximados.")

st.divider()
st.header("🌍 Radar de 150 ativos")
st.caption("50 criptomoedas, 80 ações e 20 ETFs. Dados diários, sujeitos a atrasos, horários de bolsa e disponibilidade da fonte.")
st.warning("Os sinais abaixo são apenas tendências técnicas; NÃO são probabilidades calibradas de 70%, nem ordens de compra/venda.")
if st.button("Analisar os 150 ativos (pode demorar)"):
    try:
        from scanner import scan
        with st.spinner("A analisar dados públicos em lotes..."):
            radar = scan()
        if radar.empty:
            st.error("Não foi possível obter dados suficientes. Tenta novamente mais tarde.")
        else:
            st.success(f"{len(radar)} ativos com dados válidos; os restantes foram ignorados.")
            st.dataframe(radar, use_container_width=True, hide_index=True)
            st.caption("COMPRAR = candidato técnico, VENDER = sinal de saída caso já detenhas o ativo, ESPERAR = sem sinal. Nenhuma ordem é executada.")
    except Exception as exc:
        st.error(f"Falha no radar: {exc}")
