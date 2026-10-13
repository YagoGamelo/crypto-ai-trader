# NEXUS / Crypto AI Trader — pesquisa e simulação


## Versão 4 — procurar vantagem líquida, não perseguir lucros

**Meta de estudo: +400% num ano.** Com capital inicial de 50 unidades,
seriam 250 unidades no fim (200 de lucro): cerca de +14,35% composto ao
mês. **Não existe uma combinação conhecida que torne +400% provável e,
ao mesmo tempo, de baixo risco.** É perfeitamente possível perder o
capital. Nenhuma probabilidade de atingir esta meta é inferida da IA.

Por isso, a meta continua a ser apenas uma referência no separador
`🎯 Meta 400%`. Não foi acrescentada alavancagem nem acesso a
corretoras reais, nem são aumentadas as posições para recuperar perdas.

### Alterações ao motor de decisão

- **`edge_filter.py`** estima uma margem de vantagem de uma operação
  com as magnitudes médias das subidas e descidas do bloco de teste,
  o custo suposto de compra+venda e a probabilidade mais recente.
  Reduz a probabilidade favorável em pelo menos **8 pontos percentuais**
  ou no erro de calibração medido (o que for maior), para construir
  uma expectativa líquida conservadora.
- **`research_v2.py`** exige 12 sinais de subida >=70% no bloco
  histórico de teste, dos quais pelo menos **8 períodos sem sobreposição
  de resultados**, acerto observado e um limite inferior aproximado
  de confiança (>50%) calculado com a fórmula de Wilson, além dos
  filtros existentes de Brier, ECE e rentabilidade média após custos.
  Os testes não asseguram independência estatística de regimes de
  mercado nem lucro futuro; não corrigem seleção múltipla entre ativos.
- **A entrada virtual é bloqueada** se faltar qualquer indicador de
  aprovação, se não houver vantagem líquida conservadora positiva ou
  se uma fonte não fornecer dados. **Nenhum sinal também é um resultado
  válido.** P(subida) ≥70% é condição necessária, mas não suficiente.
- Entre duas ações que passaram os filtros, **`auto_paper.py`**
  prefere a maior vantagem líquida conservadora por unidade de
  volatilidade ATR, em vez de selecionar automaticamente a
  probabilidade mais alta. Esta métrica de prioridade é uma heurística
  de investigação e **não está provada como melhor**.
- Compra/venda virtuais agora acrescentam **0,1% de derrapagem
  desfavorável por lado** além da comissão, mas continuam a usar
  preços de fecho como referência. São preenchimentos inventados
  para contabilizar custos e não equivalem à abertura real seguinte.
- Após vender uma ação existe uma pausa de pelo menos **dois dias
  de calendário** para esse símbolo, para reduzir operações repetidas.
  Preços diários com mais de **quatro dias** ficam inelegíveis.
- **`walkforward.py`** passou a usar o mesmo pressuposto de custos na
  validação do sinal, recusa vantagens líquidas negativas, introduz
  cooldown e bloqueia novas compras depois de -15% do máximo
  observado. As saídas continuam permitidas.
- **`strategy_scorecard.py`** deixa claro se um backtest isolado
  satisfaz critérios mínimos para **mais estudo**: 252 sessões fora da
  amostra, pelo menos 30 vendas concluídas, lucro líquido positivo e
  maior queda da carteira não inferior a -15%. Mesmo quando todos
  passam, **o resultado não valida +400% nem autoriza operações reais**.

### O que o site passa a mostrar

Em **🏆 Top 5** há agora duas perspetivas: probabilidade estimada
de subida, e os candidatos que também têm vantagem líquida positiva
depois de uma margem conservadora e que passaram os filtros históricos.
Em **📈 Explorar ativo**, após um backtest, o site mostra o resultado
da auditoria da amostra e das perdas. A aba **🎯 Meta 400%** recupera
o último backtest disponível na sessão e indica se há sequer amostra
suficiente para continuar a investigar.

