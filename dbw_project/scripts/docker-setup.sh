#!/bin/bash

# Docker setup detection and configuration for dbw
# Automatically detects whether to use Docker-outside-Docker (DOOD) or Docker-in-Docker (DIND)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[DBW Docker Setup]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

# Check if Docker socket is accessible (DOOD mode)
check_docker_socket() {
    local socket_path="/var/run/docker.sock"
    
    if [[ -S "$socket_path" ]]; then
        if docker info >/dev/null 2>&1; then
            log "Docker socket accessible - using Docker-outside-Docker (DOOD) mode"
            echo "DOOD"
            return 0
        else
            warn "Docker socket exists but not accessible (permission issue?)"
            return 1
        fi
    else
        log "Docker socket not found - will use Docker-in-Docker (DIND) mode"
        echo "DIND"
        return 1
    fi
}

# Setup Docker-in-Docker environment
setup_dind() {
    log "Setting up Docker-in-Docker environment..."
    
    # Check if DinD services are already running
    if docker-compose -f docker-compose.dind.yml ps --services --filter "status=running" | grep -q "docker-daemon"; then
        log "Docker-in-Docker daemon already running"
        return 0
    fi
    
    # Start DinD services
    log "Starting Docker-in-Docker services..."
    docker-compose -f docker-compose.dind.yml up -d docker-daemon buildkit
    
    # Wait for Docker daemon to be ready
    log "Waiting for Docker daemon to be ready..."
    timeout=60
    while ! docker-compose -f docker-compose.dind.yml exec -T docker-daemon docker info >/dev/null 2>&1; do
        sleep 2
        timeout=$((timeout - 2))
        if [[ $timeout -le 0 ]]; then
            error "Docker daemon failed to start within 60 seconds"
            return 1
        fi
    done
    
    success "Docker-in-Docker environment ready"
}

# Setup Docker-outside-Docker environment  
setup_dood() {
    log "Configuring Docker-outside-Docker environment..."
    
    # Check Docker group membership
    if ! groups | grep -q docker; then
        warn "User not in docker group. You may need to run: sudo usermod -aG docker $USER"
        warn "Then logout and login again"
    fi
    
    # Export environment variables for DOOD
    export DOCKER_HOST="unix:///var/run/docker.sock"
    export DOCKER_MODE="DOOD"
    
    success "Docker-outside-Docker environment configured"
}

# Setup Buildx builder
setup_buildx() {
    local builder_name="${1:-dbw_builder}"
    
    log "Setting up Docker Buildx builder: $builder_name"
    
    # Check if builder exists
    if docker buildx inspect "$builder_name" >/dev/null 2>&1; then
        log "Buildx builder '$builder_name' already exists"
        docker buildx use "$builder_name"
    else
        log "Creating new Buildx builder: $builder_name"
        docker buildx create --name "$builder_name" --use --driver docker-container
    fi
    
    # Ensure builder is running
    docker buildx inspect --bootstrap >/dev/null
    
    success "Buildx builder '$builder_name' ready"
}

# Clean up Docker environments
cleanup() {
    log "Cleaning up Docker environments..."
    
    # Stop DinD services if running
    if [[ -f "docker-compose.dind.yml" ]]; then
        docker-compose -f docker-compose.dind.yml down --volumes || true
    fi
    
    # Remove buildx builder
    local builder_name="${1:-dbw_builder}"
    if docker buildx inspect "$builder_name" >/dev/null 2>&1; then
        docker buildx rm "$builder_name" || true
    fi
    
    success "Cleanup complete"
}

# Get current Docker mode
get_docker_mode() {
    if [[ -n "${DOCKER_HOST:-}" ]] && [[ "$DOCKER_HOST" == *"tcp://"* ]]; then
        echo "DIND"
    elif docker info >/dev/null 2>&1; then
        echo "DOOD"
    else
        echo "UNKNOWN"
    fi
}

# Main function
main() {
    case "${1:-setup}" in
        "setup")
            log "Auto-detecting Docker configuration..."
            if docker_mode=$(check_docker_socket); then
                if [[ "$docker_mode" == "DOOD" ]]; then
                    setup_dood
                fi
            else
                setup_dind
                export DOCKER_HOST="tcp://localhost:2376"
                export DOCKER_MODE="DIND"
            fi
            setup_buildx
            ;;
        "dood")
            setup_dood
            setup_buildx
            ;;
        "dind")
            setup_dind
            export DOCKER_HOST="tcp://localhost:2376"
            export DOCKER_MODE="DIND"
            setup_buildx
            ;;
        "status")
            mode=$(get_docker_mode)
            log "Current Docker mode: $mode"
            if [[ "$mode" != "UNKNOWN" ]]; then
                docker info --format "Version: {{.ServerVersion}}"
                docker buildx ls
            fi
            ;;
        "cleanup")
            cleanup "${2:-dbw_builder}"
            ;;
        "help"|"--help"|"-h")
            cat <<EOF
DBW Docker Setup Script

Usage: $0 [COMMAND]

Commands:
  setup     Auto-detect and setup appropriate Docker mode (default)
  dood      Force Docker-outside-Docker mode
  dind      Force Docker-in-Docker mode  
  status    Show current Docker configuration
  cleanup   Clean up Docker environments and builders
  help      Show this help message

Environment Variables:
  DBW_DOCKER_MODE    Force specific mode: DOOD or DIND
  DBW_BUILDER_NAME   Custom Buildx builder name (default: dbw_builder)

Examples:
  $0 setup          # Auto-detect and configure
  $0 dind           # Force Docker-in-Docker
  $0 status         # Check current setup
  $0 cleanup        # Clean up everything
EOF
            ;;
        *)
            error "Unknown command: $1"
            error "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"