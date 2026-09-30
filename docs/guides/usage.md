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
  - *Quantidade de nós*: number of APs, between 2 and 500;
  - *Fator de clique*: minimum number of neighbors each AP tries to keep, smaller than the number of nodes.

The loaded APs are shown for review, not yet saved; those without coordinates are highlighted in red. **Baixar JSON** writes the list to a file, which is useful for repeating an experiment with the same topology. **Salvar** writes the APs to the database: APs with the same `id` as a saved AP are updated, and the others are created.

### Editing the inventory

- **Add:** click on the map to mark the position and use the **+** button to enter the description, frequency, bandwidth and channel.
- **Edit:** the icon next to each AP opens its data; the coordinates can also be adjusted by clicking on the map while the window is open.
- **Delete:** select the APs and click **Excluir Selecionados**.

When adding or editing an AP, the frequency, bandwidth and channel are chosen from lists with the channels allowed in Brazil (2.4 GHz: channels 1 to 13; 5 GHz: 36 to 64, 100 to 144 and 149 to 165; 6 GHz: 1 to 233). The bandwidths offered depend on the frequency, and the channels on the frequency and the bandwidth; changing the frequency or the bandwidth moves the following fields to a valid value. A saved AP whose configuration is outside these lists opens with the fields left to be selected.

In the list, APs without coordinates are shown in red. Only APs with coordinates take part in the analysis.

## 2. Analyzing

The **Análise** page (**Análise** menu, `/analysis`) builds the collision graph between the saved APs and suggests a new configuration for each one.

1. Click the desired strategy. The page then shows the parameters of that strategy:
   - **Backtracking:** exact search. With few APs, it returns the optimal configuration; in large networks, it stops at the time limit and returns the best configuration found so far. Parameters:
     - *Threads*: number of threads that split the search, limited to the number of APs;
     - *Limite de tempo (s)*: time limit, 60 s by default, up to 3600 s. Check *Sem limite* to let the search run to completion.
   - **Greedy:** fast heuristic, suited to large networks, with no optimality guarantee. It has no parameters.
   - **Genetic:** not implemented yet; returns the current configuration.
2. Adjust the parameters and click **Executar análise**. Values outside the accepted range are flagged below the fields, and the analysis does not start.
3. Follow the progress on the graph on the right. The run can be cancelled while it is in progress.

The details of the strategies and of the parameters accepted by the API are in [services/analysis_service/README.md](../../services/analysis_service/README.md).

## 3. Reading the Result

- **Summary:** shown above the graphs after each analysis:
  - *Conflitos*: conflicting edges (in red) in the original and optimized graphs, with the percentage reduction;
  - *APs alterados*: how many APs had their channel, bandwidth or frequency changed;
  - *Consumo*: energy estimate before and after, and the difference, over the given number of days;
  - *Estratégia*: execution time and whether the solution is optimal.
- **Graphs:** *Configuração original* and *Configuração proposta* are shown side by side on wide screens and stacked on narrow screens. The APs are positioned by their coordinates, at the same position in both graphs, and zooming and panning in one graph are mirrored in the other; **Reenquadrar** fits both graphs back into view. The color and edge legend is below each graph. Each edge connects two APs whose coverage areas overlap:
  - in **red**, thicker, when the two APs conflict in the displayed configuration, with the interference as a percentage;
  - in **light gray** when there is only overlap, without conflict, with the overlap percentage. In graphs with many edges, these labels are hidden; use *Mostrar pesos das arestas sem conflito* to show them.

  In the optimized graph, APs whose configuration changed get a dark border, and the conflicts of the original graph resolved by the strategy are shown dashed and faded. The legend shows how many APs changed and how many conflicts were resolved. Uncheck *Destacar mudanças no grafo otimizado* to hide these highlights.
- **Configuration table:** current and proposed channel, bandwidth and frequency of each AP. **Editar** changes the proposed configuration, chosen from lists with only the profiles the strategies can propose; on save, the AP is locked to that configuration and the optimized analysis is run again.
- **Consumption:** energy (kWh) and cost (R$) estimate, above each graph, for the period entered in the *Dias da estimativa de consumo* field.
- **Metadados de Execução** (execution metadata):
  - *Arestas Antes / Depois*: pairs of APs in conflict before and after the optimization;
  - *Solução*: whether the configuration is optimal, whether the search stopped at the time limit or whether it was cancelled;
  - *Conflitos Guloso / Final*: in backtracking, conflicts of the initial greedy solution and of the final solution;
  - *Nós Explorados*: size of the search performed;
  - *Parâmetros*: threads and time limit used.

## 4. Configuring Zabbix

The settings open from the gear icon in the navigation bar, on any page, and take the Zabbix API URL, the user and the password. Use **Testar Conexão** before **Salvar**. The `/settings` address leads to the home screen with the settings open. The credentials are stored in the SQLite database of `access_point_service`.
