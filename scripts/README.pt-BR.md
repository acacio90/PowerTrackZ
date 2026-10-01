# Scripts - PowerTrackZ

[English](README.md) | **Português**

Esta pasta contém todos os scripts de automação e gerenciamento do projeto PowerTrackZ, organizados por categoria para facilitar o uso e a manutenção.

## 📁 Estrutura

```
scripts/
├── README.pt-BR.md        # Este arquivo
├── monitor.sh             # Monitoramento em tempo real
├── management/            # Scripts de gerenciamento básico
│   ├── start.sh          # Iniciar/reiniciar o projeto
│   ├── stop.sh           # Parar o projeto
│   ├── start-local.ps1   # Executar sem Docker Compose (Windows)
│   └── SCRIPTS.pt-BR.md  # Documentação dos scripts de gerenciamento
├── maintenance/          # Scripts de manutenção e deploy
│   └── maintenance.sh    # Tarefas de manutenção e deploy completo
└── experiments/          # Experimentos da pesquisa
    └── processing_energy.py  # Energia do processamento das estratégias (docs/energy)
```

## 🎯 Categorias de Scripts

### 🚀 **Management** - Gerenciamento Básico
Scripts para operações diárias do projeto.

**Localização:** `scripts/management/`

- **`start.sh`** - Inicia o projeto (build + start)
- **`start.sh --restart`** - Reinicia os serviços sem rebuild
- **`stop.sh`** - Para os serviços com opções de limpeza
- **`start-local.ps1`** - Executa os serviços localmente no Windows, sem Docker Compose

**Uso:**
```bash
# Da raiz do projeto
./scripts/management/start.sh
./scripts/management/start.sh --restart
./scripts/management/stop.sh

# Ou navegando para a pasta
cd scripts/management
./start.sh
./start.sh --restart
./stop.sh
```

### 🔧 **Maintenance** - Manutenção e Deploy
Scripts para tarefas de manutenção, limpeza e deploy completo.

**Localização:** `scripts/maintenance/`

- **`maintenance.sh`** - Backup, limpeza de logs, verificação de recursos
- **`maintenance.sh --update`** - Deploy completo com atualização de código

**Funcionalidades integradas:**
- Backup automático do banco de dados
- Limpeza de logs e cache
- Verificação de recursos do sistema
- Atualização de código via Git
- Rebuild de imagens Docker
- Verificação de saúde dos serviços

### 🔬 **Experiments** - Experimentos
Scripts de medição usados na pesquisa, executados com os serviços no ar.

**Localização:** `scripts/experiments/`

- **`processing_energy.py`** - Mede o tempo de CPU de cada estratégia pelo cgroup do contêiner do analysis_service e estima a energia do processamento (método e resultados em [docs/energy/README.pt-BR.md](../docs/energy/README.pt-BR.md))

### 📊 **Monitor** - Monitoramento
Scripts para monitoramento em tempo real.

**Localização:** `scripts/` (raiz)

- **`monitor.sh`** - Monitoramento de serviços, recursos e logs

**Funcionalidades:**
- Status dos contêineres Docker
- Conectividade dos microsserviços
- Logs de erro em tempo real
- Uso de recursos do sistema
- Verificação de portas

## 🚀 Uso Rápido

### Primeira Execução
```bash
# Clone o repositório
git clone https://github.com/acacio90/PowerTrackZ.git
cd PowerTrackZ

# Torne os scripts executáveis
chmod +x scripts/management/*.sh
chmod +x scripts/maintenance/*.sh
chmod +x scripts/monitor.sh

# Inicie o projeto
./scripts/management/start.sh
```

### Operações Diárias
```bash
# Iniciar o projeto
./scripts/management/start.sh

# Parar o projeto
./scripts/management/stop.sh

# Reiniciar serviços
./scripts/management/start.sh --restart

# Monitorar em tempo real
./scripts/monitor.sh

# Manutenção básica
./scripts/maintenance/maintenance.sh

# Deploy completo
./scripts/maintenance/maintenance.sh --update
```

### Deploy em Produção
```bash
# Deploy completo com backup e verificação
./scripts/maintenance/maintenance.sh --update
```

