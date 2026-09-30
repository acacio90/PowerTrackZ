# Usage Guide

**English** | [Português](usage.pt-BR.md)

This guide describes the main flow of the interface: loading access points, saving them to the database and analyzing their channel configurations. Installation is described in [installation.md](installation.md).

The interface is in Portuguese. Screen, button and field names are written here as they appear on screen.

## 1. Your Infrastructure

The **Sua infraestrutura** page (**Infraestrutura** menu, `/infrastructure`) brings together the list and the map of the APs saved in the database. The old `/hosts` and `/register` addresses redirect to it.

### Loading APs

The **Carregar APs** button opens a window with three sources:

- **Zabbix:** lists the APs monitored by the configured Zabbix (see section 4). Zabbix does not provide coordinates; APs already saved keep their inventory coordinates.
- **Importar JSON:** reads a file with a list of APs or an object with the `aps` key, such as the one produced by the option below.
- **Gerar topologia:** creates random APs that are already positioned. The parameters are:
  - *Quantidade de APs*: number of APs, between 2 and 1000;
  - *Grau mínimo*: minimum number of neighbors near which each AP is placed, smaller than the number of APs. These links are only used to place the APs; the analyzed graph is built afterwards, from the coverage overlap in the same band, and is usually much denser;
  - *Semente* (optional): integer between 0 and 4294967295. The same seed, with the same parameters and the same PowerTrackZ version, generates the same topology; when left blank, a seed is drawn. The seed used is shown in the review, in the downloaded file name and in the JSON's `metadata.seed` field.

The loaded APs are shown for review, not yet saved; those without coordinates are highlighted in red. Above the list, the review shows the metrics of the graph that will be analyzed (APs, edges, average degree, maximum degree and density, in total and per band), useful for describing the instances of an experiment. **Baixar JSON** writes the list to a file, which is useful for repeating an experiment with the same topology (which can also be recreated from the seed). **Salvar** writes the APs to the database: APs with the same `id` as a saved AP are updated, and the others are created.

### Editing the inventory

- **Add:** click on the map to mark the position and use the **+** button to enter the description, band, bandwidth and channel; **Adicionar** saves the AP.
- **Edit:** the icon next to each AP opens its data; the coordinates can also be adjusted by clicking on the map while the window is open.
- **Delete:** select the APs and click **Excluir selecionados**.

When adding or editing an AP, the band, bandwidth and channel are chosen from lists with the channels allowed in Brazil (2.4 GHz: channels 1 to 13; 5 GHz: 36 to 64, 100 to 144 and 149 to 165; 6 GHz: 1 to 233). The bandwidths offered depend on the band, and the channels on the band and the bandwidth; changing the band or the bandwidth moves the following fields to a valid value. A saved AP whose configuration is outside these lists opens with the fields left to be selected.

In the list, APs without coordinates are shown in red. Only APs with coordinates take part in the analysis.

## 2. Analyzing

The **Análise** page (**Análise** menu, `/analysis`) builds the conflict graph between the saved APs and suggests a new configuration for each one.

1. Click the desired strategy. The page then shows the parameters of that strategy:
   - **Backtracking:** exact search. With few APs, it returns the optimal configuration; in large networks, it stops at the time limit and returns the best configuration found so far. Parameters:
     - *Threads*: number of threads that split the search, limited to the number of APs;
     - *Limite de tempo (s)*: time limit, 60 s by default, up to 3600 s, applied to each band. Check *Sem limite* to let the search run to completion.
   - **Guloso** (greedy): fast heuristic, suited to large networks, with no optimality guarantee. It has no parameters.
   - **Algoritmo genético** (genetic algorithm): not implemented yet; returns the current configuration.
