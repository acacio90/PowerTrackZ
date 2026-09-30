# Design tokens do PowerTrackZ

[English](README.md) | **Português**

## Visão Geral

A aparência do frontend é definida por um conjunto único de design tokens: variáveis CSS com as cores, a tipografia, os espaçamentos, os raios de borda e as sombras. Eles ficam em [`services/frontend_service/static/css/base/tokens.css`](../../services/frontend_service/static/css/base/tokens.css). As folhas de estilo usam os tokens em vez de valores fixos, então um ajuste de cor ou de tamanho é feito num único lugar.

## Organização das folhas de estilo

```text
static/css/
├── base/                  # carregados por todas as páginas (base.html)
│   ├── tokens.css         # design tokens
│   ├── elements.css       # reset e elementos base (html, body, main, .container)
│   └── components.css     # navegação, botões, campos, painéis, tabelas, chips e selos, modais, rodapé
└── pages/                 # um arquivo por página, carregado só por ela (bloco extra_css)
    ├── home.css
    ├── infrastructure.css
    ├── analysis.css
    └── scalability.css
```

Regras novas vão para `components.css` quando servem a mais de uma página, e para o arquivo da página quando são específicas dela. Os scripts não criam CSS: aplicam classes. Só estilos calculados em tempo de execução, como posições, larguras e a cor de cada configuração nos grafos, ficam no JavaScript.

## Cores

### Destaque

Há uma única cor de destaque; as variações de estado derivam dela.

| Token | Valor | Uso |
|---|---|---|
| `--color-accent` | `#236dc9` | botões principais, links, seleção, ícones de destaque |
| `--color-accent-hover` | `#1d5fb0` | hover e estado ativo; texto de destaque sobre fundos claros |
| `--color-accent-light` | `#6ea6e6` | destaque sobre a superfície escura (item ativo da barra de navegação) |
| `--color-accent-soft` | `#eaf2fb` | fundo suave (selos, ícones, linha selecionada) |
| `--color-accent-ring` | `rgba(35, 109, 201, 0.25)` | anel de foco e bordas translúcidas |
| `--color-on-accent` | `#fff` | texto sobre o destaque e sobre as cores de estado |

O destaque é do mesmo matiz do azul dos gráficos (`#2a78d6`), escurecido para atender ao contraste AA.

### Neutros

Família cinza-azulada, com texto em três níveis.

| Token | Valor | Uso |
|---|---|---|
| `--color-text-strong` | `#18222d` | títulos e valores |
| `--color-text` | `#304556` | texto padrão |
| `--color-text-muted` | `#607080` | rótulos, dicas e texto secundário |
| `--color-bg` | `#f5f7f9` | fundo da página |
| `--color-surface` | `#fff` | cartões, painéis e modais |
| `--color-surface-muted` | `#f8fafc` | cabeçalhos de tabela e hover suave |
| `--color-surface-sunken` | `#eef2f5` | áreas rebaixadas (trilhos, campos desabilitados) |
| `--color-surface-translucent` | `rgba(255, 255, 255, 0.88)` | sobreposições sobre conteúdo |
| `--color-border` | `#e2e7ec` | divisórias e bordas de cartão |
| `--color-border-strong` | `#cbd5df` | bordas de campos e controles |
| `--color-overlay` | `rgba(24, 34, 45, 0.5)` | fundo atrás de modais |
| `--color-surface-inverse` | `#22313f` | barra de navegação |
| `--color-on-inverse` / `--color-on-inverse-muted` | `#fff` / 85% | texto sobre a barra de navegação |
| `--color-inverse-hover` | `rgba(255, 255, 255, 0.1)` | hover sobre a barra de navegação |

### Estado

Separadas do destaque e sempre com o mesmo significado: sucesso (ação concluída, melhora), alerta (atenção, sobreposição de canais) e erro (falha, piora). Cada uma tem a cor de texto, um fundo suave e uma borda.

