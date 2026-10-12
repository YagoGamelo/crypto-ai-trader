# Crypto AI Trader — PAPER ONLY

Protótipo educativo de trading automático **simulado**, desenvolvido para abrir no iPad através de GitHub Codespaces e Streamlit. Não usa chaves de exchange nem envia ordens reais.

## Iniciar no iPad

1. No GitHub, abre este repositório → **Code** → **Codespaces** → **Create codespace**.
2. No terminal do Codespaces:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py --server.address 0.0.0.0
   ```
3. No separador **Ports**, abre a porta 8501; mantém-na privada.
4. Escolhe BTC/USD ou ETH/USD, ativa operações virtuais e carrega no botão de análise.

## Funcionamento

- Obtém velas públicas de 1h da Kraken, sem vela em formação.
- Treina regressão logística com indicadores de preços e volume.
- Mede Brier score e sinais >=70% em 30% finais dos dados, separados cronologicamente.
- Simula compra quando probabilidade >=70%, até 20% da carteira por entrada, com stop 3%, objetivo 6% e taxa simulada 0,2% por ordem.
- Regista trades em SQLite local. BTC e ETH usam carteiras virtuais separadas, de **50 unidades nominais** cada.
- Executa apenas **um ciclo por clique**; Codespaces não é um robô 24/7.

## Avisos e limitações

- O saldo nominal é calculado com preços em USD, **não convertido para EUR**. Não interpretar como 50 € reais.
- Probabilidades **não estão calibradas**: uma previsão de 70% não garante 70% de sucesso.
- Não há validação walk-forward completa, comparação com buy-and-hold, spreads reais, slippage, impostos ou conversão cambial.
- Stop-loss só é verificado quando o utilizador carrega no botão; não é proteção contínua.
- A base SQLite local pode perder-se se o Codespace for apagado.
- **Sem depósitos, sem API keys, sem ordens reais e sem alavancagem.**

## Testes

```bash
pytest -q
```

Próximas fases: calibrar probabilidades, walk-forward, simulação realista e serviço persistente para paper trading agendado. Só depois considerar integração real, com aprovação explícita e controlos de segurança.
