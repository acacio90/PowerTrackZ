# Energia do Processamento das Estratégias

[English](README.md) | **Português**

O PowerTrackZ estima a energia consumida pelos pontos de acesso com a configuração proposta, mas não a energia gasta para calcular essa configuração. Este documento registra a investigação da #87: as opções de medição, a viabilidade de cada uma no ambiente do projeto, o método escolhido e os resultados de um protótipo.

## Ambiente

As medições foram feitas na máquina de desenvolvimento, em 2026-10-01:

- Dell OptiPlex SFF Plus 7020 (desktop, sem bateria), com Intel Core i7-14700: 20 núcleos (8 de desempenho e 12 de eficiência), 28 threads, potência base (PBP) de 65 W e potência turbo máxima (MTP) de 219 W;
- Windows, com os serviços em contêineres Docker sobre o WSL2 (kernel `6.6.87.2-microsoft-standard-WSL2`);
- o analysis_service roda num contêiner próprio, sem limite de CPU (`cpu.max` = `max`).

## Opções Avaliadas

| Opção | Precisão | Requisitos | Limitações | Viável no ambiente? |
|---|---|---|---|---|
| RAPL pelo `powercap` (`/sys/class/powercap/intel-rapl`) | Boa para o pacote do processador (Khan et al., 2018), com granularidade de cerca de 1 ms | Linux com acesso direto ao processador | Mede o processador inteiro, não o processo; precisa de linha de base em repouso | **Não**: o diretório não existe no WSL2, nem em contêiner privilegiado |
| RAPL pelo `perf` (PMU `power`, eventos `energy-pkg`, `energy-cores`...) | Igual à anterior | Linux, `perf_event_paranoid` permitindo, contêiner privilegiado | Igual à anterior | **Não**: o PMU `power` existe no kernel do WSL2, mas sem eventos, e abrir `energy-pkg`, `energy-cores`, `energy-ram`, `energy-gpu` ou `energy-psys` pela chamada `perf_event_open` retorna `EINVAL` |
| RAPL no Windows por ferramenta (LibreHardwareMonitor, HWiNFO, Intel PCM) | Boa para o pacote, com amostragem de cerca de 1 s nas ferramentas de monitoramento | Instalar a ferramenta e um *driver* de kernel, como administrador | Mede a máquina inteira, inclusive o Windows e a VM do WSL2; precisa de linha de base e de execuções longas em relação à amostragem; depende do hospedeiro e não entra no PowerTrackZ | **Possível, não verificada**: nenhuma ferramenta está instalada, e o terminal do projeto não roda como administrador. A Intel Power Gadget foi descontinuada |
| Contadores de energia do Windows (conjuntos "Energy Meter" e "Power Meter") | Variável | Firmware que os exponha | Disponíveis só em alguns equipamentos | **Não**: os dois conjuntos de contadores não existem nesta máquina |
| Estimativa do Windows por processo (*Energy Estimation Engine*, `powercfg /srumutil`) | Baixa: modelo agregado por hora | Administrador; voltada a equipamentos com bateria | Não separa uma execução de outra | **Não adequada** à medição por execução |
| Medidor externo na tomada | Boa para a máquina inteira | Equipamento de medição | Mede tudo o que a máquina consome; precisa de linha de base e de execuções longas; não é automatizável no projeto | **Possível, não verificada**: depende de equipamento |
| **Tempo de CPU × potência por núcleo** | Estimativa: assume potência constante por núcleo ocupado | Contabilidade de CPU do processo ou do contêiner | Não captura frequência, turbo, diferença entre núcleos de desempenho e de eficiência, memória nem consumo em repouso | **Sim**: o cgroup do contêiner (`cpu.stat`, `usage_usec`) é acessível, e o próprio processo pode medir o tempo de CPU das suas *threads* |

## Método Escolhido

**Energia estimada = tempo de CPU da análise × potência por núcleo.**

- O tempo de CPU vem da contabilidade do sistema operacional: no protótipo, a variação de `usage_usec` no cgroup do contêiner do analysis_service durante a análise, com o serviço ocioso; numa integração, o tempo de CPU das *threads* da própria análise, medido pelo serviço.
- A potência por núcleo é um coeficiente configurável. O padrão é a potência base dividida pelos núcleos (65 W / 20 = 3,25 W), como na calculadora Green Algorithms (Lannelongue, Grealey e Inouye, 2021), que estima a energia pelo tempo de execução, pelos núcleos usados e pela potência por núcleo do processador. O limite superior usa a potência turbo máxima (219 W / 20 = 10,95 W). A biblioteca CodeCarbon adota a mesma estimativa pela potência nominal quando o RAPL não está disponível.