| Estado | Texto | Fundo suave | Borda |
|---|---|---|---|
| Sucesso | `--color-success` `#15803d` | `--color-success-soft` `#ecfdf3` | `--color-success-border` `#86efac` |
| Alerta | `--color-warning` `#b45309` | `--color-warning-soft` `#fffbeb` | `--color-warning-border` `#fcd34d` |
| Erro | `--color-danger` `#b42318` | `--color-danger-soft` `#fef2f2` | `--color-danger-border` `#fca5a5` |

A cor não deve ser o único sinal: as variações do painel de resumo, por exemplo, também usam seta e sinal.

### Grafos

As cores das configurações nos grafos de conflito e das séries nos gráficos do teste de escalabilidade vêm de uma paleta categórica de oito cores, sempre na mesma ordem:

| Posição | Token | Cor |
|---|---|---|
| 1 | `--color-graph-series-1` | azul `#2a78d6` |
| 2 | `--color-graph-series-2` | laranja `#eb6834` |
| 3 | `--color-graph-series-3` | verde-água `#1baf7a` |
| 4 | `--color-graph-series-4` | amarelo `#eda100` |
| 5 | `--color-graph-series-5` | rosa `#e87ba4` |
| 6 | `--color-graph-series-6` | verde `#008300` |
| 7 | `--color-graph-series-7` | violeta `#4a3aa7` |
| 8 | `--color-graph-series-8` | vermelho `#e34948` |

**Atribuição.** As configurações presentes nos dois grafos (original e proposto) são ordenadas por faixa, largura de banda e canal, e cada uma recebe, nessa ordem, uma combinação fixa de cor e forma do nó. A mesma configuração tem, assim, a mesma cor e forma nos dois grafos e nas legendas; quando a análise traz configurações novas, o grafo original é recolorido junto. As cores não vêm mais do hash calculado pelo analysis_service (os campos `cor` e `proposed_cor` continuam na resposta da API, mas a interface não os usa).

**Cor e forma.** Nos grafos, qualquer nó pode ficar ao lado de qualquer outro, então a paleta precisa funcionar em todos os pares, e não só entre cores vizinhas. Por isso a cor é combinada com a forma:

- configurações 1 a 8: as oito cores, em círculo, exceto laranja (quadrado) e vermelho (triângulo), que se confundem com outras cores para pessoas daltônicas;
- da 9ª à 28ª: as cores se repetem em quadrado, triângulo, losango e hexágono, e cada forma só recebe cores que se distinguem entre si;
- a partir da 29ª configuração, as combinações se repetem na mesma ordem. Nesse caso, a legenda, que lista canal, largura e faixa de cada combinação, é a referência.

A sequência completa está em `CONFIG_STYLE_SEQUENCE`, no `analysis.js`.

**Validação para daltonismo.** A paleta foi conferida com o validador de paletas categóricas (separação em OKLab para protanopia, deuteranopia e tritanopia):

- entre cores vizinhas na ordem, passa em todos os critérios (pior par: amarelo e verde-água, ΔE 9,1 em protanopia; visão normal: ΔE 19,6);
- entre todos os pares, cinco combinações ficam abaixo do mínimo: laranja com amarelo, rosa, verde e vermelho, e rosa com vermelho (a pior, laranja e verde, com ΔE 3,2 em protanopia). Em todas elas as duas configurações têm formas diferentes, o que foi verificado para as 28 combinações;
- amarelo, rosa e verde-água ficam abaixo de 3:1 sobre o branco; por isso os nós levam o nome do AP e a legenda descreve cada configuração em texto.

As arestas usam `--color-graph-conflict` (`#d62828`) para conflitos, `--color-graph-overlap` (`#c3cad2`) para sobreposição sem conflito e `--color-graph-resolved` (conflito resolvido, tracejado). A borda dos APs alterados usa `--color-text-strong`, e os rótulos das arestas usam `--color-text-muted` sobre `--color-surface`. O JavaScript lê esses tokens do CSS, então as cores dos grafos, das legendas e dos gráficos mudam num só lugar.

## Contraste

Todas as combinações de texto usadas atendem ao nível AA (4,5:1 para texto normal, 3:1 para texto grande).

