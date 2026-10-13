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
tab1,tab2,tab3,tab4,tab5=st.tabs(["🏆 Top 5","📈 Explorar ativo","🧪 Trading virtual","ℹ️ Metodologia","🏦 Corretoras & APIs"])
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
    st.caption("Cada visitante tem uma carteira virtual própria, temporária e separada por ativo. Sem negociação contínua.")
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
            # Session-only: public visitors must never share a single SQLite wallet.
            if "paper_wallets" not in st.session_state:
                st.session_state["paper_wallets"] = {}
            if sym not in st.session_state["paper_wallets"]:
                st.session_state["paper_wallets"][sym] = connect(":memory:")
            db = st.session_state["paper_wallets"][sym]
            # Historical Brier score must exceed the naive reference before
            # authorizing even a simulated entry.
            validated = report["brier"] < report["baseline_brier"]
            action = step(db,price,p,.70,enabled and validated)
            if enabled and not validated:
                st.warning("Operações bloqueadas: o modelo não superou a previsão de referência no teste histórico.")
            snap=snapshot(db,price)
            x,y,z=st.columns(3)
            x.metric("Saldo virtual USD",f"{snap['equity']:.2f}")
            y.metric("Estimativa",f"{p:.1%}")
            z.metric("Preço USD",f"{price:,.2f}")
            st.info(action)
            st.metric("Lucros reservados (30%) USD",f"{snap['reserved']:.2f}")
            st.dataframe(pd.DataFrame(trade_history(db),columns=["Data","Ação","Preço","Unidades","Taxa","Motivo"]),hide_index=True,use_container_width=True)
            st.caption(f"Diagnóstico: {report}. Stop-loss verificado apenas neste ciclo. Carteira apagada ao terminar a sessão." )
        except Exception as exc: st.error(str(exc))
with tab4:
    st.subheader("O que a IA estuda")
    st.write("**Nesta versão:** preços históricos, momentum, volatilidade, médias móveis e validação cronológica. O Top 5 usa modelos estatísticos separados por ativo e uma previsão de 5 dias.")
    st.write("**Opiniões de profissionais e vídeos:** ainda não são analisados automaticamente. Para integrar notícias, relatórios de analistas e transcrições de vídeos com fontes verificáveis, são necessários fornecedores de dados, permissões e controlo de qualidade. Não atribuímos notas a fontes que não consultámos.")
    st.write("**Gestão de risco:** nenhum sinal é uma ordem; o módulo de trading atual é exclusivamente virtual e manual por ciclo.")
    st.write("**Limites:** a seleção do Top 5 entre muitos modelos pode amplificar falsos positivos. É necessária validação adicional, calibração e testes de custos antes de negociar.")
    st.caption("Dados Yahoo Finance via yfinance, para investigação; verifica condições de uso antes de publicar comercialmente.")

with tab5:
    from brokers import PROVIDERS, CHECKED_ON, comparable_stock_costs
    st.subheader("Corretoras, custos e ligação ao bot")
    st.caption(f"Pesquisa orientada a residentes em Portugal · fontes oficiais consultadas em {CHECKED_ON}")
    st.info("Uma API de negociação permite estudar uma futura integração, mas o NEXUS não liga contas reais, não recebe credenciais e não envia ordens. A regulamentação e disponibilidade devem ser verificadas para a entidade que te serve.")
    a,b=st.columns(2)
    market=a.selectbox("Tipo de investimento",["Todos","Ações e ETFs","Criptomoedas"],key="broker_type")
    api_only=b.toggle("Só com API oficial de trading",value=False)
    candidates=[p for p in PROVIDERS if (market=="Todos" or p["type"]==market) and (not api_only or p["api_ok"])]
    view=pd.DataFrame([{
        "Plataforma":p["name"],"Mercado":p["type"],"API p/ bot":p["api"],
        "Compras/vendas":p["trade"],"Câmbio EUR/USD":p["fx"],
        "Saque EUR":p["withdraw_eur"],"Saque USD":p["withdraw_usd"]
    } for p in candidates])
    st.dataframe(view,hide_index=True,use_container_width=True)
    st.markdown("### Qual poderá compensar?")
    st.write("**Para um bot de ações pequeno:** Trading 212 Invest (API beta + demo + 0 € de comissão própria). **Para automação avançada de ações:** Interactive Brokers (API robusta, mas mínimos por ordem). **Para cripto spot:** Kraken Pro, a comparar com Coinbase Advanced. XTB e DEGIRO são opções para negociar manualmente, sem API oficial.")
    st.caption("A classificação é editorial e depende dos produtos, montantes, país, impostos, spreads, conversão e condições da tua conta. Não é uma garantia de segurança nem recomendação personalizada.")
    currency=st.selectbox("Moeda da ação/ETF (conta em EUR)",["USD","EUR"])
    amount=st.number_input("Valor de cada compra/venda (EUR)",min_value=10.0,max_value=1000.0,value=50.0,step=10.0,format="%.2f")
    pairs=comparable_stock_costs(amount,currency)
    st.dataframe(pd.DataFrame([{"Corretora":name,"Custo teórico total EUR":fee,"Peso do custo %":round(100*fee/amount,2)} for name,fee in pairs]),hide_index=True,use_container_width=True)
    st.caption("Exemplo ilustrativo: compra + venda pelo mesmo preço, com duas conversões EUR↔USD apenas quando o ativo é em USD. Exclui spread, impostos, diferenças de câmbio, comissões de terceiros e levantamentos. Não é uma cotação de custos. IBKR não entra nesta comparação porque tem preçários e mínimos distintos.")
    st.markdown("### Detalhes, regulamentação e tabelas oficiais")
    for p in candidates:
        with st.expander(p["name"]+"  ·  "+("API disponível" if p["api_ok"] else "Sem API para o bot")):
            st.write("**Indicação:** "+p["fit"])
            st.write("**Negociação:** "+p["trade"])
            st.write("**EUR/USD:** "+p["fx"])
            st.write("**Levantamento EUR:** "+p["withdraw_eur"])
            st.write("**Levantamento USD:** "+p["withdraw_usd"])
            st.write("**Supervisão:** "+p["regulation"])
            st.write("**Atenção:** "+p["risks"])
            st.markdown(f"[Site oficial]({p['website']}) · [Preçário]({p['fees']}) · [API / situação]({p['api_docs']}) · [Regulamentação]({p['regulator']})")
    st.warning("Uma taxa de levantamento não é uma percentagem dos lucros. Muitas plataformas cobram 0 € ou montante fixo em EUR; compras, vendas, câmbio, impostos e spreads são custos distintos. Em Portugal, o Regulamento CMVM 5/2019 proíbe em regra a comercialização de opções binárias a investidores não profissionais (com exceções específicas); por isso não incluímos plataformas binárias para integração. Consulte https://diariodarepublica.pt/dr/detalhe/regulamento-cmvm/5-2019-122754276")
    st.caption("Antes de qualquer integração real: confirmar licenças junto da CMVM/ESMA/regulador competente, testar em demo, autenticação segura, permissões de negociação sem levantamentos, limites de perdas e supervisão humana.")
