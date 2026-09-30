# Arquitetura do PowerTrackZ

[English](README.md) | **Português**

## Visão Geral

O PowerTrackZ é um sistema distribuído enxuto para monitorar e analisar pontos de acesso. A interface web é a entrada principal da aplicação, renderiza o mapa no próprio frontend e conversa diretamente com os serviços internos configurados por variáveis de ambiente.

## Componentes Principais

### Frontend Service
- Interface web principal
- Renderização das páginas
- Mapa interativo com Leaflet
- Rotas `/api/*` usadas pelo JavaScript da interface
- Encaminhamento direto para o Analysis e o Access Point Service

### Access Point Service
- Gerenciamento dos pontos de acesso
- Importação, geração e sincronização de dados
- Configuração, teste e consulta do Zabbix externo
- Persistência dos APs cadastrados
- Fonte dos dados exibidos no mapa

### Analysis Service
- Análise de colisão e otimização
- Execução dos algoritmos de análise
- Streaming de progresso para a interface
- Consulta ao Access Point Service quando precisa carregar os pontos cadastrados

## Fluxo de Dados

1. O usuário acessa o Frontend Service em `http://localhost:3000`.
2. O frontend renderiza as páginas, incluindo o mapa interativo.
3. As rotas internas do frontend chamam diretamente o microsserviço responsável.
4. O Access Point Service concentra CRUD, importação, geração e integração com o Zabbix.
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

## Considerações

- Os serviços continuam isolados em contêineres.
- O frontend concentra as responsabilidades de interface, incluindo o mapa.
- O Access Point Service é o dono de tudo que cria, importa ou sincroniza APs.
- As URLs internas são configuradas pelo `.env` e pelo `docker-compose.yml`.
