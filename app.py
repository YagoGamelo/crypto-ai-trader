"""Minimal research-first interface. Paper trading only."""
import streamlit as st
import pandas as pd
from catalog import WATCHLIST,CRYPTO,STOCKS,ETFS
st.set_page_config(page_title="NEXUS • Market Intelligence",page_icon="✦",layout="wide",initial_sidebar_state="collapsed")
st.markdown("""<style>
.stApp {background:#f5f6f8;color:#17202b}
.block-container {max-width:1220px;padding-top:2rem;padding-bottom:3rem}
h1,h2,h3 {letter-spacing:-.045em;color:#111827}
[data-testid="stMetric"] {background:#fff;border:1px solid #e8eaef;border-radius:16px;padding:18px}
[data-testid="stTabs"] button {font-weight:650}
div.stButton>button[kind="primary"] {background:#111827;border-radius:12px;border:0}
[data-testid="stSidebar"] {background:#fff}
</style>""",unsafe_allow_html=True)
st.caption("✦ NEXUS   /   MARKET INTELLIGENCE")
st.title("Menos ruído. Melhores decisões.")
st.caption("Pesquisa quantitativa em ações, ETFs e criptoativos. Apenas simulação — nenhuma ordem real.")
a,b,c=st.columns(3)
a.metric("Universo monitorizado",len(WATCHLIST))
b.metric("Empresas",len(STOCKS))
c.metric("Cripto + ETFs",len(CRYPTO)+len(ETFS))
tab1,tab2,tab3,tab4=st.tabs(["🏆 Top 5","📈 Explorar ativo","🧪 Trading virtual","ℹ️ Metodologia"])
with tab1:
    st.subheader("As 5 maiores estimativas de subida")
    st.write("O modelo analisa todos os ativos disponíveis, testa o desempenho fora da amostra e compara previsões para os próximos **5 dias**.")
    if st.button("Analisar todo o mercado",type="primary"):
        from top5_research import scan_all
        bar=st.progress(0,text="A consultar preços e calcular modelos...")
        try:
            with st.spinner("A análise pode demorar vários minutos."):
                def progress(done,total): bar.progress(done/total,text=f"{done} de {total} ativos processados")
                st.session_state["full_scan"]=scan_all(progress)
            bar.empty()
        except Exception as exc:
            st.error(f"Falha na análise: {exc}")
    df=st.session_state.get("full_scan")
    if df is not None:
        if df.empty:
            st.warning("Não foram encontrados dados suficientes. Experimenta mais tarde.")
        else:
            valid=df[df["Validação"]=="Supera referência"].sort_values("Prob. subir (estimada)",ascending=False)
            st.caption(f"{len(df)} ativos analisados com dados válidos; {len(WATCHLIST)-len(df)} indisponíveis ou sem histórico suficiente.")
            if valid.empty:
                st.warning("Nenhum modelo superou a referência neste teste. Não há um Top 5 validado.")
            else:
                top=valid.head(5).copy()
                top.insert(0,"Posição",range(1,len(top)+1))
                st.dataframe(top[["Posição","Ativo","Mercado","Prob. subir (estimada)","Prob. descer (estimada)","Acerto teste %","Data"]],hide_index=True,use_container_width=True)
                st.caption("Ranking apenas entre modelos com Brier melhor do que a referência. Isto NÃO prova calibração nem rentabilidade.")
            with st.expander("Ver a tabela completa de todos os ativos analisados"):
                st.dataframe(df.sort_values("Prob. subir (estimada)",ascending=False),hide_index=True,use_container_width=True)
                st.download_button("Exportar CSV",df.to_csv(index=False).encode("utf-8-sig"),"analise_mercados.csv","text/csv")
            st.warning("Probabilidades experimentais não calibradas. Não são sinais autorizados para operações automáticas.")
    else:
        st.info("Carrega em Analisar todo o mercado para gerar o ranking. Não são apresentados resultados fictícios.")