**Ponto de risco:** a confiança de Wilson é apenas uma aproximação,
e as observações selecionadas continuam dependentes de fatores comuns
do mercado; as comissões reais, dividendos, impostos, movimentos
intradiários, liquidez, câmbio e gaps podem alterar radicalmente o
resultado. Estes filtros podem causar semanas ou meses sem compras.
Isso é preferível a apresentar falsas garantias.

### Testes

Foram acrescentados testes unitários em
`tests/test_edge_filter.py`, `tests/test_strategy_scorecard.py`,
`tests/test_auto_paper.py` e `tests/test_walkforward.py`.
O GitHub Actions executa `python -m pytest -q` a cada atualização
da branch `main`. A existência dos testes **não prova que passaram**
ou que a estratégia seja rentável; verificar sempre o estado do
workflow em `Actions → Tests and syntax`.


## Criptomoedas, memecoins e opções — módulos de estudo

### Cripto spot e memecoins

O catálogo foi expandido com **15 novas memecoins** (além da Dogecoin, que já existia), totalizando até
**185 ativos de investigação** (65 criptomoedas, 100 ações e 20 ETFs).
Uma moeda no catálogo **NÃO** significa que esteja disponível para
negociação na Kraken nem que tenha dados históricos suficientes.

A aba **🪙 Cripto e Memecoins** consulta apenas preços públicos do mercado
**spot USD** da Kraken via `ccxt`, usando velas completas de 30 minutos,
1 hora ou 4 horas. O modelo `research_v2.py` avalia as **próximas quatro
velas** (por exemplo, **2 horas** quando cada vela tem 30 minutos), com
treino, calibração e teste em períodos distintos. Este sinal cripto NÃO
é igual às estimativas de subida nos cinco dias das ações.

- **Entradas virtuais:** subida prevista ≥70%, desempenho histórico
  aprovado, cotação recente, mínimo de volume negociado em 24 horas e
  spread observado compatível com o mercado. Sem spread, sem histórico ou
  com mercado indisponível, **não há compra**.
- **Saídas virtuais:** descida prevista ≥70%; subida ≤50%; stop móvel
  adaptativo; stop de perda; tempo máximo de observação. Uma descida
  prevista de 70% só encerra uma posição **existente**; nunca abre short.
- **Ações por clique** ou tentativa de reavaliação a cada meia hora
  enquanto a sessão Streamlit estiver aberta e o alojamento ativo.
  **Não é um serviço de trading contínuo 24/7.**
- **Mercados maiores:** investimento máximo de 20% do valor livre numa
  entrada; risco hipotético de 1% da carteira.
- **Memecoins:** máximo de 10% numa entrada e 0,5% de risco inicial
  planeado; volume de referência ≥500 mil USD nas últimas 24h,
  spread observado ≤1,5% e bloqueio em variações extremamente violentas.
  São estimativas imperfeitas: volume de negociação NÃO equivale à
  liquidez do livro de ordens.
- **Custos simulados por operação completa**: 1,4% nas criptomoedas
  maiores e 2,8% nas memecoins (comissões e derrapagem assumidas).
  A Kraken pode cobrar valores reais diferentes por par e escalão.
- **A carteira é virtual e separada por sessão**, começa com 50 unidades
  USD nominais e não pode ser vinculada à API da Trading 212 nem a uma
  conta de exchange real. Não disponibiliza levantamentos.

Os preços e os modelos podem tornar-se desatualizados; quando não há
confirmação do par spot e indicadores de liquidez, o sistema falha sem
comprar. O utilizador precisa de selecionar o ativo que quer observar;
a carteira virtual não faz varrimento autónomo de todas as moedas em
segundo plano.

### CALL e PUT — gráfico ilustrativo de lucro/prejuízo

Na aba **📉 Opções Call/Put** é possível ajustar o preço do ativo
subjacente, strike, prémio pago, multiplicador, quantidade de contratos,
comissões e uma data de expiração **meramente indicativa**.

O ficheiro `options_payoff.py` mostra **apenas na expiração**:

