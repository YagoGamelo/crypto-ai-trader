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


## Trading 212 — ligação DEMO segura

A aba **🔐 Trading 212 DEMO** usa exclusivamente
`https://demo.trading212.com/api/v0`. O projeto **não contém o host de negociação
real**, não recebe códigos no formulário e nunca envia ordens reais.
A Trading 212 Public API v0 está em versão beta e aplica-se às contas Invest
e Stocks ISA elegíveis. A conta DEMO da Trading 212 não é a mesma coisa que
a carteira virtual isolada de 50 USD criada pelo nosso próprio site.

### Preparar as credenciais

1. Cria/abre a conta de **demonstração / Practice** na Trading 212 e seleciona
   uma conta Invest elegível.
2. Na Trading 212: **Settings → API (Beta) → Generate API key**.
3. Para testar primeiro, concede só permissões para **account/portfolio/positions**;
   posteriormente, se quiseres testar ordens DEMO, cria credenciais apropriadas
   com permissão para ordens da **conta DEMO**.
4. Na gestão do serviço no **Render → Environment**, adiciona as variáveis abaixo.
   Guarda cada variável como segredo privado (nunca faças commit num ficheiro
   público, nunca envies estas chaves no chat):
   - `T212_DEMO_API_KEY`: API Key DEMO
   - `T212_DEMO_API_SECRET`: API Secret DEMO (mostrada uma única vez)
   - `T212_PANEL_PASSWORD`: palavra-passe *nova, forte e única*, com **pelo menos 16 caracteres**, para a aba privada do site
   - `T212_ENABLE_DEMO_ORDERS`: por defeito **não configures**. Opcionalmente,
     apenas quando estiveres pronto para testes DEMO explícitos, define
     `YES_I_UNDERSTAND_DEMO_ONLY`.
5. Reinicia/publica o serviço e abre a aba **Trading 212 DEMO**. Introduz apenas
   a palavra-passe do painel (não a API Key) para aceder à secção privada.
6. Clica **Consultar saldo**; confirma que a conta apresentada é a conta demo.
   De seguida consulta posições e ordens pendentes. Instrumentos disponíveis
   devem ser carregados a partir da API oficial (os símbolos do radar Yahoo
   Finance não coincidem necessariamente com os tickers oficiais Trading 212).

Em Codespaces, podes usar **Streamlit Secrets** ou variáveis de ambiente do
Codespaces, sem os adicionares ao repositório; usa os mesmos nomes acima.

### Ordens DEMO (opcionais e manuais)

- Por defeito, ordens estão **desativadas**.
- Para ativar apenas DEMO, precisas de permitir ordens na API Key da conta demo
  e definir a variável de autorização exatamente como acima.
- O painel permite **uma ordem limite DEMO por clique explícito**, com confirmação
  textual `CONFIRMAR DEMO`, máximo de **10 unidades da moeda da conta** por
  ordem, uma tentativa por minuto na sessão e apenas instrumentos com moeda
  idêntica à da conta. As vendas são limitadas à posição disponível.
- A ordem DEMO pode ficar pendente durante o fecho do mercado; consulta o estado
  na conta Trading 212.
- **Não repitas automaticamente uma ordem após um erro de rede**: este endpoint
  da API não é idempotente e pode criar ordens duplicadas.
- O projeto não executa trading autónomo na API da Trading 212, não contém
  levantamento ou transferência, nem dispõe de integração real de 50 EUR.

### Segurança numa publicação pública

- Não permitas que terceiros conheçam a palavra-passe da aba. Por ser um
  protótipo Streamlit, esta autenticação de ecrã não substitui autenticação
  robusta, separação de utilizadores, auditoria e rate limits a nível de servidor.
- Antes de expor uma API com permissão para **ordens DEMO** a terceiros, protege
  o acesso ao site com um proxy de identidade (por exemplo, Render/Cloudflare
  Access) e prefere credenciais **apenas de leitura** enquanto isso.
- **Nunca cries credenciais de API de dinheiro real para este serviço**.
- Se uma chave for exposta, revoga-a imediatamente na Trading 212 e emite nova.

Fontes oficiais:
- Documentação: https://docs.trading212.com/api
- Como gerar chaves e gerir permissões:
  https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-How-can-I-generate-an-API-key
- Ordens limite: https://docs.trading212.com/api/orders/placelimitorder