2. In **Canais disponíveis por faixa**, open each band to see its spectrum map: one line per bandwidth and, on each line, one bar per option, at the position and with the width it occupies on the frequency axis. Click the bars to choose the channels the strategies may use. At 40 MHz, each bar is a pair of primary and secondary, labeled by both channels (such as 7+11); at the other widths, the label is the primary channel, and at 80 and 160 MHz each bar is a channel block (such as 36–48 at 80 MHz). The bar's tooltip shows the channels, the primary sent and the range in MHz. Bars that overlap on the axis interfere with each other, and checked bars that overlap another checked bar of the same width turn orange. The **Padrão**, **Todos** and **Nenhum** shortcuts check ready-made sets, and the **Sem sobreposição** ones check a single width, with the largest set of channels that do not overlap (in 2.4 GHz, 1, 5, 9 and 13 at 20 MHz), clearing the others. The summary of each band shows the total number of profiles (k), and each width shows its share. The default profiles come checked; in 2.4 GHz, the two 40 MHz ones (1+5 and 7+11) overlap by 10 MHz and show in orange, and the 40 MHz **Sem sobreposição** shortcut swaps them for 1+5 and 9+13 when the experiment should not have that overlap (the decision to keep them as defaults is in the analysis_service README). In 2.4 and 5 GHz, at least one channel must remain checked, and the 6 GHz band starts empty, with its APs keeping their current configuration.
3. In **Critério de otimização** (optimization criterion), choose the order in which the strategies compare solutions:
   - **Padrão** (default): fewer conflicts, then lower interference and, as a tiebreak, larger bandwidth;
   - **Energia no desempate** (energy as tiebreak): fewer conflicts, then lower interference and, as a tiebreak, lower power;
   - **Energia primeiro** (energy first): lower power, then fewer conflicts and lower interference; it accepts conflicts to save energy.

   Power comes from the same consumption model shown in the results. Configurations with no value in the model (160 MHz) count as the highest modeled power of their band, and in 6 GHz, which has no values in the model, energy does not tell the profiles apart. Running the same network with different criteria shows how much energy is gained or lost in exchange for conflicts and interference.
4. Adjust the parameters and click **Executar análise**. Values outside the accepted range are flagged below the fields, and the analysis does not start.
5. Follow the progress on the graph on the right, which shows the band being processed. The run can be cancelled while it is in progress.

APs in different bands do not interfere with each other: the analysis builds one graph per band, with no edges between bands, and solves each one separately.

The details of the strategies and of the parameters accepted by the API are in [services/analysis_service/README.md](../../services/analysis_service/README.md).

## 3. Reading the Result

- **Summary:** shown above the graphs after each analysis, with the values computed by analysis_service:
  - *Conflitos*: conflicting edges (in red) before and after the optimization;
  - *Interferência total*: sum of the interference (w·s) of the conflicting edges, before and after;
  - *APs alterados*: how many APs had their channel, bandwidth or frequency changed;
  - *Consumo*: energy estimate before and after, over the given number of days;
  - *Estratégia*: execution time and whether the solution is optimal.

  Each change is shown in green, with ▼, when it improves, and in red, with ▲, when it worsens; for the four metrics, lower values are better. Below the cards, the **Resultados por faixa** table shows, for each band, the APs, the number of profiles (k), the conflicts, the interference, the power and the solution.
- **Graphs:** *Configuração original* and *Configuração proposta* are shown side by side on wide screens and stacked on narrow screens. The APs are positioned by their coordinates, at the same position in both graphs, and zooming and panning in one graph are mirrored in the other; **Reenquadrar** fits both graphs back into view. The legend is below each graph. Each channel, bandwidth and band configuration has a node color and shape (circle, square, triangle, diamond or hexagon), the same in both graphs; the legend shows the swatch with the color and shape, the number of APs and the configuration. Each edge connects two APs whose coverage areas overlap:
  - in **red**, thicker, when the two APs conflict in the displayed configuration, with the interference as a percentage;
  - in **light gray** when there is only overlap, without conflict, with the overlap percentage. In graphs with many edges, these labels are hidden; use *Mostrar pesos das arestas sem conflito* to show them.

  In the optimized graph, APs whose configuration changed get a dark border, and the conflicts of the original graph resolved by the strategy are shown dashed and faded. The legend shows how many APs changed and how many conflicts were resolved. Uncheck *Destacar mudanças no grafo otimizado* to hide these highlights.