- **Compra de Call:** lucro líquido =
  `max(0, preço_final - strike) × unidades - prémio_total - comissões`.
  Break-even = strike + custo por unidade. A perda máxima teórica é
  o débito pago; o lucro máximo teórico não tem limite superior.
- **Compra de Put:** lucro líquido =
  `max(0, strike - preço_final) × unidades - prémio_total - comissões`.
  Break-even = strike − custo por unidade. A perda máxima teórica é
  o débito pago; o lucro máximo ocorre teoricamente com preço final
  zero e é limitado.
- A linha do gráfico **não** inclui valor temporal da opção antes da
  expiração, volatilidade implícita, dividendos, FX, conversão de
  moeda, regras de exercício nem possíveis comissões adicionais.
  Por isso **não é uma cotação da corretora** e não prevê a evolução
  real do prémio.
- **NÃO** há venda de opções descobertas, ordens de derivados, opções
  binárias, margem ou alavancagem. Estes contratos NÃO são executados
  pela Trading 212 API do projeto.

**Aviso importante:** 70% de hipótese de subida de um ativo não é
70% de hipótese de lucro numa Call; também é necessário ultrapassar
o strike, o prémio e os custos *antes do prazo escolhido*.

Antes de qualquer integração real, seria necessário contratar dados
de opções autorizados, verificar acesso regulamentar aos instrumentos,
confirmar condições de corretagem e testar exaustivamente as ordens.


## Meta anual de +400% — painel de objetivos, não uma promessa

**Uma rentabilidade de +400%** corresponde a multiplicar o capital por
cinco: por exemplo, **50 € → 250 €**, ou +200 € de lucro, antes de
impostos e custos adicionais. O crescimento composto necessário em 12
meses é aproximadamente **14,35% ao mês**, todos os meses. Isso é uma
meta extremamente agressiva, não a expectativa de rentabilidade do bot.

Foi adicionada a aba **🎯 Meta 400%**, suportada por `goal_planner.py`.
Ela apresenta:
- o valor necessário para cumprir a meta e o progresso **real** da
  carteira de simulação de ações (saldo virtual expresso em **USD
  nominais**, não convertido para EUR);
- a taxa composta mensal exigida para um prazo entre 6 e 36 meses;
- trajetórias aritméticas hipotéticas de +5%, −5% e do crescimento
  necessário para a meta, **sem extrapolar o rendimento da IA**;
- estatísticas de operações virtualmente fechadas: lucro realizado,
  número de trades e taxa de acerto. Com menos de 30 vendas o painel
  avisa que a amostra ainda é demasiado pequena.

Esta atualização **não aumentou a alavancagem nem os limites de risco**,
nem alterou a compra acima dos 70% e saída aos 50% ou descida de 70%.
A única forma responsável de decidir se vale a pena alterar a estratégia
é demonstrar melhores resultados posteriores aos custos em teste
independente. O objetivo não deve levar o bot a assumir perdas
ilimitadas, negociar com empréstimos ou tentar recuperar prejuízos
aumentando automaticamente as posições.

### Custos mais altos podem eliminar ganhos

O botão de backtest em **📈 Explorar ativo** agora oferece três
cenários ilustrativos de execução, todos **por lado da operação**:

| Cenário | Comissão | Derrapagem de preço |
| --- | ---: | ---: |
| Base | 0,2% | 0,1% |
| Custos superiores | 0,4% | 0,3% |
| Custos extremos | 0,8% | 0,5% |

`walkforward.py` usa estas condições tanto nas compras/vendas como
na comparação comprar-e-manter, pelo mesmo período histórico.
A estratégia **não usa os resultados do teste para otimizar
automaticamente os limiares**. Um bom resultado histórico não prova
rentabilidade futura, e um único ativo não representa o portfólio de
185 ativos. Impostos, dividendos, câmbio e outras fricções não foram
incluídos.

