# NEXUS / Crypto AI Trader — pesquisa e simulação

Projeto educativo para iPad, GitHub Codespaces, Render e Streamlit. **Não negocia dinheiro real**, não recebe chaves de corretoras nem autoriza levantamentos.

## Site

Separadores:
1. **Top 5:** analisa até 170 ativos (50 cripto, 100 ações, 20 ETFs) com dados públicos; ordena as estimativas de subida para cinco dias apenas entre modelos cujo Brier de teste supera uma previsão de referência. Não corrige seleção múltipla nem calibra probabilidades: **não usar para colocar ordens reais**.
2. **Explorar ativo:** gráfico de velas, médias móveis e estudo estatístico a 1, 5 e 20 dias.
3. **Trading virtual:** um ciclo por clique, BTC/USD ou ETH/USD, carteira local **privada por sessão do navegador** e por símbolo; saldo inicial nominal de 50 USD. Reserva 30% do lucro líquido realizado sem reinvestir; não reserva quando há perdas. Compras virtuais bloqueadas quando o teste Brier não supera a referência.
4. **Metodologia:** limitações e origem dos dados.
5. **Corretoras & APIs:** comparação orientada a residentes em Portugal com taxas de negociação, câmbio, levantamentos EUR e USD, requisitos de API, regulamentação, sites oficiais e exemplo de custos em ações USD. Pesquisa verificada em 13-10-2026 no ficheiro `brokers.py`.

## Arranque

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py --server.address 0.0.0.0
```

Abre a porta 8501 no Codespaces, mantendo-a **privada**. Em Render, o comando de arranque é:

```bash
python -m streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

Os testes de sintaxe e unitários também têm uma verificação GitHub Actions em `.github/workflows/tests.yml`.

## Funcionamento e limitações técnicas

- Dados de mercado: `yfinance` para radar e análise; dados públicos OHLCV da Kraken via `ccxt` no trading virtual. Verifica a licença/termos da fonte antes de oferecer um serviço público.
- Modelos: regressão logística, features de histórico, validação cronológica em 30% final com separação/embargo no treino.
- **Probabilidades não calibradas.** Probabilidade de subir não equivale a probabilidade de um trade com lucro após comissões; ranking Top 5 entre muitos ativos introduz viés de seleção.
- O programa não recolhe automaticamente notícias, recomendações profissionais nem vídeos. Não inventa essas fontes.
- A carteira virtual é mantida apenas em memória do Streamlit por sessão e perde-se quando a sessão terminar. Não é partilhada entre visitantes e não serve como histórico duradouro.
- Os controlos de stop-loss só são avaliados no clique, **não de forma permanente**. Os preços, o slippage, impostos e spreads reais diferem da simulação.
- `brokers.py` não usa APIs privadas, não contém credenciais e não estabelece ligações a corretoras. Taxas e disponibilidade podem mudar. Abrir conta está sujeito a elegibilidade e supervisão específicas.
- As opções binárias com pagamento fixo têm limitações/restrições regulamentares para retalho na UE; não há integração binária.
- Alojamento gratuito no Render pode suspender; **nenhum robô automático 24/7 está implementado**.
- Nunca adicionar segredos ao GitHub nem publicar o painel de um dia para o outro com permissões de negociação reais sem autenticação e controlos específicos.

## Antes de considerar trading real

Calibração e backtesting walk-forward sem look-ahead, custos reais por mercado, fonte de dados licenciada e fiável, persistência isolada, autenticação de utilizadores, reconciliação de ordens, limites de risco, botão de emergência, sandbox e aprovação humana. Se forem concedidas permissões API, **desativar levantamentos** e manter a chave apenas em armazenamento secreto do servidor. Os serviços de corretagem devem ser disponibilizados pelo próprio intermediário autorizado.

Consulta a aba Corretoras & APIs para enlaces aos documentos oficiais. Não é aconselhamento de investimento ou parecer jurídico.
