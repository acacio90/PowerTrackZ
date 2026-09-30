# Management Scripts - PowerTrackZ

**English** | [Português](SCRIPTS.pt-BR.md)

This document describes the scripts available to manage the PowerTrackZ project.

## Available Scripts

### 1. `start.sh` - Start the Project

Main script to build and start all PowerTrackZ services.

**Usage:**
```bash
./start.sh [OPTIONS]
```

**Options:**
- `--restart` - Restarts the services without rebuilding
- `--clean` - Removes old images before building
- `-h, --help` - Shows the help

**Examples:**
```bash
./start.sh              # Normal build and start
./start.sh --restart    # Restarts the services (no rebuild)
./start.sh --clean      # Clean build (removes old images)
./start.sh --clean --restart  # Restarts with a clean build
```

**What it does:**
1. Checks that Docker and Docker Compose are installed
2. Stops existing containers (if --restart is used)
3. Removes old images (if --clean is used)
4. Builds the Docker images (skipped if --restart is used)
5. Starts all services
6. Checks the health of the services
7. Shows the access information

### 2. `stop.sh` - Stop the Project

Script to stop all PowerTrackZ services.

**Usage:**
```bash
./stop.sh [OPTIONS]
```

**Options:**
- `--clean` - Removes containers and volumes
- `--clean-all` - Removes containers, volumes and images
- `-h, --help` - Shows the help

**Examples:**
```bash
./stop.sh              # Stops the services normally
./stop.sh --clean      # Stops and removes containers/volumes
./stop.sh --clean-all  # Stops and removes everything (containers, volumes, images)
```

### 3. `start-local.ps1` - Run without Docker Compose (Windows)

Starts the Python services in a local virtual environment and `analysis_service` in a standalone Docker container, each one in its own PowerShell window.

**Usage:**
```powershell
.\scripts\management\start-local.ps1 [-SkipInstall] [-VenvPath <path>]
```

**Options:**
- `-SkipInstall`: does not reinstall the virtual environment dependencies
- `-VenvPath`: path of the virtual environment (default: `.venv-local`)

Without Docker in the `PATH`, `analysis_service` is not started. To stop, press `Ctrl+C` in each window.

## Typical Workflow

### First Run
```bash
# 1. Clone the repository
git clone https://github.com/acacio90/PowerTrackZ.git
cd PowerTrackZ

# 2. Make the scripts executable
chmod +x scripts/management/*.sh

# 3. Start the project
./scripts/management/start.sh
```

### Daily Development
```bash
# Stop the services
./scripts/management/stop.sh

# Restart the services (no rebuild)
./scripts/management/start.sh --restart

# Restart with a rebuild
./scripts/management/start.sh --clean

# Show the logs
docker compose logs -f

# Show the status
docker compose ps
```

### Full Cleanup
```bash
# Stop and remove everything
./scripts/management/stop.sh --clean-all

# Start with a clean build
./scripts/management/start.sh --clean
```

## Available Services

After running `./start.sh`, the following services are available:

| Service | Port | Description |
|---------|------|-------------|
| Frontend Service | 3000 | Main web interface |
| Analysis Service | 5002 | Data analysis and algorithms |
| Access Point Service | 5004 | AP management |

## Useful Docker Commands

```bash
# Show the logs of all services
docker compose logs -f

# Show the logs of a specific service
docker compose logs -f frontend_service
docker compose logs -f analysis_service

# Show the container status
docker compose ps

# Run a command in a container
docker compose exec frontend_service bash

# Show resource usage
docker stats

# Check service connectivity
./scripts/monitor.sh
```

## Troubleshooting

### Common Problems

1. **Port already in use:**
   ```bash
   # Check what is using the port
   sudo lsof -i :3000

   # Stop the process
   sudo kill -9 <PID>
   ```

2. **Permission error:**
   ```bash
   # Make the scripts executable
   chmod +x scripts/management/*.sh
   ```

3. **Docker not found:**
   ```bash
   # Install Docker
   sudo apt-get update
   sudo apt-get install docker.io docker-compose
   sudo systemctl start docker
   sudo systemctl enable docker
   sudo usermod -aG docker $USER
   ```

4. **Image build error:**
   ```bash
   # Clear the Docker cache
   docker builder prune -f

   # Clean rebuild
   ./scripts/management/start.sh --clean
   ```

5. **Full cleanup:**
   ```bash
   # Stop and remove everything
   ./scripts/management/stop.sh --clean-all

   # Remove unused images
   docker system prune -a
   ```

6. **Connectivity problems:**
   ```bash
   # Check the status of the services
   ./scripts/monitor.sh

   # Check the error logs
   docker compose logs --tail=50 | grep ERROR
   ```

## Requirements

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **curl** (for health checks)
- **bash** (default shell)
- **git** (to clone the repository)

## Script Structure

All scripts follow the same pattern:
- **Colored output** (green, red, yellow, blue)
- **Log functions** (success, error, warn, info)
- **Dependency check** (Docker, Docker Compose)
- **Argument handling** (--help, --restart, --clean)
- **Project banner** with information
- **Service health check**
- **Robust error handling**

## Integration with Other Scripts

The management scripts work together with:

- **`scripts/monitor.sh`** - Real-time monitoring
- **`scripts/maintenance/maintenance.sh`** - Maintenance and deploy
- **`scripts/maintenance/maintenance.sh --update`** - Full deploy

## Advanced Usage Examples

### Development
```bash
# Start the development environment
./scripts/management/start.sh

# Monitor in real time
./scripts/monitor.sh

# Restart after changes
./scripts/management/start.sh --restart
```

### Production
```bash
# Full deploy
./scripts/maintenance/maintenance.sh --update

# Continuous monitoring
./scripts/monitor.sh

# Periodic maintenance
./scripts/maintenance/maintenance.sh
```

### Debug
```bash
# Show detailed logs
docker compose logs -f --tail=100

# Check connectivity
curl -f http://localhost:3000/health
curl -f http://localhost:5002/health
curl -f http://localhost:5004/health

# Check resources
docker stats --no-stream
```