| Texto | sobre `surface` | sobre `surface-muted` | sobre `bg` | sobre `surface-sunken` |
|---|---|---|---|---|
| `text-strong` | 16,09 | 15,37 | 14,98 | 14,29 |
| `text` | 9,95 | 9,51 | 9,26 | 8,84 |
| `text-muted` | 5,09 | 4,86 | 4,74 | 4,52 |
| `accent` | 5,12 | 4,89 | 4,77 | 4,55 |
| `success` | 5,02 | 4,79 | 4,67 | 4,46 ✗ |
| `warning` | 5,02 | 4,80 | 4,68 | 4,46 ✗ |
| `danger` | 6,57 | 6,28 | 6,12 | 5,84 |

- `on-accent` (branco) sobre `accent`: 5,12; sobre `accent-hover`: 6,33; sobre `warning`: 5,02; sobre `danger`: 6,57; sobre `text-muted` (botão secundário): 5,09.
- Sobre a barra de navegação: `on-inverse` 13,30; `on-inverse-muted` 10,05; `accent-light` 5,23.
- Cores de estado sobre o próprio fundo suave: sucesso 4,76; alerta 4,84; erro 6,01.
- Texto de sucesso ou de alerta não deve ficar sobre `surface-sunken` nem `accent-soft` (4,44 a 4,46).

O contraste foi conferido também nas páginas renderizadas, em todos os textos visíveis, nas larguras de 1280, 1000, 800 e 600 px.

## Tipografia

| Token | Valor | Uso |
|---|---|---|
| `--font-family-base` | pilha de fontes do sistema | todo o texto |
| `--font-size-xs` | `0.75rem` | selos, rótulos em maiúsculas, legendas |
| `--font-size-sm` | `0.85rem` | texto auxiliar, tabelas compactas, dicas |
| `--font-size-md` | `0.9rem` | botões, campos, corpo de tabelas |
| `--font-size-base` | `1rem` | texto padrão |
| `--font-size-lg` | `1.15rem` | títulos de cartão e de seção |
| `--font-size-xl` | `1.5rem` | títulos de painel e de modal |
| `--font-size-2xl` | `2rem` | números em destaque |
| `--font-size-display` | `clamp(2rem, 4vw, 3rem)` | título da página |
| `--font-weight-regular` … `--font-weight-bold` | 400, 500, 600, 700 | pesos |
| `--line-height-tight` / `--line-height-base` | 1,2 / 1,5 | entrelinha de títulos e de texto |

A raiz fica em `16px`, base de todos os valores em `rem`.

## Espaçamento, raios e sombras

| Token | Valor |
|---|---|
| `--space-1` … `--space-7` | `0.25rem`, `0.5rem`, `0.75rem`, `1rem`, `1.5rem`, `2rem`, `3rem` |
| `--radius-sm` | `4px`: botões, campos, selos pequenos |
| `--radius-md` | `8px`: cartões e painéis |
| `--radius-lg` | `12px`: painéis grandes e botões de estratégia |
| `--radius-pill` / `--radius-round` | `999px` / `50%`: pílulas e círculos |
| `--shadow-sm` | elevação leve (cartões) |
| `--shadow-md` | elevação média (painéis, cartões em hover) |
| `--shadow-lg` | elementos flutuantes (modais, sobreposições, botão de adicionar) |
| `--shadow-focus` | anel de foco com `--color-accent-ring` |

Os tokens de espaçamento servem ao código novo; os espaçamentos existentes ainda não foram convertidos.

## Componentes

Cada tipo de componente tem um único estilo, definido em `components.css`. As páginas só acrescentam o que é específico delas (largura, posição, colunas), sem redefinir cores, bordas, raios ou sombras.

### Botões

Variantes por função, sobre o `.btn` do Bootstrap:

| Função | Classe | Aparência | Exemplos |
|---|---|---|---|
| Principal | `.btn-primary` | preenchido no destaque | Salvar, Executar análise, Gerar, Carregar APs |
| Secundário | `.btn-secondary` | contorno neutro | Cancelar, Testar conexão, Reenquadrar, Análise |
| Perigo | `.btn-danger` | contorno vermelho, preenchido no hover | Excluir selecionados, excluir execução |
| Discreto | `.btn-ghost` | só texto, fundo suave no hover | Editar na tabela, Ver, CSV, JSON |