Para testar depois de fazer `git pull` no Codespaces:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py --server.address 0.0.0.0
```


## Versão 3 — qualidade do sinal + disciplina de risco

Esta versão foi implementada para **reduzir entradas sem evidência**, melhorar
a compreensão das perdas e evitar simulações excessivamente otimistas.
**Não é possível programar lucros máximos garantidos.**

### 1. Modelo único para radar e gráficos

`research_v2.py` passou a ser o motor comum do `Top 5` e de
`Explorar ativo` (`asset_analysis.py`):

- Usa indicadores com dados **anteriores à previsão**: retornos, média
  móvel de 20 e 50 sessões e volatilidade de 20 sessões.
- Para testar a previsão de subida em **cinco velas diárias**, divide o
  histórico em 55% treino / 20% calibração / 25% teste, com intervalo de
  separação (*embargo*) de cinco sessões entre conjuntos. Isto evita
  sobreposição direta de rótulos.
- Ajusta as probabilidades no período de calibração e mede a qualidade
  exclusivamente num teste posterior, através de Brier, baseline, erro
  de calibração (ECE), amostras e acerto das previsões ≥70%.
- Reajusta treino/calibração cronologicamente para a estimativa mais
  recente, **sem usar o futuro**.
- Descarta por prudência a vela diária de hoje, que pode ainda estar
  em formação; alguns mercados podem apresentar um dia adicional de
  atraso.

A decisão de **comprar virtualmente** requer tudo o seguinte:

1. estimativa de subida ≥70%;
2. Brier inferior à referência por pelo menos 0,005;
3. erro de calibração no teste ≤12 pontos percentuais;
4. pelo menos oito previsões históricas com ≥70% de subida no teste;
5. pelo menos 60% de acerto nesse pequeno grupo histórico;
6. rendimento médio histórico dos sinais ≥70% positivo **depois de uma dedução teórica de 0,6%** por compra e venda (comissão de 0,2% e derrapagem de 0,1% por lado).

Estas exigências **não garantem** acerto futuro de 70%, significância
estatística ou lucro líquido. São travões de segurança preliminares,
não uma certificação da IA. Se ninguém cumprir, a IA **não compra**.
O Top 5 pode mostrar ativos interessantes que **não foram aprovados
para operações virtuais**.

### 2. Carteira virtual de ações

O `auto_paper.py` continua em simulação isolada por sessão e
mantém os limiares escolhidos:

- **Compra:** sinal calibrado ≥70% com critérios de qualidade aprovados.
- **Venda:** 70% ou mais de descida estimada, ou subida ≤50%,
  apenas de ações efetivamente detidas. Não abre *shorts*.
- **Saída de segurança:** stop por volatilidade = duas vezes o ATR de
  14 dias, limitado a 3–8% (5% na ausência de ATR). Stop móvel armado
  depois de +4% ou 1,5 ATR; permite um recuo de 3% ou um ATR do máximo
  observado. Estes são controlos avaliados no **fecho diário**, não
  ordens stop executadas pela corretora.
- **Quantidade por entrada:** até 20% do capital investível e orçamento
  equivalente a aproximadamente 1% de risco inicial da carteira se
  o stop hipotético for respeitado (a volatilidade e gaps podem causar
  perdas maiores).
- **Proteção da carteira:** até 3 ações abertas; uma entrada nova por
  ciclo; bloqueio de novas compras depois de uma queda diária de 5%
  ou total de 15% desde o máximo observado na sessão; 30% dos lucros
  líquidos realizados vão para reserva virtual.
- O histórico e os limites não sobrevivem ao fecho/reinício da sessão
  Streamlit. **Não é adequado para trading real 24 horas por dia.**

### 3. Backtest *walk-forward* por ativo

No separador **📈 Explorar ativo**, seleciona uma empresa e carrega em
**Executar backtest do ativo selecionado**. O ficheiro `walkforward.py`
reproduz o percurso histórico sem usar dados futuros em cada decisão:

- Refaz a previsão periodicamente utilizando apenas cotações até à
  **sessão anterior** à operação simulada.
- Compra e vende virtualmente na **abertura seguinte**, acrescentando
  0,2% de comissão simulada por lado e 0,1% de derrapagem por lado.
- Mede retorno, máxima queda observada (*drawdown*), transações
  fechadas, taxas totais, exposição e retorno de uma estratégia
  comparável de comprar e manter.
- Simulação **de um único ativo**, não uma simulação integral da
  escolha diária dos melhores entre os 185. Não inclui dividendos,
  impostos, câmbio, falta de liquidez, execução parcial nem todas as
  fricções da bolsa. Pode produzir **zero operações**. O retorno
  anualizado, quando mostrado, é apenas uma transformação matemática
  da amostra, **não uma previsão de lucro anual**.

### 4. Execução e ligação a corretoras

`trading212_demo.py` continua **exclusivamente DEMO**, sem host
de trading real. O monitor GitHub Actions atualiza o relatório público
de forma agendada, não opera posições. O Render Free e o Codespaces
podem suspender e não garantem tarefas automáticas 24/7.

A fonte Yahoo Finance/`yfinance` limita a utilização de dados a
contextos pessoais/de investigação, dependendo das condições
específicas. Para uso público/comercial ou ordens reais, é
indispensável licenciamento de dados, um servidor persistente,
autenticação forte, reconciliação de ordens, auditoria, recuperação
de falhas e validação estatística independente.

### Testar

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py --server.address 0.0.0.0
```

