"""Crypto AI Trader — research dashboard and virtual paper trading only."""
import streamlit as st
import pandas as pd
from catalog import WATCHLIST, CRYPTO, STOCKS, ETFS

st.set_page_config(page_title="Atlas Trader AI | Simulação", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp {background: #090e1b; color: #e7eefb}
.block-container {padding-top: 2rem; max-width: 1500px}
h1,h2,h3 {letter-spacing: -.035em}
[data-testid="stMetric"] {background:#121c2e; padding:18px; border:1px solid #24334b; border-radius:16px}
[data-testid="stSidebar"] {background:#0d1524}
div.stButton>button[kind="primary"] {background:#3a74ff; border-radius:10px}
div[data-testid="stAlert"] {border-radius:12px}
</style>
""", unsafe_allow_html=True)
st.sidebar.title("◈ ATLAS TRADER AI")
st.sidebar.caption("Mercados • Modelos • Simulação")
page = st.sidebar.radio("Navegação", ["🏠 Visão geral", "🌍 Radar de 150 ativos", "📊 Gráficos e previsões", "🤖 Trading virtual", "⏱️ Estudo de prazos", "⚙️ Segurança"], label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.info("🛡️ Apenas simulação. Sem depósitos, levantamentos ou ordens reais.")
st.sidebar.caption("O Render gratuito pode suspender o serviço. Nenhuma execução contínua está ativa.")

st.title("ATLAS / Trader AI")
st.caption("Centro de análise multi-mercado · Dados públicos sujeitos a atrasos · Protótipo de investigação")

if page == "🏠 Visão geral":
    st.subheader("O teu centro de mercados")
    a,b,c,d = st.columns(4)
    a.metric("Ativos no catálogo", len(WATCHLIST))
    b.metric("Criptomoedas", len(CRYPTO))
    c.metric("Ações", len(STOCKS))
    d.metric("ETFs", len(ETFS))
    st.info("Começa no Radar para comparar ativos; abre Gráficos e previsões para estudar um ativo e os horizontes de 1, 5 e 20 dias.")
    st.markdown("### Como interpretar as previsões")
    st.write("As percentagens são estimativas de um modelo estatístico, não certezas. O teste cronológico compara o modelo com uma previsão de referência. Uma previsão de 70% não implica 70% de acerto comprovado.")
    st.write("**Trading normal:** compras e vendas virtuais, com intenção de reservar 30% dos lucros líquidos realizados numa versão futura. **Subida/descida:** estudo separado; ainda sem contratos binários nem execução.")
    st.warning("O radar técnico não é uma recomendação de investimento. O modelo de previsões não foi validado para negociar com dinheiro real.")

elif page == "🌍 Radar de 150 ativos":
    st.subheader("Radar global")
    st.caption("50 criptomoedas · 80 ações · 20 ETFs. O carregamento inicial pode demorar; ativos sem dados são omitidos.")
    market = st.selectbox("Mercado", ["Todos", "Cripto", "Ações", "ETF"])
    st.caption("Sinais técnicos: tendência, médias móveis e momento. Não representam uma probabilidade de lucro.")
    if st.button("🔎 Atualizar radar", type="primary"):
        try:
            from scanner import scan
            with st.spinner("A consultar os mercados em lotes..."):
                st.session_state["radar"] = scan()
        except Exception as exc:
            st.error(f"Não foi possível atualizar: {exc}")
    radar = st.session_state.get("radar")
    if radar is not None and not radar.empty:
        view = radar if market == "Todos" else radar[radar["Mercado"] == market]
        a,b,c = st.columns(3)
        a.metric("Ativos com dados", len(view))
        b.metric("Candidatos a compra", int(view["Sinal técnico"].str.contains("COMPRAR").sum()))
        c.metric("Candidatos a saída", int(view["Sinal técnico"].str.contains("VENDER").sum()))
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.caption("Seleciona um ativo na aba Gráficos e previsões para obter indicadores e percentagens do modelo.")
    else:
        st.info("Carrega em Atualizar radar para começar.")

elif page == "📊 Gráficos e previsões":
    st.subheader("Laboratório de gráficos e IA")
    kind = st.selectbox("Categoria", ["Ações", "Cripto", "ETF"])
    assets = [x["symbol"] for x in WATCHLIST if x["category"] == kind]
    symbol = st.selectbox("Ativo", assets, index=0)
    period = st.selectbox("Histórico", ["1y", "2y", "5y"], index=1)
    if st.button("📈 Estudar gráfico e prever", type="primary"):
        try:
            from asset_analysis import history, indicators, forecast
            import plotly.graph_objects as go
            with st.spinner("A obter preços, calcular indicadores e validar previsões..."):
                raw = history(symbol, period)
                data = indicators(raw)
                reports = []
                for h in (1,5,20):
                    try:
                        reports.append(forecast(raw, h))
                    except ValueError:
                        pass
                st.session_state["detail"] = (symbol, raw, data, reports)
        except Exception as exc:
            st.error(f"Falha na análise: {exc}")
    detail = st.session_state.get("detail")
    if detail and detail[0] == symbol:
        _, raw, data, reports = detail
        a,b,c,d = st.columns(4)
        a.metric("Último fecho (USD)", f"{float(raw.Close.iloc[-1]):,.2f}")
        a1 = float(raw.Close.iloc[-1] / raw.Close.iloc[-2] - 1)*100
        b.metric("Variação diária", f"{a1:+.2f}%")
        c.metric("RSI (14)", f"{float(data.RSI14.iloc[-1]):.1f}")
        d.metric("Volatilidade diária", f"{float(data.Vol20.iloc[-1])*100:.2f}%")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=raw.index, open=raw.Open, high=raw.High, low=raw.Low, close=raw.Close, name="Preço"))
        fig.add_trace(go.Scatter(x=data.index, y=data.MA20, name="Média 20", line=dict(width=1.6)))
        fig.add_trace(go.Scatter(x=data.index, y=data.MA50, name="Média 50", line=dict(width=1.6)))
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10,r=10,t=20,b=10), xaxis_rangeslider_visible=False, paper_bgcolor="#090e1b", plot_bgcolor="#0d1524", legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("### Perspetivas da IA por duração")
        if reports:
            for r in reports:
                with st.container(border=True):
                    st.markdown(f"**Próximos {r['horizon']} dia(s)**")
                    l,m,n = st.columns(3)
                    l.metric("Prob. estimada SUBIR", f"{r['p_up']:.1%}")
                    m.metric("Prob. estimada DESCER", f"{r['p_down']:.1%}")
                    n.metric("Acerto no teste", f"{r['accuracy']:.1%}")
                    st.progress(r["p_up"], text="Estimativa de subida (não calibrada)")
                    st.caption(f"Teste: {r['samples']} observações · Brier modelo {r['brier']:.3f} / referência {r['baseline']:.3f} · " + ("Melhor que a referência" if r["better_than_baseline"] else "Pior que a referência"))
            st.warning("Estas probabilidades não estão calibradas nem aprovadas para operar. Os prazos são dias de negociação nas ações e dias corridos nas criptomoedas. O modelo não prevê um preço exato.")
        else:
            st.warning("Histórico insuficiente para calcular previsões validadas. Experimenta um período maior.")
        st.markdown("### Indicadores")
        st.line_chart(data[["RSI14"]].dropna())
        st.bar_chart(data[["Volume"]].tail(90))
        st.caption(f"Último fecho disponível: {raw.index[-1].date()}. Fontes públicas podem ter atrasos; mercados de ações fecham em horários específicos.")
    else:
        st.info("Escolhe um ativo e carrega em Estudar gráfico e prever.")

elif page == "🤖 Trading virtual":
    st.subheader("Trading virtual · BTC / ETH")
    st.warning("Este motor executa UM ciclo por clique. Não faz trading contínuo nem ordens reais.")
    from market import candles
    from model import fit_and_score, latest_signal
    from paper import connect, snapshot, step, history as trade_history
    symbol = st.selectbox("Mercado virtual", ["BTC/USD", "ETH/USD"])
    threshold = st.slider("Probabilidade mínima estimada", .50, .95, .70, .05)
    enabled = st.toggle("Autorizar compra/venda virtual neste ciclo", value=False)
    if st.button("Executar ciclo virtual", type="primary"):
        try:
            with st.spinner("A analisar velas horárias..."):
                df = candles(symbol)
                _, _, _, report = fit_and_score(df)
                prob = latest_signal(df)
                price = float(df.close.iloc[-1])
                db = connect("paper_btc.db" if symbol == "BTC/USD" else "paper_eth.db")
                result = step(db, price, prob, threshold, enabled)
                wallet = snapshot(db, price)
            a,b,c = st.columns(3)
            a.metric("Carteira virtual (USD)", f"{wallet['equity']:.2f}")
            b.metric("Estimativa do modelo", f"{prob:.1%}")
            c.metric("Preço (USD)", f"{price:,.2f}")
            st.info(result)
            st.json(report)
            st.line_chart(df.set_index("timestamp")["close"])
            st.dataframe(pd.DataFrame(trade_history(db), columns=["Data UTC","Ação","Preço","Unidades","Comissão","Motivo"]), use_container_width=True, hide_index=True)
            st.caption("Cada ativo tem carteira virtual separada. Base de dados local pode perder-se após reinício no alojamento gratuito.")
        except Exception as exc:
            st.error(f"Erro no ciclo virtual: {exc}")

elif page == "⏱️ Estudo de prazos":
    st.subheader("IA · Comparação de durações")
    st.caption("Comparação exploratória de 1, 2, 4, 8, 12 e 24 velas de 1 hora. Não é um contrato binário.")
    symbol = st.selectbox("Criptomoeda", ["BTC/USD", "ETH/USD"])
    if st.button("Comparar horizontes", type="primary"):
        try:
            from market import candles
            from horizon_research import compare_horizons
            with st.spinner("A comparar modelos..."):
                results = compare_horizons(candles(symbol))
            if results:
                st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
            else:
                st.warning("Não existem dados suficientes.")
        except Exception as exc:
            st.error(str(exc))
    st.warning("Nenhum destes horizontes está aprovado para operações automáticas; falta calibração e teste após custos.")

else:
    st.subheader("Segurança e publicação")
    st.markdown("**Estado:** protótipo virtual; sem ligação a bancos ou corretoras, sem API keys e sem levantamentos.")
    st.markdown("**Domínio futuro:** trader.epicverifyapp.com, após configurar o DNS.")
    st.markdown("**Render:** alojamento do painel não garante execução contínua nem armazenamento persistente.")
    st.markdown("**Antes de negociar com dinheiro real:** validar probabilidades, testar custos e spreads, adicionar limites diários, pausa de emergência, persistência, autenticação e auditoria.")
    st.info("Não introduzas chaves privadas nem dados bancários neste painel.")