Dois tamanhos: padrão e `.btn-sm`. Os estados (hover, ativo, desabilitado e foco) seguem o mesmo mecanismo em todas as variantes. Uma ação principal por área; ações destrutivas usam perigo, mesmo quando são secundárias. Componentes de escolha, como o seletor de estratégia da Análise, as origens de carregamento de APs e o botão flutuante do mapa, têm estilo próprio e não usam essas variantes.

### Painéis

`.panel` é a superfície padrão de cartões e seções (fundo, borda, raio `md`, sombra `sm` e espaço interno `--space-5`). Modificadores:

| Classe | Uso |
|---|---|
| `.panel-compact` | menos espaço interno (resumos, formulários embutidos) |
| `.panel-flush` | quase sem espaço interno (quadro dos grafos) |
| `.panel-muted` | fundo neutro e sem sombra (indicadores, blocos dentro de outro painel) |
| `.panel-floating` | elementos sobrepostos ao conteúdo (progresso da análise) |

### Tabelas

`.app-table` é a tabela padrão (cabeçalho com fundo neutro, linhas separadas por borda, destaque no hover), dentro de `.app-table-shell` (contorno) e `.app-table-wrap` (rolagem horizontal). `.app-table-compact` é a versão densa, usada nas tabelas de dados e no histórico.

### Chips e selos

- `.chip`: interativo, em forma de pílula (atalhos do mapa do espectro).
- `.tag`: só informativo; `.tag-accent` para destacar (configuração nova, origem dos dados) e `.tag-outline` para rótulos com contorno (pontos de quebra).

### Campos de formulário

Campos de texto, número e seleção têm um único estilo, aplicado ao elemento e às classes `.form-control` e `.form-select` do Bootstrap: borda `border-strong`, raio `sm`, anel de foco no destaque e fundo rebaixado quando desabilitado. O ícone ao lado do campo (`.input-group-text`) segue a mesma borda e altura.

### Foco do teclado

Todo elemento interativo mostra o foco ao navegar pelo teclado: botões e campos com o anel de foco (`--shadow-focus`), e links, resumos (`summary`) e demais controles com um contorno no destaque (`:focus-visible`), que usa o destaque claro sobre a barra de navegação.

## Bootstrap

O Bootstrap 5.3 continua sendo usado, com estes componentes: botões (`.btn`, `.btn-sm`), campos (`.form-control`, `.input-group`), alertas das mensagens do sistema (`.alert`), o modal de configurações, o botão de fechar (`.btn-close`) e alguns utilitários de espaçamento (`me-2`, `mt-4`). A relação com os tokens é esta:

- em `tokens.css`, as variáveis globais dele (`--bs-primary`, `--bs-link-color`, `--bs-body-color`, `--bs-border-color`, `--bs-focus-ring-color`) apontam para os tokens;
- em `components.css`, as variantes de botão são definidas pelas variáveis `--bs-btn-*`, de modo que os estados de hover, ativo, foco e desabilitado continuam sendo os do Bootstrap, com as cores dos tokens;
- `.form-control`, `.form-select` e `.input-group-text` recebem o estilo único de campo;
- os alertas (`.alert-success`, `.alert-warning`, `.alert-danger`) usam as cores de estado pelas variáveis `--bs-alert-*`;
- o fundo escuro do modal de configurações vem do próprio `.modal`, então o `.modal-backdrop` do Bootstrap fica oculto.

Os cartões usam `.panel`, e não o `.card` do Bootstrap. Controles nativos (caixas de seleção) usam o destaque por `accent-color`.

## Exceções

Valores fixos que continuam fora dos tokens:

- `font-size: 16px` na raiz, que define o `rem`;
- `inherit` nas sobrescritas do Leaflet;
- a cor de cada amostra da legenda e de cada série nos gráficos, aplicada pelo JavaScript a partir dos tokens da paleta.

As folhas de estilo não usam `!important`: as sobrescritas do Leaflet (`.map-container .leaflet-*`) e das linhas do inventário vencem pela especificidade dos seletores.