O workflow `.github/workflows/tests.yml` testa sintaxe e cenários
sem contacto com corretoras. Não confundir testes unitários aprovados
com uma estratégia financeiramente rentável.


Projeto educativo para iPad, GitHub Codespaces, Render e Streamlit. **Não negocia dinheiro real**, não recebe chaves de corretoras nem autoriza levantamentos.

## Site

Separadores:
1. **Top 5:** analisa até 185 ativos (65 cripto (incluindo 16 memecoins, contando DOGE), 100 ações, 20 ETFs) com dados públicos; ordena as estimativas de subida para cinco dias apenas entre modelos cujo Brier de teste supera uma previsão de referência. Não corrige seleção múltipla nem calibra probabilidades: **não usar para colocar ordens reais**.
2. **Explorar ativo:** gráfico de velas, médias móveis e estudo estatístico a 1, 5 e 20 dias.
3. **Auto-trading virtual:** pesquisa automaticamente as 100 ações do catálogo de hora a hora enquanto a sessão Streamlit estiver aberta, compra virtualmente quando o modelo estima ≥70% de subida em cinco dias e vende quando essa estimativa cai para ≤50% (ou ao atingir o stop diário de 5%). Não executa operações reais.
4. **Trading virtual:** um ciclo por clique, BTC/USD ou ETH/USD, carteira local **privada por sessão do navegador** e por símbolo; saldo inicial nominal de 50 USD. Reserva 30% do lucro líquido realizado sem reinvestir; não reserva quando há perdas. Compras virtuais bloqueadas quando o teste Brier não supera a referência.
5. **Metodologia:** limitações e origem dos dados.
6. **Corretoras & APIs:** comparação orientada a residentes em Portugal com taxas de negociação, câmbio, levantamentos EUR e USD, requisitos de API, regulamentação, sites oficiais e exemplo de custos em ações USD. Pesquisa verificada em 13-10-2026 no ficheiro `brokers.py`.

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

## IA 70/70/50 — motor automático virtual de ações

A aba **🤖 Auto-trading virtual** usa a mesma tabela de previsões da
pesquisa `top5_research.scan_all(categories=("Ações",))`, para as ações
com dados históricos suficientes. Uma previsão é uma estimativa *não
calibrada*, não uma garantia.

- **COMPRAR** uma ação candidata quando P(subida em 5 dias) ≥ 70% **e**
  o Brier da janela de teste for inferior ao da referência histórica, com
  no mínimo 30 exemplos no teste.
- **VENDER uma posição existente** quando P(descida) ≥ 70% (equivale a
  P(subida) ≤ 30%), ou quando P(subida) ≤ 50%.
- Também fecha virtualmente em **stop de perda de 5%** ou num **stop móvel
  de 3% de recuo relativamente ao máximo observado**, mas só depois de
  uma subida observada de pelo menos 4% desde a entrada.
