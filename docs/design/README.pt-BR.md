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
│   └── components.css     # barra de navegação, modais, formulários, botões, tabelas, rodapé
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

As linhas da legenda dos grafos de conflito usam `--color-graph-conflict` (`#d62828`), `--color-graph-overlap` (`#c3cad2`) e `--color-graph-resolved`. Elas repetem as cores das arestas desenhadas pelo Cytoscape; o alinhamento dos grafos à paleta está previsto na #96.

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

## Bootstrap

O Bootstrap 5.3 continua sendo usado. Os tokens ajustam as variáveis dele (`--bs-primary`, `--bs-link-color`, `--bs-body-color`, `--bs-border-color`, `--bs-focus-ring-color`) em `tokens.css` e as variáveis de botão (`--bs-btn-*`) de `.btn-primary`, `.btn-secondary`, `.btn-outline-primary`, `.btn-outline-secondary` e `.btn-outline-danger` em `components.css`, para que os estados de hover, foco e ativo usem as cores dos tokens. Controles nativos (caixas de seleção) usam o destaque por `accent-color`.

## Exceções

Valores fixos que continuam fora dos tokens:

- `font-size: 16px` na raiz, que define o `rem`;
- `inherit` nas sobrescritas do Leaflet;
- cores calculadas em tempo de execução no JavaScript (cor de cada configuração nos grafos e nos gráficos), tratadas na #96.