## 🎨 Convenções

### Cores dos Scripts
Todos os scripts seguem o mesmo padrão de cores:
- 🟢 **Verde** - Logs de sucesso
- 🔴 **Vermelho** - Erros críticos
- 🟡 **Amarelo** - Avisos e informações importantes
- 🔵 **Azul** - Informações gerais
- ⚪ **Branco** - Logs padrão

### Estrutura dos Scripts
Todos os scripts seguem o mesmo padrão:
- **Verificação de dependências** (Docker, Docker Compose)
- **Funções de log** (success, error, warn, info)
- **Tratamento de argumentos** (--help, --restart, --update)
- **Banner do projeto** com informações
- **Verificação de saúde** dos serviços
- **Tratamento de erros** robusto

### Logs e Arquivos
Os scripts geram logs e arquivos em:
- `logs/monitor.log` - Logs de monitoramento
- `logs/maintenance.log` - Logs de manutenção
- `backups/` - Backups automáticos do banco de dados
- `logs/` - Logs de erro e debug

## 🔧 Troubleshooting

### Problemas Comuns

1. **Permissão negada:**
   ```bash
   chmod +x scripts/*/*.sh scripts/*.sh
   ```

2. **Docker não encontrado:**
   ```bash
   sudo apt-get install docker.io docker-compose
   sudo systemctl start docker
   sudo usermod -aG docker $USER
   ```

3. **Porta já em uso:**
   ```bash
   sudo kill -9 <PID>
   ```

4. **Erro de build das imagens:**
   ```bash
   docker builder prune -f
   ./scripts/management/start.sh
   ```

### Logs e Debug
```bash
# Ver logs do Docker Compose
docker compose logs -f

# Ver logs de um serviço específico
docker compose logs -f frontend_service
docker compose logs -f analysis_service

# Ver status dos contêineres
docker compose ps

# Ver uso de recursos
docker stats

# Verificar conectividade dos serviços
./scripts/monitor.sh
```

### Verificação de Saúde
```bash
# Verificar se todos os serviços estão rodando
docker compose ps

# Verificar logs de erro
docker compose logs --tail=50 | grep ERROR

# Verificar uso de recursos
docker stats --no-stream
```

## 📋 Requisitos

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **bash** (shell padrão)
- **curl** (para verificações de conectividade)
- **bc** (para cálculos matemáticos)
- **openssl** (para verificação SSL)
- **git** (para atualizações de código)

## 🔄 Fluxo de Trabalho

### Desenvolvimento
1. **Iniciar ambiente**: `./scripts/management/start.sh`
2. **Monitorar**: `./scripts/monitor.sh`
3. **Reiniciar quando necessário**: `./scripts/management/start.sh --restart`

### Produção
1. **Deploy**: `./scripts/maintenance/maintenance.sh --update`
2. **Monitoramento contínuo**: `./scripts/monitor.sh`
3. **Manutenção periódica**: `./scripts/maintenance/maintenance.sh`

### Manutenção
1. **Backup**: automático no deploy
2. **Limpeza**: logs e cache
3. **Verificação**: saúde dos serviços
4. **Atualização**: código e dependências

## 🤝 Contribuição

Ao adicionar novos scripts:

1. **Use o padrão estabelecido**:
   - Cores consistentes
   - Tratamento de erros
   - Funções de log padronizadas

2. **Documente adequadamente**:
   - Adicione ao README apropriado, nos dois idiomas
   - Inclua exemplos de uso
   - Documente os parâmetros

3. **Teste em diferentes ambientes**:
   - Desenvolvimento
   - Produção
   - Diferentes sistemas operacionais

4. **Mantenha a organização**:
   - Coloque na categoria correta
   - Use nomes descritivos
   - Siga as convenções

## 📚 Documentação Adicional

- [SCRIPTS.pt-BR.md](management/SCRIPTS.pt-BR.md) - Documentação detalhada dos scripts de gerenciamento
- [README.pt-BR.md](../README.pt-BR.md) - Documentação principal do projeto
- [docs/](../docs/) - Documentação técnica detalhada
