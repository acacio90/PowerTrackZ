# Scripts - PowerTrackZ

**English** | [Português](README.pt-BR.md)

This folder contains all the automation and management scripts of the PowerTrackZ project, organized by category to make them easier to use and maintain.

## 📁 Structure

```
scripts/
├── README.md              # This file
├── monitor.sh             # Real-time monitoring
├── management/            # Basic management scripts
│   ├── start.sh          # Start/restart the project
│   ├── stop.sh           # Stop the project
│   ├── start-local.ps1   # Run without Docker Compose (Windows)
│   └── SCRIPTS.md        # Documentation of the management scripts
├── maintenance/          # Maintenance and deploy scripts
│   └── maintenance.sh    # Maintenance tasks and full deploy
└── experiments/          # Research experiments
    └── processing_energy.py  # Processing energy of the strategies (docs/energy)
```

## 🎯 Script Categories

### 🚀 **Management** - Basic Management
Scripts for the project's day-to-day operations.

**Location:** `scripts/management/`

- **`start.sh`** - Starts the project (build + start)
- **`start.sh --restart`** - Restarts the services without rebuilding
- **`stop.sh`** - Stops the services, with cleanup options
- **`start-local.ps1`** - Runs the services locally on Windows, without Docker Compose

**Usage:**
```bash
# From the project root
./scripts/management/start.sh
./scripts/management/start.sh --restart
./scripts/management/stop.sh

# Or from inside the folder
cd scripts/management
./start.sh
./start.sh --restart
./stop.sh
```

### 🔧 **Maintenance** - Maintenance and Deploy
Scripts for maintenance, cleanup and full deploy tasks.

**Location:** `scripts/maintenance/`

- **`maintenance.sh`** - Backup, log cleanup, resource check
- **`maintenance.sh --update`** - Full deploy with code update

**Built-in features:**
- Automatic database backup
- Log and cache cleanup
- System resource check
- Code update via Git
- Docker image rebuild
- Service health check

### 🔬 **Experiments** - Experiments
Measurement scripts used in the research, run with the services up.

**Location:** `scripts/experiments/`

- **`processing_energy.py`** - Measures the CPU time of each strategy through the analysis_service container cgroup and estimates the processing energy (method and results in [docs/energy/README.md](../docs/energy/README.md))

### 📊 **Monitor** - Monitoring
Scripts for real-time monitoring.

**Location:** `scripts/` (root)

- **`monitor.sh`** - Monitoring of services, resources and logs

**Features:**
- Docker container status
- Microservice connectivity
- Real-time error logs
- System resource usage
- Port check

## 🚀 Quick Start

### First Run
```bash
# Clone the repository
git clone https://github.com/acacio90/PowerTrackZ.git
cd PowerTrackZ

# Make the scripts executable
chmod +x scripts/management/*.sh
chmod +x scripts/maintenance/*.sh
chmod +x scripts/monitor.sh

# Start the project
./scripts/management/start.sh
```

### Daily Operations
```bash
# Start the project
./scripts/management/start.sh

# Stop the project
./scripts/management/stop.sh

# Restart services
./scripts/management/start.sh --restart

# Monitor in real time
./scripts/monitor.sh

# Basic maintenance
./scripts/maintenance/maintenance.sh

# Full deploy
./scripts/maintenance/maintenance.sh --update
```

### Production Deploy
```bash
# Full deploy with backup and checks
./scripts/maintenance/maintenance.sh --update
```

## 🎨 Conventions

### Script Colors
All scripts follow the same color pattern:
- 🟢 **Green** - Success logs
- 🔴 **Red** - Critical errors
- 🟡 **Yellow** - Warnings and important information
- 🔵 **Blue** - General information
- ⚪ **White** - Default logs

### Script Structure
All scripts follow the same pattern:
- **Dependency check** (Docker, Docker Compose)
- **Log functions** (success, error, warn, info)
- **Argument handling** (--help, --restart, --update)
- **Project banner** with information
- **Service health check**
- **Robust error handling**

### Logs and Files
The scripts write logs and files to:
- `logs/monitor.log` - Monitoring logs
- `logs/maintenance.log` - Maintenance logs
- `backups/` - Automatic database backups
- `logs/` - Error and debug logs

## 🔧 Troubleshooting

### Common Problems

1. **Permission denied:**
   ```bash
   chmod +x scripts/*/*.sh scripts/*.sh
   ```

2. **Docker not found:**
   ```bash
   sudo apt-get install docker.io docker-compose
   sudo systemctl start docker
   sudo usermod -aG docker $USER
   ```

3. **Port already in use:**
   ```bash
   sudo kill -9 <PID>
   ```

4. **Image build error:**
   ```bash
   docker builder prune -f
   ./scripts/management/start.sh
   ```

### Logs and Debug
```bash
# Show Docker Compose logs
docker compose logs -f

# Show logs of a specific service
docker compose logs -f frontend_service
docker compose logs -f analysis_service

# Show container status
docker compose ps

# Show resource usage
docker stats

# Check service connectivity
./scripts/monitor.sh
```

### Health Check
```bash
# Check that all services are running
docker compose ps

# Check error logs
docker compose logs --tail=50 | grep ERROR

# Check resource usage
docker stats --no-stream
```

## 📋 Requirements

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **bash** (default shell)
- **curl** (for connectivity checks)
- **bc** (for arithmetic)
- **openssl** (for SSL checks)
- **git** (for code updates)

## 🔄 Workflow

### Development
1. **Start the environment**: `./scripts/management/start.sh`
2. **Monitor**: `./scripts/monitor.sh`
3. **Restart when needed**: `./scripts/management/start.sh --restart`

### Production
1. **Deploy**: `./scripts/maintenance/maintenance.sh --update`
2. **Continuous monitoring**: `./scripts/monitor.sh`
3. **Periodic maintenance**: `./scripts/maintenance/maintenance.sh`

### Maintenance
1. **Backup**: automatic on deploy
2. **Cleanup**: logs and cache
3. **Check**: service health
4. **Update**: code and dependencies

## 🤝 Contributing

When adding new scripts:

1. **Follow the established pattern**:
   - Consistent colors
   - Error handling
   - Standard log functions

2. **Document them properly**:
   - Add them to the appropriate README, in both languages
   - Include usage examples
   - Document the parameters

3. **Test in different environments**:
   - Development
   - Production
   - Different operating systems

4. **Keep things organized**:
   - Put them in the right category
   - Use descriptive names
   - Follow the conventions

## 📚 Additional Documentation

- [SCRIPTS.md](management/SCRIPTS.md) - Detailed documentation of the management scripts
- [README.md](../README.md) - Main project documentation
- [docs/](../docs/) - Detailed technical documentation
