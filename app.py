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
tab1,tab2,tab_auto,tab3,tab4,tab5,tab6=st.tabs(["🏆 Top 5","📈 Explorar ativo","🤖 Auto-trading virtual","🧪 Trading virtual","ℹ️ Metodologia","🏦 Corretoras & APIs","🔐 Trading 212 DEMO"])
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

with tab6:
    import hmac
    import os
    import time
    from trading212_demo import DemoClient, Credentials, Trading212DemoError
    st.subheader("Trading 212 · Conta de demonstração")
    st.caption("Ligação oficial de teste, sem dinheiro real. O conector utiliza exclusivamente demo.trading212.com.")
    st.info("Não introduzas API Keys neste site ou no chat. Configura apenas variáveis privadas no Render ou secrets no Codespaces.")
    def _setting(name):
        value = os.environ.get(name, "").strip()
        if value:
            return value
        try:
            return str(st.secrets.get(name, "")).strip()
        except Exception:
            # Streamlit raises different exceptions for missing secrets across versions.
            return ""

    key = _setting("T212_DEMO_API_KEY")
    secret = _setting("T212_DEMO_API_SECRET")
    panel_password = _setting("T212_PANEL_PASSWORD")
    can_order = _setting("T212_ENABLE_DEMO_ORDERS") == "YES_I_UNDERSTAND_DEMO_ONLY"
    config_ready = bool(key and secret and len(panel_password) >= 16)
    if not config_ready:
        st.warning("A ligação aguarda configuração privada: T212_DEMO_API_KEY, T212_DEMO_API_SECRET e T212_PANEL_PASSWORD (mínimo 16 caracteres).")
        st.markdown("[Gerar chaves na Trading 212]("+ "https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-How-can-I-generate-an-API-key" + ")")
        st.write("No Render: serviço → Environment → adiciona as variáveis privadas → guarda e publica novamente. Gera chaves da conta PRACTICE/DEMO, nunca da conta real.")
    else:
        if not st.session_state.get("t212_authenticated", False):
            if st.session_state.get("t212_login_attempts", 0) >= 5:
                st.error("Demasiadas tentativas nesta sessão. Fecha o separador e revê a configuração.")
            else:
                with st.form("t212_login_form"):
                    password_input = st.text_input("Palavra-passe privada do painel", type="password")
                    login = st.form_submit_button("Entrar no painel demo")
                if login:
                    if hmac.compare_digest(password_input.encode("utf-8"), panel_password.encode("utf-8")):
                        st.session_state["t212_authenticated"] = True
                        st.session_state["t212_login_attempts"] = 0
                        st.rerun()
                    else:
                        st.session_state["t212_login_attempts"] = st.session_state.get("t212_login_attempts", 0) + 1
                        st.error("Palavra-passe incorreta.")
        else:
            col_left, col_right = st.columns([3,1])
            col_left.success("Painel demo desbloqueado para esta sessão do navegador.")
            if col_right.button("Sair"):
                for name in ("t212_authenticated", "t212_summary", "t212_positions", "t212_pending", "t212_instruments"):
                    st.session_state.pop(name, None)
                st.rerun()
            try:
                client = DemoClient(Credentials(key, secret))
                st.markdown("#### Conta de demonstração")
                a, b, c = st.columns(3)
                get_balance = a.button("Consultar saldo", type="primary")
                get_positions = b.button("Consultar posições")
                get_pending = c.button("Ordens pendentes")
                if get_balance:
                    st.session_state["t212_summary"] = client.account_summary()
                if get_positions:
                    st.session_state["t212_positions"] = client.positions()
                if get_pending:
                    st.session_state["t212_pending"] = client.pending_orders()
                summary = st.session_state.get("t212_summary")
                if summary:
                    cash = summary.get("cash", {})
                    currency = str(summary.get("currency", "—"))
                    p,q,r = st.columns(3)
                    p.metric("Saldo disponível", f"{float(cash.get('availableToTrade', 0)):,.2f} {currency}")
                    q.metric("Valor total da conta", f"{float(summary.get('totalValue', 0)):,.2f} {currency}")
                    r.metric("Investimentos", f"{float(summary.get('investments', {}).get('currentValue', 0)):,.2f} {currency}")
                if "t212_positions" in st.session_state:
                    positions = st.session_state["t212_positions"]
                    if positions:
                        visible = [{
                            "Nome": x.get("instrument", {}).get("name", ""),
                            "Ticker": x.get("instrument", {}).get("ticker", ""),
                            "Quantidade": x.get("quantity", 0),
                            "Disponível para venda": x.get("quantityAvailableForTrading", 0),
                            "Preço atual": x.get("currentPrice", 0),
                        } for x in positions]
                        st.dataframe(pd.DataFrame(visible), use_container_width=True, hide_index=True)
                    else:
                        st.caption("Sem posições abertas na conta de demonstração.")
                if "t212_pending" in st.session_state:
                    pending = st.session_state["t212_pending"]
                    if pending:
                        st.dataframe(pd.DataFrame([{
                            "ID": x.get("id"), "Ticker": x.get("ticker", x.get("instrument", {}).get("ticker")),
                            "Quantidade": x.get("quantity"), "Estado": x.get("status")
                        } for x in pending]), use_container_width=True, hide_index=True)
                    else:
                        st.caption("Não existem ordens pendentes.")
                st.divider()
                st.markdown("#### Ordens limite de demonstração")
                if not can_order:
                    st.info("Ordens demo bloqueadas de origem. Para permitir ordens de teste, define no Render T212_ENABLE_DEMO_ORDERS=YES_I_UNDERSTAND_DEMO_ONLY. Não existe ligação à conta real.")
                else:
                    st.warning("Estas ordens são enviadas à conta DEMO da Trading 212, não são operações locais fictícias. Não repitas uma ordem após um erro de rede sem consultar as ordens existentes: a API não oferece idempotência neste endpoint.")
                    if st.button("Carregar instrumentos oficiais"):
                        st.session_state["t212_instruments"] = client.instruments()
                    instruments = st.session_state.get("t212_instruments", [])
                    if not summary:
                        st.info("Consulta primeiro o saldo da conta.")
                    elif not instruments:
                        st.info("Carrega os instrumentos oficiais antes de criar uma ordem.")
                    else:
                        currency = str(summary.get("currency", ""))
                        # Research watchlist uses Yahoo symbols; only official
                        # Trading 212 ticker IDs returned by their API are allowed.
                        query = st.text_input("Pesquisar ticker ou empresa na Trading 212", max_chars=40)
                        cleaned_query = query.casefold().strip()
                        matches = [x for x in instruments
                                   if x.get("currencyCode") == currency
                                   and (not cleaned_query or
                                        cleaned_query in str(x.get("ticker", "")).casefold() or
                                        cleaned_query in str(x.get("name", "")).casefold())]
                        if not cleaned_query:
                            st.caption("Pesquisa por nome ou ticker para reduzir a lista.")
                        elif not matches:
                            st.warning("Nenhum instrumento dessa moeda corresponde à pesquisa.")
                        else:
                            subset = matches[:50]
                            choices = {str(x.get("ticker")) + " · " + str(x.get("name", "")): x for x in subset}
                            selected = st.selectbox("Instrumento confirmado pela Trading 212", list(choices.keys()))
                            instrument = choices[selected]
                            side = st.radio("Operação", ["COMPRAR", "VENDER"], horizontal=True)
                            qty = st.number_input("Quantidade de ações", min_value=0.000001, max_value=1000.0,
                                                  value=0.01, step=0.01, format="%.6f")
                            limit_price = st.number_input("Preço limite por ação na moeda da conta", min_value=0.000001,
                                                          max_value=100000.0, value=10.0, step=0.5, format="%.4f")
                            estimated_cost = qty * limit_price
                            st.caption(f"Valor de referência {estimated_cost:.2f} {currency}. Máximo por ordem demo: 10 {currency}. Sem conversões cambiais neste protótipo.")
                            typed = st.text_input("Para confirmar uma ordem DEMO, escreve CONFIRMAR DEMO", max_chars=24)
                            if st.button("Enviar ordem limite para conta DEMO", type="primary"):
                                if typed != "CONFIRMAR DEMO":
                                    st.error("Escreve CONFIRMAR DEMO antes de enviar a ordem.")
                                elif time.monotonic() - st.session_state.get("t212_last_attempt", -1e9) < 60:
                                    st.error("Só é permitida uma tentativa por minuto nesta sessão.")
                                else:
                                    st.session_state["t212_last_attempt"] = time.monotonic()
                                    # Fresh reads; never rely on stale values for risk limits.
                                    live_summary = client.account_summary()
                                    live_positions = client.positions()
                                    account_currency = str(live_summary.get("currency", ""))
                                    holdings = next((float(x.get("quantityAvailableForTrading", 0))
                                                     for x in live_positions
                                                     if x.get("instrument", {}).get("ticker") == instrument.get("ticker")), 0.0)
                                    signed_qty = qty if side == "COMPRAR" else -qty
                                    result = client.place_demo_limit(
                                        instrument=instrument, quantity=signed_qty, limit_price=limit_price,
                                        account_currency=account_currency,
                                        available_to_trade=float(live_summary.get("cash", {}).get("availableToTrade", 0)),
                                        quantity_available_to_sell=holdings, explicitly_confirmed=True)
                                    st.success("Pedido de ordem DEMO enviado. Consulta as ordens e confirma o estado de execução na Trading 212.")
                                    st.write("ID:", str(result.get("id", "por confirmar")))
                                    st.write("Estado:", str(result.get("status", "por confirmar")))
            except Trading212DemoError as exc:
                st.error(str(exc))
            except (TypeError, ValueError):
                st.error("Resposta inesperada da conta demo. Não foi enviada uma nova ordem após este erro.")
    st.caption("A conta demo Trading 212 é independente da carteira simulada de 50 USD do separador anterior. Sem negociação real, sem execução automática e sem API de levantamentos.")

