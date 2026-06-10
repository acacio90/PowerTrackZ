# Arquitetura do PowerTrackZ

## Visao Geral

O PowerTrackZ e um sistema distribuido enxuto para monitorar e analisar pontos de acesso. A interface web e a entrada principal da aplicacao, renderiza o mapa no proprio frontend e conversa diretamente com os servicos internos configurados por variaveis de ambiente.

## Componentes Principais

### Frontend Service
- Interface web principal
- Renderizacao das paginas
- Mapa interativo com Leaflet
- Rotas `/api/*` usadas pelo JavaScript da interface
- Encaminhamento direto para Analysis e Access Point Service

### Access Point Service
- Gerenciamento dos pontos de acesso
- Importacao, geracao e sincronizacao de dados
- Configuracao, teste e consulta do Zabbix externo
- Persistencia dos APs cadastrados
- Fonte dos dados exibidos no mapa

### Analysis Service
- Analise de colisao e otimizacao
- Execucao dos algoritmos de analise
- Streaming de progresso para a interface
- Consulta ao Access Point Service quando precisa carregar os pontos cadastrados

## Fluxo de Dados

1. O usuario acessa o Frontend Service em `http://localhost:3000`.
2. O frontend renderiza as paginas, incluindo o mapa interativo.
3. As rotas internas do frontend chamam diretamente o microservico responsavel.
4. O Access Point Service concentra CRUD, importacao, geracao e integracao com Zabbix.
5. O Analysis Service consulta o Access Point Service quando precisa carregar os pontos cadastrados.

## Diagrama de Arquitetura

```text
[Cliente]
   |
   v
[Frontend Service]
   |                 |
   v                 v
[Access Point]  [Analysis]
      |
      v
[Banco de Dados]
      |
      v
[Zabbix externo]
```

## Consideracoes

- Os servicos continuam isolados em containers.
- O frontend concentra as responsabilidades de interface, incluindo o mapa.
- O Access Point Service e o dono de tudo que cria, importa ou sincroniza APs.
- As URLs internas sao configuradas por `.env` e `docker-compose.yml`.
