# PowerTrackZ
PowerTrackZ é um projeto que visa monitorar e analisar pontos de acesso de energia utilizando a API do Zabbix. Este projeto permite registrar, visualizar e analisar dados de pontos de acesso de forma eficiente.

## Funcionalidades
- Rastreamento de pontos de acesso de energia
- Análise detalhada de desempenho dos pontos de acesso
- Indicação da melhor distribuição de configurações de APs
- Integração com a API do Zabbix

## Estrutura do Projeto

```
PowerTrackZ/
├── gateway/                 # API Gateway
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py       # Configurações
│   │   ├── routes/         # Rotas da API
│   │   │   ├── __init__.py
│   │   │   ├── zabbix.py
│   │   │   ├── map.py
│   │   │   ├── analysis.py
│   │   │   └── access_point.py
│   │   ├── services/       # Serviços de comunicação
│   │   │   ├── __init__.py
│   │   │   └── http.py
│   │   └── templates/      # Templates HTML
│   ├── Dockerfile
│   └── requirements.txt
│
├── services/              # Microserviços
│   ├── zabbix_service/    # Serviço de integração com Zabbix
│   ├── map_service/       # Serviço de mapas
│   ├── analysis_service/  # Serviço de análise
│   └── access_point_service/ # Serviço de pontos de acesso
│
└── docker-compose.yml     # Configuração Docker
```

## Requisitos

- Docker
- Docker Compose
- Python 3.9+

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/acacio90/PowerTrackZ.git
cd PowerTrackZ
```

2. Build das imagens Docker:
```bash
docker-compose build
```

3. Inicie os serviços:
```bash
docker-compose up -d
```

## Serviços

### Gateway (Porta 80)
- API Gateway principal
- Roteamento de requisições
- Interface web

### Zabbix Service (Porta 5003)
- Integração com Zabbix

### Map Service (Porta 5001)
- Visualização de mapas
- Geolocalização de pontos de acesso

### Analysis Service (Porta 5002)
- Análise de dados
- Relatórios

### Access Point Service (Porta 5004)
- Gerenciamento de pontos de acesso
- Registro e monitoramento

## Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request