- **Configuration table:** current and proposed channel, bandwidth and frequency of each AP. **Editar** changes the proposed configuration, chosen from lists with the channels checked in **Canais disponíveis por faixa**; on save, the AP is locked to that configuration and the optimized analysis is run again.
- **Consumption:** energy (kWh) and cost (R$, at R$ 0.72 per kWh) estimate, above each graph, for the period entered in the *Dias da estimativa de consumo* field. The power of each AP is computed by analysis_service with the Dembélé et al. (2023) model, from its band and bandwidth; APs at 160 MHz or in 6 GHz, which have no value in the model, are left out of the sum.
- **Metadados da execução** (execution metadata):
  - *Critério de otimização*: the criterion used in the analysis;
  - *Arestas*: pairs of APs whose coverage overlaps in the same band, with or without conflict;
  - *Conflitos (antes / depois)*: pairs of APs in conflict (interference greater than zero) before and after the optimization;
  - *Densidade de conflitos (antes / depois)*: fraction of the possible pairs of APs that are in conflict;
  - *Solução*: whether the configuration is optimal, whether the search stopped at the time limit or whether it was cancelled;
  - *Conflitos (guloso / final)*: in backtracking, conflicts of the initial greedy solution and of the final solution;
  - *Nós explorados*: size of the search performed;
  - *Parâmetros*: threads and time limit used;
  - *Faixa*: one line per band, with APs, edges, number of profiles (k), conflicts and whether the band's solution is optimal. The other metadata add up the bands.

## 4. Configuring Zabbix

The settings open from the gear icon in the navigation bar, on any page, and take the Zabbix API URL, the user and the password. Use **Testar conexão** before **Salvar**. The `/settings` address leads to the home screen with the settings open. The credentials are stored in the SQLite database of `access_point_service`.

## 5. Scalability Test

The **Teste de escalabilidade** page (card on the home screen, `/scalability`) measures up to what network size each strategy solves the problem. It generates a topology from the seed, with the maximum size, and analyzes prefixes of it of increasing size (the first 10 APs, the first 20, ...), so that each instance contains the previous one. Nothing is saved to the AP inventory, and the graphs are not drawn.

1. Enter the **maximum size** (up to 1,000 APs), the **step**, the **minimum degree**, the **seed** (when left blank, one is drawn), the **time limit**, the **threads**, the **optimization criterion** and the **strategies**. The channels used are the default profiles. The criterion appears in the parameters of each run in the history and in the `objective` column of the CSV.
2. Click **Executar teste**. The progress shows the size and the strategy being analyzed, and the run can be cancelled. Only one run executes at a time, so the measured times do not mix.
3. For each size, the exact strategies run first. A strategy **breaks** at the first size at which it no longer solves the problem: an exact method (backtracking), when it does not find the optimum within the time limit, which applies to each band; a method without an optimality guarantee (greedy), when it exceeds the time limit. After breaking, it is no longer run at the following sizes, and the test ends when every strategy has broken or the maximum size is reached.

The result shows the break point of each strategy and two charts as a function of the number of APs: the execution time, on a logarithmic scale, with the time-limit line, and the conflicts after the optimization. The break point is shown as an X. The **Tabela dos pontos medidos** lists, for each size and strategy, the edges, the density, the time, the conflicts, the distance to the optimum (while the exact method finds it), the interference, the power, the explored nodes and the stop reason.

Each run is kept in the **Histórico de execuções** with its date, parameters and PowerTrackZ version (commit, branch and, when there is one, the tag), which allows repeating the test in another version and comparing the results. **Ver** opens a run's charts, **CSV** and **JSON** download the measured points, and **Excluir** removes the run. A run interrupted by a service restart is recorded as **Interrompida**.