**Justificativa.**

1. É o único método viável dentro do ambiente do projeto, sem *driver* de kernel nem equipamento.
2. É aplicado da mesma forma a todas as estratégias: não depende de como cada uma é implementada, só do tempo de CPU que ela consome, inclusive com várias *threads* (o backtracking com 4 *threads* gasta 4 segundos de CPU por segundo).
3. É reprodutível em qualquer máquina: o tempo de CPU é medido, e a potência por núcleo é um parâmetro declarado nos resultados.
4. Para comparar estratégias, o que importa é a proporção entre elas, que não depende do coeficiente. O valor absoluto é uma estimativa e deve ser apresentado como faixa (potência base a turbo) ou com o coeficiente explícito.

**O que a estimativa não captura:** a variação de frequência e o turbo, a diferença entre núcleos de desempenho e de eficiência (o agendador do Windows e do WSL2 escolhe os núcleos), a energia da memória e o consumo da máquina em repouso. Por isso, ela mede a energia atribuível ao processamento da estratégia, e não o consumo total da máquina.

**Trabalho futuro: calibração com medição real.** Com uma ferramenta de RAPL no Windows ou um medidor na tomada, a estimativa pode ser calibrada: medir a máquina em repouso e durante execuções longas de uma mesma estratégia, subtrair a linha de base e comparar com o tempo de CPU da execução. Essa calibração trocaria o coeficiente padrão por um medido nesta máquina.

## Protótipo

O script [`scripts/experiments/processing_energy.py`](../../scripts/experiments/processing_energy.py) gera uma topologia pela semente, executa cada estratégia algumas vezes sobre ela, uma por vez, e mede o tempo de CPU pelo cgroup do contêiner, descontando o custo da própria leitura (o `docker exec` roda dentro do contêiner; cerca de 12 ms de CPU por leitura).

```bash
docker compose up -d
python scripts/experiments/processing_energy.py --nodes 100 --repetitions 3
```

Resultado com 100 APs (semente 2026, grau mínimo 3), média de 3 repetições:

| Estratégia | Tempo (s) | CPU (s) | Núcleos | Energia (J), base a turbo | Conflitos |
|---|---|---|---|---|---|
| Guloso | 0,022 | 0,005 | 0,24 | 0,02 a 0,06 | 211 |
| Backtracking, 1 *thread*, limite de 10 s | 20,9 | 20,9 | 1,00 | 68 a 229 | 201 |
| Backtracking, 4 *threads*, limite de 10 s | 20,9 | 83,6 | 4,00 | 272 a 916 | 158 |
| Busca local, 200 mil iterações | 0,85 | 0,85 | 1,00 | 2,8 a 9,3 | 94 |
| Simulated Annealing, 200 mil iterações | 1,39 | 1,39 | 1,00 | 4,5 a 15,2 | 77 |

O backtracking parou no limite de tempo nas duas faixas (10 s em cada), então gasta tempo de CPU proporcional ao limite e ao número de *threads*: com 4 *threads*, o mesmo tempo de relógio custa quatro vezes mais energia. Nesta instância, as metaheurísticas chegaram a menos conflitos com uma fração da energia do backtracking interrompido. No guloso, o tempo de CPU (5 ms) é da ordem da variação da leitura (cerca de 2 ms), então execuções muito curtas precisam de repetições.

## Integração ao PowerTrackZ

Integrada na #124: o analysis_service mede o tempo de CPU de cada análise, somando o das *threads* que a executam (sem misturar análises simultâneas), e informa na resposta, por faixa e no total, o tempo de CPU e a energia estimada, com a potência por núcleo configurada em `ANALYSIS_CORE_POWER_W` e `ANALYSIS_MAX_CORE_POWER_W` (detalhes no README do analysis_service, seção Energia do Processamento). A página de Análise exibe a estimativa, e o teste de escalabilidade a registra em cada ponto e no CSV. O protótipo continua útil para medir de fora, pelo cgroup, e conferir a medição interna.

## Referências

- KHAN, K. N.; HIRKI, M.; NIEMI, T.; NURMINEN, J. K.; OU, Z. RAPL in Action: Experiences in Using RAPL for Power Measurements. *ACM Transactions on Modeling and Performance Evaluation of Computing Systems*, v. 3, n. 2, 2018.
- LANNELONGUE, L.; GREALEY, J.; INOUYE, M. Green Algorithms: Quantifying the Carbon Footprint of Computation. *Advanced Science*, v. 8, n. 12, 2021.
- CodeCarbon. Documentação do método de estimativa da energia do processador. Disponível em: https://mlco2.github.io/codecarbon/.
