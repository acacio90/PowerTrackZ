# PowerTrackZ

PowerTrackZ é um sistema avançado de monitoramento e análise de pontos de acesso WiFi, com foco em otimização de energia e detecção de interferência. O projeto utiliza uma arquitetura de microserviços para garantir escalabilidade e facilidade de manutenção.

## 🚀 Funcionalidades Principais

- **Monitoramento Inteligente**: Rastreamento de pontos de acesso com integração Zabbix
- **Análise de Colisões**: Detecção automática de interferências entre APs
- **Otimização de Energia**: Múltiplos algoritmos de otimização (Backtracking, Greedy, Genetic/ML)
- **Visualização Avançada**: Mapas interativos e grafos de colisão
- **Interface Moderna**: Dashboard responsivo com análise em tempo real
- **Arquitetura Escalável**: Microserviços independentes e bem estruturados

## 🏗️ Arquitetura do Projeto

```
PowerTrackZ/
├── gateway/                 # API Gateway (Roteamento puro)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py       # Configurações
│   │   ├── routes.py       # Rotas da API e proxy
│   │   └── main.py         # Aplicação principal
│   ├── Dockerfile
│   └── requirements.txt
│
├── services/              # Microserviços
│   ├── frontend_service/  # Interface de usuário
│   │   ├── app.py         # Aplicação Flask
│   │   ├── templates/     # Templates HTML
│   │   ├── static/        # CSS, JS e assets
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── zabbix_service/    # Integração com Zabbix
│   ├── map_service/       # Mapas e geolocalização
│   ├── analysis_service/  # Análise e algoritmos de otimização
│   └── access_point_service/ # CRUD de pontos de acesso
│
├── scripts/               # Scripts de automação
│   ├── management/        # Gerenciamento básico
│   ├── maintenance/       # Manutenção e deploy
│   └── monitor.sh         # Monitoramento
│
└── docker-compose.yml     # Orquestração Docker
```

## 📋 Requisitos

- **Docker** (versão 20.10+)
- **Docker Compose** (versão 2.0+)
- **Git** (para clonagem)

## 🛠️ Instalação

### Método Rápido (Recomendado)

1. **Clone o repositório**:
```bash
git clone https://github.com/acacio90/PowerTrackZ.git
cd PowerTrackZ
```

2. **Torne os scripts executáveis**:
```bash
chmod +x scripts/management/*.sh
chmod +x scripts/maintenance/*.sh
chmod +x scripts/monitor.sh
```

3. **Execute o script de inicialização**:
```bash
./scripts/management/start.sh
```

O sistema estará disponível em `http://localhost`

### Método Manual

1. **Clone o repositório**:
```bash
git clone https://github.com/acacio90/PowerTrackZ.git
cd PowerTrackZ
```

2. **Build das imagens Docker**:
```bash
docker compose build
```

3. **Inicie os serviços**:
```bash
docker compose up -d
```

## 🔧 Scripts de Gerenciamento

O projeto inclui scripts organizados por categoria para facilitar o gerenciamento:

### 🚀 **Management** - Gerenciamento Básico
- `./scripts/management/start.sh` - Inicia o projeto (build + start)
- `./scripts/management/start.sh --restart` - Reinicia os serviços
- `./scripts/management/stop.sh` - Para os serviços

### 🔧 **Maintenance** - Manutenção e Deploy
- `./scripts/maintenance/maintenance.sh` - Tarefas de manutenção
- `./scripts/maintenance/maintenance.sh --update` - Deploy completo

### 📊 **Monitor** - Monitoramento
- `./scripts/monitor.sh` - Monitoramento em tempo real

Para mais detalhes, consulte [scripts/README.md](scripts/README.md).

## 🏢 Serviços

### Gateway (Porta 80)
- **API Gateway puro** com roteamento inteligente
- **Proxy reverso** para microserviços
- **Roteamento de requisições** com prefixo `/api/`
- **Servir arquivos estáticos** com MIME types corretos

### Frontend Service (Porta 3000)
- **Interface de usuário moderna** e responsiva
- **Templates HTML** com Bootstrap 5
- **Arquivos estáticos** (CSS, JS, imagens)
- **Análise interativa** com Cytoscape.js

### Zabbix Service (Porta 5003)
- **Integração completa** com Zabbix API
- **Sincronização automática** de dados
- **SSL/HTTPS** com certificados próprios
- **Monitoramento de hosts** e triggers

### Map Service (Porta 5001)
- **Visualização de mapas** interativos
- **Geolocalização** de pontos de acesso
- **API de coordenadas** para integração
- **Marcadores personalizados** com informações detalhadas

### Analysis Service (Porta 5002)
- **Múltiplos algoritmos** de análise:
  - **Backtracking**: Busca exaustiva para otimização
  - **Greedy**: Algoritmo guloso para soluções rápidas
  - **Genetic/ML**: Algoritmo genético para otimização avançada
- **Detecção de colisões** entre pontos de acesso
- **Relatórios estatísticos** detalhados
- **API RESTful** para integração

### Access Point Service (Porta 5004)
- **CRUD completo** de pontos de acesso
- **Sincronização bidirecional** com Zabbix
- **Validação de dados** e integridade
- **API RESTful** com suporte a filtros

## 🧠 Algoritmos de Análise

O sistema oferece três estratégias de otimização:

### 🔍 **Backtracking**
- Busca exaustiva por soluções ótimas
- Garante a melhor configuração possível
- Ideal para redes pequenas e médias

### ⚡ **Greedy**
- Algoritmo guloso para soluções rápidas
- Escalável para redes grandes
- Boa relação custo-benefício

### 🧬 **Genetic (ML)**
- Algoritmo genético para otimização avançada
- Aprendizado adaptativo
- Ideal para problemas complexos

## 🎯 Uso

1. **Acesse o sistema**: `http://localhost`
2. **Registre pontos de acesso** na seção "Registrar"
3. **Visualize no mapa** na seção "Pontos"
4. **Execute análises** na seção "Análise":
   - Selecione uma estratégia (Backtracking, Greedy, Genetic)
   - Visualize os grafos de colisão
   - Analise as propostas de otimização
5. **Monitore em tempo real** com `./scripts/monitor.sh`

## 🔍 Monitoramento

Para monitorar o sistema em tempo real:

```bash
./scripts/monitor.sh
```

Este script verifica:
- Status dos containers Docker
- Conectividade dos serviços
- Logs de erro em tempo real
- Performance dos microserviços

## 🛠️ Manutenção

### Atualização do Código
```bash
./scripts/maintenance/maintenance.sh --update
```

### Reinicialização
```bash
./scripts/management/start.sh --restart
```

### Parada Completa
```bash
./scripts/management/stop.sh
```

## 🤝 Contribuição

1. **Fork** o projeto
2. **Crie uma branch** para sua feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. **Push** para a branch (`git push origin feature/AmazingFeature`)
5. **Abra um Pull Request**

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 🆘 Suporte

Para suporte e dúvidas:
- Abra uma [Issue](https://github.com/acacio90/PowerTrackZ/issues)
- Consulte a [documentação](docs/)
- Verifique os [logs](scripts/monitor.sh) do sistema