with tab_auto:
    from datetime import datetime, timezone
    import time
    from auto_paper import create_portfolio, evaluate_cycle, portfolio_equity, decision_table
    st.subheader("Piloto automático · Ações")
    st.caption("O modelo escolhe empresas para comprar e vender em carteira virtual. Nenhuma ordem é enviada à Trading 212 ou a qualquer corretora.")
    m1,m2,m3,m4=st.columns(4)
    m1.metric("COMPRAR", "Subida ≥70%", help="Estimativa de subida para 5 dias; não calibrada.")
    m2.metric("VENDER", "Descida ≥70%", help="Só vende posições existentes; não abre short.")
    m3.metric("FECHAR", "Subida ≤50%", help="Fecha a posição mesmo que a descida ainda não tenha atingido 70%.")
    m4.metric("Proteção lucro", "−3% do pico", help="Stop móvel virtual quando houve valorização observada de 4%; também existe stop de perda de 5%.")
    st.info("O motor usa a mesma previsão da tabela das empresas. Compra a partir de 70% de subida apenas se o modelo superar a referência; vende se a descida atingir 70%, se a subida cair até 50% ou se disparar uma proteção de risco. Reserva 30% dos lucros líquidos realizados.")
    if "autobot_wallet" not in st.session_state:
        st.session_state["autobot_wallet"] = create_portfolio()
    st.warning("Somente simulação: preços históricos de fecho, sem execução real. As percentagens NÃO são probabilidades calibradas de lucro. O modo automático funciona apenas enquanto a sessão do site estiver conectada.")
    @st.fragment(run_every="1h")
    def automatic_paper_dashboard():
        portfolio=st.session_state["autobot_wallet"]
        enabled=st.toggle("Ativar decisões virtuais automáticas enquanto o site estiver aberto",
                          value=False,key="autobot_enabled")
        run_now=st.button("🔍 Analisar empresas e executar um ciclo virtual agora",
                          type="primary",key="autobot_run_now")
        current=time.time()
        due=enabled and current-st.session_state.get("autobot_checked_epoch",0)>=3600
        if run_now or due:
            try:
                from top5_research import scan_all
                with st.spinner("A analisar o histórico das empresas e calcular sinais..."):
                    dataset=scan_all(categories=("Ações",))
                    st.session_state["autobot_checked_epoch"]=time.time()
                    if dataset.empty:
                        st.warning("Não há preços e previsões suficientes; nenhuma operação foi executada.")
                    else:
                        latest_rows=dataset.to_dict("records")
                        st.session_state["autobot_latest_rows"]=latest_rows
                        if enabled:
                            cycle=evaluate_cycle(portfolio,latest_rows,now=datetime.now(timezone.utc))
                        else:
                            cycle={"actions":[],"signal_table":decision_table(portfolio,latest_rows)}
                        st.session_state["autobot_last_cycle"]=cycle
                        st.session_state["autobot_coverage"]=len(dataset)
                        st.session_state["autobot_last_analysis"]=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                        if cycle["actions"]:
                            st.success(f"{len(cycle['actions'])} operação(ões) virtuais registadas neste ciclo.")
                        elif enabled:
                            st.info("Análise concluída: nenhum novo trade satisfaz as regras ou o sinal do dia já foi processado.")
                        else:
                            st.info("Análise efetuada sem operações. Ativa o interruptor para permitir execução virtual automática.")
            except Exception as exc:
                st.error(f"Falha na análise automática; sem novas operações: {exc}")
        metrics=st.columns(4)
        metrics[0].metric("Carteira virtual (USD)",f"{portfolio_equity(portfolio):.2f}")
        metrics[1].metric("Disponível USD",f"{portfolio['cash']:.2f}")
        metrics[2].metric("Lucros reservados USD",f"{portfolio['reserved']:.2f}")
        metrics[3].metric("Posições abertas",len(portfolio["positions"]))
        if "autobot_last_analysis" in st.session_state:
            st.caption(f"Última análise: {st.session_state['autobot_last_analysis']} · Ações com dados: {st.session_state.get('autobot_coverage',0)}.")
        else:
            st.caption("Ainda não houve análise nesta sessão.")
        if "autobot_latest_rows" in st.session_state:
            st.markdown("#### Tabela de previsões e decisões da IA")
            table_rows=decision_table(portfolio,st.session_state["autobot_latest_rows"])
            if table_rows:
                table=pd.DataFrame(table_rows)
                st.dataframe(table,use_container_width=True,hide_index=True)
                st.caption("70% SUBIDA = candidato a compra; 70% DESCIDA = vender se detido; 50% ou menos SUBIDA = fechar se detido. Sinais são previsões não calibradas.")
            else:
                st.caption("Nenhum sinal recente de ações.")
        if portfolio["positions"]:
            st.markdown("#### Empresas em carteira")
            positions=[]
            for ticker,position in portfolio["positions"].items():
                last_price=portfolio["last_prices"].get(ticker,position["entry_price"])
                positions.append({"Empresa":ticker,"Entrada USD":round(position["entry_price"],4),
                                  "Último fecho USD":round(last_price,4),
                                  "Unidades":round(position["quantity"],6),
                                  "Valor virtual USD":round(position["quantity"]*last_price,2),
                                  "Variação desde entrada %":round(100*(last_price/position["entry_price"]-1),2)})
            st.dataframe(pd.DataFrame(positions),hide_index=True,use_container_width=True)
        if portfolio["trades"]:
            st.markdown("#### Histórico de decisões")
            transactions=pd.DataFrame(portfolio["trades"][::-1])
            transactions["prob_subida"]=transactions["prob_subida"].mul(100).round(1)
            transactions=transactions.rename(columns={"prob_subida":"Subida estimada %"})
            st.dataframe(transactions.head(40),hide_index=True,use_container_width=True)
        if not enabled:
            if st.button("Reiniciar esta carteira virtual",key="autobot_reset"):
                st.session_state["autobot_wallet"]=create_portfolio()
                for key in ("autobot_last_cycle","autobot_coverage","autobot_last_analysis","autobot_checked_epoch"):
                    st.session_state.pop(key,None)
                st.rerun()
        st.caption("Máx. 20% do saldo investível por compra, 3 posições, 1 nova compra por ciclo, stop virtual de 5%, trailing stop de 3% após +4% observado e bloqueio de novas compras após queda diária de 5%. Cada ativo só é negociado uma vez por vela diária. Enquanto esta página estiver aberta, o site reavalia aproximadamente de hora a hora; Render/Codespaces podem suspender e interromper a execução.")
    automatic_paper_dashboard()
