"""Editorial comparison of established providers serving Portugal.

Sources were checked 2026-10-13. NOT a live fee quote or a regulatory
certification. Always verify legal entity, eligibility, tariffs and products.
No credentials, private APIs, withdrawals or order-placement functionality.
"""
CHECKED_ON = "2026-10-13"
PROVIDERS = [
    {
        "name": "Trading 212 Invest", "type": "Ações e ETFs", "api": "Sim — beta, demo e real", "api_ok": True,
        "fit": "Melhor ponto de partida para testar um bot de ações com conta demo",
        "trade": "0 € de comissão própria nas ações/ETFs Invest; impostos/encargos de bolsa à parte",
        "fx": "0,15% quando existe conversão EUR↔USD",
        "withdraw_eur": "0 € cobrado pela Trading 212; bancos podem cobrar",
        "withdraw_usd": "0 € cobrado pela Trading 212; conversão/intermediários podem cobrar",
        "regulation": "Trading 212 EU GmbH: BaFin (Alemanha), para contas portuguesas",
        "risks": "API beta apenas Invest; ordens apenas na moeda principal da conta; funções e limites podem mudar",
        "website": "https://www.trading212.com/pt", "fees": "https://www.trading212.com/pt/terms/invest",
        "api_docs": "https://docs.trading212.com/api/orders/orders",
        "regulator": "https://helpcentre.trading212.com/hc/en-us/articles/12933782261917-What-are-the-supported-countries",
        "fee_model": "fx_only", "trade_rate": 0.0, "fx_rate": 0.0015, "fee_fixed": 0.0
    },
    {
        "name": "Interactive Brokers", "type": "Ações e ETFs", "api": "Sim — Web/TWS API", "api_ok": True,
        "fit": "Melhor infraestrutura técnica para automação mais avançada",
        "trade": "GlobalTrader: ações EUA a partir de 1 USD/ordem; Europa tipicamente 3 EUR/ordem. Depende do plano/bolsa",
        "fx": "GlobalTrader: conversão automática ~0,03% (3 pontos base); outros planos diferem",
        "withdraw_eur": "GlobalTrader: 1 levantamento SEPA/mês grátis; seguintes 1 EUR (outros planos podem diferir)",
        "withdraw_usd": "O método USD, país, banco e tabela de preços determinam taxa; consultar preçário",
        "regulation": "Interactive Brokers Ireland: Banco Central da Irlanda",
        "risks": "Autenticação/API mais complexas; mínimos por ordem pesam numa carteira de 50 EUR",
        "website": "https://www.interactivebrokers.ie", "fees": "https://www.interactivebrokers.ie/en/trading/globaltrader/pricing-ie.php",
        "api_docs": "https://www.interactivebrokers.com/docs/web-api/v1/endpoints/orders/place-order",
        "regulator": "https://www.interactivebrokers.ie/en/general/disclaimers.php",
        "fee_model": "variable", "trade_rate": None, "fx_rate": None, "fee_fixed": None
    },
    {
        "name": "Kraken Pro", "type": "Criptomoedas", "api": "Sim — API oficial", "api_ok": True,
        "fit": "Primeira candidata para investigar trading spot automático de criptomoedas",
        "trade": "Escalão inicial spot: maker 0,40% / taker 0,80% (tabela alterada em 2026)",
        "fx": "Depende do par; EUR/USD e stablecoins têm tabelas próprias; usar pares EUR quando possível",
        "withdraw_eur": "SEPA: habitualmente 0,90–1 EUR por levantamento, conforme método",
        "withdraw_usd": "Depende do método SWIFT/país e mínimos; confirmar na conta",
        "regulation": "Prestadores de criptoativos licenciados MiCA pelo Banco Central da Irlanda",
        "risks": "Taxas, spread, limites de mínimos, cripto disponível e levantamentos variam por par/país",
        "website": "https://www.kraken.com/pt", "fees": "https://www.kraken.com/pt/features/fee-schedule",
        "api_docs": "https://docs.kraken.com/api/docs/rest-api/add-order",
        "regulator": "https://support.kraken.com/pt/articles/where-is-kraken-licensed-or-regulated",
        "fee_model": "variable", "trade_rate": None, "fx_rate": None, "fee_fixed": None
    },
    {
        "name": "Coinbase Advanced", "type": "Criptomoedas", "api": "Sim — Advanced Trade API", "api_ok": True,
        "fit": "Alternativa com API para trading cripto; comparar preços na própria conta",
        "trade": "Maker/taker conforme escalão e par; consultar taxas mostradas antes da ordem",
        "fx": "Depende do par de trading e conversões aplicadas",
        "withdraw_eur": "Consultar custos do levantamento SEPA no perfil e pré-visualização",
        "withdraw_usd": "Consultar método disponível em Portugal e custos apresentados",
        "regulation": "Coinbase Luxembourg S.A.: licença MiCA da CSSF (Luxemburgo)",
        "risks": "Não confundir preçário Coinbase Exchange institucional com Advanced de retalho",
        "website": "https://www.coinbase.com/advanced-trade",
        "fees": "https://help.coinbase.com/en-gb/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees",
        "api_docs": "https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/sdk",
        "regulator": "https://www.coinbase.com/pt-pt/legal/licenses/europe",
        "fee_model": "variable", "trade_rate": None, "fx_rate": None, "fee_fixed": None
    },
    {
        "name": "XTB", "type": "Ações e ETFs", "api": "Não — API descontinuada em 2025", "api_ok": False,
        "fit": "Boa opção para investimento manual; não serve para integrar este bot via API",
        "trade": "Ações/ETFs sem comissão até 100 000 EUR de volume mensal; depois 0,2% (mín. 10 EUR)",
        "fx": "0,5% por conversão de moeda aplicável às transações",
        "withdraw_eur": "0 EUR, segundo condições portuguesas",
        "withdraw_usd": "Confirmar disponibilidade; eventual conversão/intermediários",
        "regulation": "Sucursal em Portugal registada na CMVM",
        "risks": "API oficial foi descontinuada em 14/03/2025",
        "website": "https://www.xtb.com/pt", "fees": "https://www.xtb.com/pt/conta-e-taxas",
        "api_docs": "https://www.xtb.com/pt/centro-de-ajuda/nossas-plataformas/a-xtb-oferece-ferramentas-de-automatizacao-de-investimentos",
        "regulator": "https://acoes.xtb.com/investir-em-acoes-sem-comissao",
        "fee_model": "fx_only", "trade_rate": 0.0, "fx_rate": 0.005, "fee_fixed": 0.0
    },
    {
        "name": "DEGIRO", "type": "Ações e ETFs", "api": "Não — sem API oficial", "api_ok": False,
        "fit": "Corretora para negociação manual, não para ligação automática",
        "trade": "Ações EUA e Lisboa: 1 EUR de comissão + 1 EUR de manuseamento por ordem",
        "fx": "Conversão de moeda AutoFX 0,25%; conetividade pode acrescer",
        "withdraw_eur": "0 EUR cobrado pela DEGIRO",
        "withdraw_usd": "Em geral é necessário converter saldo para EUR e levantar à conta bancária associada",
        "regulation": "Grupo flatexDEGIRO, instituição europeia regulada; verificar entidade contratual",
        "risks": "Custos fixos altos para ordens de 50 EUR; API não disponível",
        "website": "https://www.degiro.pt", "fees": "https://www.degiro.pt/precario",
        "api_docs": "https://www.degiro.pt/helpdesk/pt-pt/plataforma-de-negociacao/utilizando-plataforma-de-negociacao/degiro-dispoe-de-uma-api",
        "regulator": "https://www.degiro.pt/precario",
        "fee_model": "fixed_fx", "trade_rate": 0.0, "fx_rate": 0.0025, "fee_fixed": 2.0
    },
]

def preview_roundtrip_eur(provider, amount_eur=50.0, asset_currency="USD"):
    """Illustrative EUR-account buy & sell of EUR- or USD-quoted stocks at unchanged price.
    Excludes spreads, slippage, taxes, rebates, and third-party/withdrawal fees.
    Only compare providers with explicitly supported simple fee models.
    """
    if asset_currency not in ("EUR", "USD"):
        raise ValueError("Moeda inválida")
    if not 0 < amount_eur <= 1_000_000:
        raise ValueError("Montante inválido")
    if provider["type"] != "Ações e ETFs" or provider["fee_model"] == "variable":
        return None
    fx = provider["fx_rate"] if asset_currency == "USD" else 0
    return round(2 * (amount_eur * fx + amount_eur * provider["trade_rate"] + provider["fee_fixed"]), 2)

def comparable_stock_costs(amount_eur=50.0, asset_currency="USD"):
    pairs = [(p["name"], preview_roundtrip_eur(p, amount_eur, asset_currency))
             for p in PROVIDERS if p["type"] == "Ações e ETFs"]
    return sorted(((name, value) for name, value in pairs if value is not None), key=lambda x:x[1])