with tab2:
    st.subheader("Análise detalhada")
    cat=st.selectbox("Mercado",["Ações","Cripto","ETF"])
    syms=[x["symbol"] for x in WATCHLIST if x["category"]==cat]
    sym=st.selectbox("Ativo",syms)
    if st.button("Abrir estudo",type="primary"):
        try:
            from asset_analysis import history,indicators,forecast
            import plotly.graph_objects as go
            with st.spinner("A estudar o histórico..."):
                raw=history(sym,"2y"); ind=indicators(raw)
                reports=[]
                for horizon in (1,5,20):
                    try: reports.append(forecast(raw,horizon))
                    except ValueError: pass
            st.metric("Último fecho",f"{float(raw.Close.iloc[-1]):,.2f}")
            fig=go.Figure()
            fig.add_trace(go.Candlestick(x=raw.index,open=raw.Open,high=raw.High,low=raw.Low,close=raw.Close,name="Preço"))
            fig.add_trace(go.Scatter(x=ind.index,y=ind.MA20,name="Média 20"))
            fig.add_trace(go.Scatter(x=ind.index,y=ind.MA50,name="Média 50"))
            fig.update_layout(template="plotly_white",height=440,xaxis_rangeslider_visible=False,margin=dict(l=5,r=5,t=20,b=5))
            st.plotly_chart(fig,use_container_width=True)
            if reports:
                st.dataframe(pd.DataFrame([{"Prazo (dias)":r["horizon"],"Subida estimada %":round(r["p_up"]*100,1),
                    "Descida estimada %":round(r["p_down"]*100,1),"Acerto teste %":round(r["accuracy"]*100,1),
                    "Brier":round(r["brier"],3),"Referência":round(r["baseline"],3)} for r in reports]),hide_index=True,use_container_width=True)
            st.caption(f"Dados até {raw.index[-1].date()}. Probabilidades não calibradas.")
        except Exception as exc: st.error(f"Não foi possível analisar: {exc}")
with tab3:
    st.subheader("Carteira de demonstração")
    st.caption("Este motor executa apenas um ciclo quando carregas no botão. Sem negociação contínua.")
    from market import candles
    from model import fit_and_score,latest_signal
    from paper import connect,snapshot,step,history as trade_history
    sym=st.selectbox("Par",["BTC/USD","ETH/USD"])
    enabled=st.toggle("Autorizar operações virtuais neste ciclo",value=False)
    if st.button("Executar ciclo virtual"):
        try:
            df=candles(sym)
            _,_,_,report=fit_and_score(df)
            p=latest_signal(df); price=float(df.close.iloc[-1])
            db=connect("paper_btc.db" if sym=="BTC/USD" else "paper_eth.db")
            action=step(db,price,p,.70,enabled)
            snap=snapshot(db,price)
            x,y,z=st.columns(3)
            x.metric("Saldo virtual USD",f"{snap['equity']:.2f}")
            y.metric("Estimativa",f"{p:.1%}")
            z.metric("Preço USD",f"{price:,.2f}")
            st.info(action)
            st.dataframe(pd.DataFrame(trade_history(db),columns=["Data","Ação","Preço","Unidades","Taxa","Motivo"]),hide_index=True,use_container_width=True)
            st.caption(f"Diagnóstico: {report}")
        except Exception as exc: st.error(str(exc))
with tab4:
    st.subheader("O que a IA estuda")
    st.write("**Nesta versão:** preços históricos, momentum, volatilidade, médias móveis e validação cronológica. O Top 5 usa modelos estatísticos separados por ativo e uma previsão de 5 dias.")
    st.write("**Opiniões de profissionais e vídeos:** ainda não são analisados automaticamente. Para integrar notícias, relatórios de analistas e transcrições de vídeos com fontes verificáveis, são necessários fornecedores de dados, permissões e controlo de qualidade. Não atribuímos notas a fontes que não consultámos.")
    st.write("**Gestão de risco:** nenhum sinal é uma ordem; o módulo de trading atual é exclusivamente virtual e manual por ciclo.")
    st.write("**Limites:** a seleção do Top 5 entre muitos modelos pode amplificar falsos positivos. É necessária validação adicional, calibração e testes de custos antes de negociar.")
    st.caption("Dados Yahoo Finance via yfinance, para investigação; verifica condições de uso antes de publicar comercialmente.")