- **Nunca abre posições short**. Não compra ou vende se não houver dados
  válidos recentes ou se o preço estiver desatualizado. O motor só
  opera ações, não ETFs ou criptomoedas, nesta fase.
- **Risco:** carteira inicial virtual de 50 USD, até 20% de cada compra,
  3 posições simultâneas, 1 nova compra por ciclo, taxas simuladas
  de 0,2% por compra e venda; reserva 30% de lucros líquidos realizados;
  bloqueia novas compras após queda de 5% relativamente ao valor
  de referência diário.
- **Periodicidade:** uma tentativa de análise aproximadamente de
  hora a hora **apenas enquanto a página e sessão estão abertas e a
  opção de trading virtual está ativa**; também há botão de análise
  manual, que não executa ordens quando a autorização está desligada.
  Cada símbolo só executa decisões em novos fechos diários. Render Free
  e Codespaces podem adormecer; isto não é serviço 24/7.
- O motor mantém a sua carteira **apenas em memória na sessão atual**;
  os resultados desaparecem quando a sessão termina. Não envia nenhuma
  operação à Trading 212, sequer à demo: é um livro-razão interno.

**Importante:** os lucros anuais, a taxa real de acerto e a
qualidade preditiva ainda não foram demonstrados com backtests
walk-forward rigorosos, liquidez e custos reais. O stop móvel não
identifica o topo do preço e não oferece proteção contínua.

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

## Regras 70/50 para ações (simulação, outubro de 2026)

Na aba **🤖 Auto-trading virtual**:
- **COMPRAR** uma ação ao preço do último fecho disponível quando a estimativa de subida para os próximos cinco dias for **≥70%** e o Brier fora da amostra superar a previsão de referência.
- **VENDER** uma posição quando a estimativa de subida descer para **≤50%**, mesmo que a comparação Brier se tenha deteriorado.
- Como salvaguarda, vender também se o último fecho cair **5% abaixo do preço de entrada**. Não existe stop intradiário garantido: só é verificado quando chega uma nova vela diária.
- Entre 50% e 70%, manter a posição aberta. Nunca abrir posições só para o bot parecer ativo.
- Até **20%** do património investível por nova compra, no máximo **3 posições**, e **1 nova posição** por ciclo. Depois de uma queda diária de 5% face à referência, parar novas compras.
- Quando fechar uma posição com ganho líquido após taxa simulada de 0,2% por lado, **reservar 30% do lucro realizado**. Em perdas, não reservar.
- Simular com **50 USD nominais**, ações USD do catálogo. Não confundir com depósito de 50 EUR; FX, spreads reais, impostos e preenchimento de ordens não estão simulados em detalhe.
- As previsões **não estão calibradas**, não demonstram uma taxa de acerto de 70% e a simples comparação Brier com uma referência é insuficiente para garantir viabilidade. A seleção entre dezenas de empresas pode exagerar falsos sinais.
- O motor usa os últimos preços de fecho; não executa trades automáticos dentro da Trading 212, não coloca ordens reais e não usa credenciais da corretora.
- A atualização automática da sessão usa um fragmento Streamlit com intervalo de 1h. **Se a página perder a ligação ou o Codespace/Render parar, o bot deixa de executar.** Cada ativo é processado só uma vez por data de fecho, para não repetir entradas após atualizar a página. Quando termina a sessão, a carteira é apagada.
- O botão de análise manual permite executar um ciclo virtual, mesmo com o modo automático desligado. O botão de reiniciar só aparece quando a automatização está desligada.

Testes de estratégia em `tests/test_auto_paper.py`, sem rede ou corretoras. Para automatização persistente, será necessário um worker de produção, armazenamento duradouro, controlo de identidade e fontes de dados adequadas, além de revisão de segurança.


## Monitor automático de mercado, a cada 30 minutos (aproximado)

O NEXUS tem agora dois processos separados:

