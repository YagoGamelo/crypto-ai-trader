"""Read-only public market-monitor panel.

Loads the latest snapshot produced by scheduled GitHub Actions. Does not
query broker APIs, execute trades, or claim intraday model calibration.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

BASE = "https://raw.githubusercontent.com/YagoGamelo/crypto-ai-trader/market-data/data/"
ACTION_URL = "https://github.com/YagoGamelo/crypto-ai-trader/actions/workflows/market-monitor.yml"
REPORT_URL = "https://github.com/YagoGamelo/crypto-ai-trader/blob/market-data/data/latest.json"


def parse_utc(iso):
    if not isinstance(iso, str):
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None


@st.cache_data(ttl=120, show_spinner=False)
def load_public_data(filename):
    if filename not in ("latest.json", "history.json"):
        raise ValueError("Ficheiro não autorizado")
    response = requests.get(BASE+filename, timeout=(5, 12),
                            headers={"Accept":"application/json"})
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Formato de relatório não reconhecido")
    return data


def recent_minutes(ts):
    dt=parse_utc(ts)
    if dt is None:
        return None
    return max(0, (datetime.now(timezone.utc)-dt).total_seconds()/60)


def _top_table(assets, probability_key):
    return pd.DataFrame([{
        "Ativo": asset.get("symbol"),
        "Mercado": asset.get("market"),
        "Prob. subir 5d %": asset.get("prob_up_pct"),
        "Prob. descer 5d %": asset.get("prob_down_pct"),
        "Movimento 30min %": (asset.get("quote") or {}).get("change_30m_pct"),
        "Última vela 30min UTC": (asset.get("quote") or {}).get("close_candle_start_utc"),
        "Sinal experimental": asset.get("signal"),
    } for asset in assets]).sort_values(
        "Prob. subir 5d %" if probability_key == "up" else "Prob. descer 5d %",
        ascending=False, na_position="last")


def render_monitor():
    st.subheader("Monitor do mercado · 30 minutos")
    st.caption("GitHub Actions atualiza os preços em execuções agendadas, mesmo com o site fechado. Os modelos para 5 velas diárias têm atualização separada.")
    a,b=st.columns([4,1])
    a.markdown(f"[Ver execuções e falhas no GitHub Actions]({ACTION_URL})")
    if b.button("Atualizar agora", key="force_monitor_refresh"):
        load_public_data.clear()
        st.rerun()
    try:
        report=load_public_data("latest.json")
    except (requests.RequestException,ValueError,TypeError) as exc:
        st.error("Ainda não consegui obter os relatórios públicos. Confirma que o monitor está ativo no GitHub Actions.")
        st.caption(f"Detalhe técnico: {type(exc).__name__}")
        return
    generated=report.get("generated_at_utc")
    if not generated:
        st.info("O monitor ainda aguarda a primeira execução. Abre o link GitHub Actions acima e escolhe Run workflow para iniciar uma análise manual.")
        st.markdown(f"[Estado atual no GitHub]({REPORT_URL})")
        return
    last_age=recent_minutes(generated)
    model_age=recent_minutes(report.get("model_updated_at"))
    if last_age is None:
        st.error("Data do último relatório inválida.")
        return
    a,b,c,d=st.columns(4)
    a.metric("Última análise", f"{last_age:.0f} min atrás")
    b.metric("Ativos com previsão", f"{report.get('model_coverage',0)} / {report.get('universe_count',0)}")
    c.metric("Preços 30min recentes", str(report.get("recent_30m_quotes",0)))
    d.metric("Candidatos de compra", str(report.get("buy_candidates",0)))
    if last_age > 75:
        st.error("Relatório desatualizado: a execução agendada pode ter falhado ou sido atrasada. Não usar estas cotações para tomar decisões.")
    if model_age is None or model_age > 30*60:
        st.warning("O modelo histórico está antigo ou sem data válida. A previsão não foi recalculada neste ciclo.")
    st.caption(f"Relatório UTC: {generated} · Modelo (5 velas diárias) atualizado UTC: {report.get('model_updated_at','indisponível')}")
    st.info("As cotações podem mudar de 30 em 30 minutos; as probabilidades foram calibradas apenas em dados históricos independentes e **não** são previsões para os próximos 30 minutos nem garantias de lucro. Ações e ETFs não negoceiam de madrugada ou ao fim de semana.")
    t1,t2,t3=st.tabs(["↗️ Cinco maiores subidas","↘️ Cinco maiores descidas","📈 Variação dos 30 minutos"])
    with t1:
        rows=report.get("top_up",[])
        if rows:
            st.dataframe(_top_table(rows,"up"),use_container_width=True,hide_index=True)
        else:
            st.caption("Ainda não há modelos elegíveis que superem a referência.")
    with t2:
        rows=report.get("top_down",[])
        if rows:
            st.dataframe(_top_table(rows,"down"),use_container_width=True,hide_index=True)
        else:
            st.caption("Ainda não há modelos elegíveis que superem a referência.")
    with t3:
        assets=report.get("assets",[])
        movers=[]
        for x in assets:
            quote=x.get("quote")
            if not isinstance(quote,dict):
                continue
            age=quote.get("age_minutes")
            variation=quote.get("change_30m_pct")
            if (not isinstance(age,(float,int)) or age>90 or age<0 or
                    not isinstance(variation,(float,int))):
                continue
            movers.append({"Ativo":x.get("symbol"),"Mercado":x.get("market"),
                           "Variação 30min %":variation,
                           "Última vela UTC":quote.get("close_candle_start_utc")})
        if movers:
            mover_df=pd.DataFrame(movers).sort_values("Variação 30min %",ascending=False)
            st.dataframe(pd.concat([mover_df.head(5),mover_df.tail(5)]).drop_duplicates(subset="Ativo"),
                         use_container_width=True,hide_index=True)
            st.bar_chart(mover_df.head(10).set_index("Ativo")[["Variação 30min %"]])
        else:
            st.caption("Sem velas recentes. As bolsas podem estar fechadas ou o fornecedor indisponível.")
    with st.expander("Ver a tabela completa de todos os ativos"):
        rows=report.get("assets",[])
        if rows:
            st.dataframe(pd.DataFrame([{
                "Ativo":x.get("symbol"),
                "Mercado":x.get("market"),
                "Subida estimada 5d %":x.get("prob_up_pct"),
                "Descida estimada 5d %":x.get("prob_down_pct"),
                "Último preço":(x.get("quote") or {}).get("close"),
                "Variação da vela 30m %":(x.get("quote") or {}).get("change_30m_pct"),
                "Idade do preço (min)":(x.get("quote") or {}).get("age_minutes"),
                "Sinal experimental":x.get("signal"),
                "Modelo supera referência":x.get("better_than_baseline"),
            } for x in rows]),use_container_width=True,hide_index=True)
        else:
            st.caption("Não existem dados disponíveis.")
    st.markdown("#### Histórico recente do monitor")
    try:
        history=load_public_data("history.json")
        points=history.get("samples",[])
        if points:
            frame=pd.DataFrame(points)
            frame["Hora UTC"]=pd.to_datetime(frame["time_utc"],utc=True)
            frame=frame.set_index("Hora UTC")
            st.line_chart(frame[["buy_candidates","sell_if_held","recent_30m_quotes"]])
        else:
            st.caption("Histórico ainda vazio.")
    except (requests.RequestException,ValueError,TypeError,KeyError):
        st.caption("Histórico indisponível neste momento.")
    st.warning("Monitor apenas informativo. Os modelos podem não superar a referência e podem gerar sinais falsos. Não dá garantias de lucro, não executa ordens automáticas e não envia notificações push. O agendamento GitHub é aproximado, não um serviço com garantia 24/7.")