1. **GitHub Actions** — `.github/workflows/market-monitor.yml` agenda uma
   análise a cada meia hora, UTC, nas horas **:11 e :41**, mesmo com o
   Streamlit, o Render e o iPad fechados. GitHub Actions usa agendamento
   **best effort**, sem garantir a hora, podendo atrasar, falhar, ser
   suspenso por limites do fornecedor, ou ser desativado após **60 dias
   de inatividade** num repositório público.
2. **Radar** — no Streamlit, seleciona **📡 Monitor 30 min → Abrir monitor**.
   O painel carrega os últimos dados públicos de `market-data/data/latest.json`,
   cujo conteúdo é mantido em ramo Git separado. Se estiveres a ver o site,
   consulta o relatório aproximadamente a cada dois minutos.

**Dados e precisão:**
- Tenta obter uma **vela de 30 minutos já concluída** para cada um dos 185
  ativos. Dados podem chegar com atraso; mercados de ações fecham à
  noite e ao fim de semana. Uma mudança que atravessa o fecho de uma
  bolsa **não** é rotulada como movimento de 30 minutos.
- As percentagens do modelo representam a hipótese **não calibrada de
  subida/descida nos próximos 5 períodos diários**, e são reestimadas
  aproximadamente a cada 22 horas (com histórico de ~2 anos) para
  controlar a utilização da fonte pública. NÃO são probabilidades
  calculadas para os próximos 30 minutos.
- O ficheiro `market-data/data/history.json` guarda até 96
  amostras (cerca de 48 horas de ciclos bem-sucedidos).
- O relatório é marcado como **atrasado** quando não é atualizado há
  mais de 75 minutos; modelo e cotações têm carimbos temporais
  independentes. Não há cotações inventadas em caso de falha.
- Usa `yfinance` para investigação pessoal com limites de acesso, e
  não um feed profissional com SLA. Para serviço público/comercial,
  adquirir dados licenciados e infraestrutura fiável.

### Ativação e verificação no GitHub

1. Em **GitHub → YagoGamelo/crypto-ai-trader → Actions**, abre
   **NEXUS market report every 30 minutes**.
2. Se o GitHub pedir para ativar os workflows, ativa-os.
3. Usa **Run workflow → Branch main → Run workflow** para solicitar
   a primeira execução manual.
4. Em **Settings → Actions → General → Workflow permissions**, caso o
   histórico mostre erro de `git push`, confirma que as ações podem
   obter `Read and write permissions` (com acesso limitado ao projeto).
5. Abre o resultado público em:
   `https://github.com/YagoGamelo/crypto-ai-trader/blob/market-data/data/latest.json`
   e confirma `generated_at_utc` com uma hora recente.

### Página estática disponível mesmo que o Render esteja adormecido

O ramo `market-data` inclui um ficheiro `index.html` responsivo
que pode ser publicado com o **GitHub Pages**. Faz uma única vez:

**GitHub → Settings → Pages → Build and deployment → Source:
Deploy from a branch → Branch `market-data` → `/(root)` → Save.**

Depois de o GitHub Pages terminar a primeira publicação, a página será
habitualmente `https://yagogamelo.github.io/crypto-ai-trader/`.
O HTML carrega o JSON atualizado diretamente do ramo `market-data`
de dois em dois minutos, pelo que **não depende de redeploys do Pages**
para mostrar novos preços. Se o agendamento falhar, a página indica
que o relatório ficou desatualizado. O site estático **não opera**
nem comunica com a API Trading 212.

### A função não é um sistema autónomo de execução de ordens

**Monitorizar 24h ≠ executar ordens reais 24h.** O motor local de
auto-trading continua virtual e limitado à sessão Streamlit aberta.
Este workflow envia **apenas JSON público** para um ramo Git separado;
não carrega API keys, carteira do utilizador nem coloca ordens.
O GitHub Pages e o GitHub Actions podem indisponibilizar-se ou atrasar.

Para comunicação proativa por email/push, seria necessário instalar
um canal de notificações específico e configurar os respetivos
limites e credenciais; ainda não existem notificações push.
