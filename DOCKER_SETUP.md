# TrustChain Docker Setup Guide

Quick start guide for running TrustChain with Docker.

## Prerequisites

- Docker Engine 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ (included with Docker Desktop)
- At least 2GB free disk space

## Quick Start (Development)

### 1. Clone and Configure

```bash
cd /path/to/TrustChain

# Copy environment template
cp backend/.env.example backend/.env

# Edit .env and add your API keys
nano backend/.env  # or use your preferred editor
```

**Required: Add your API keys to `.env`:**
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here
```

### 2. Start Services

```bash
# Start core services (backend + postgres)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Check health
curl http://localhost:8000/api/v1/health
```

### 3. Test the API

```bash
# Submit a test decision
curl -X POST http://localhost:8000/api/v1/decisions \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "TEST-001",
    "case_type": "unemployment_benefits",
    "decision_type": "standard",
    "context": "Applicant lost job due to company downsizing. Has worked for 5 years. No disciplinary issues."
  }'

# Get decision status
curl http://localhost:8000/api/v1/decisions/TEST-001
```

## Service Architecture

### Core Services (Always Running)

| Service | Port | Description |
|---------|------|-------------|
| **backend** | 8000 | FastAPI application |
| **postgres** | 5432 | PostgreSQL database |

### Optional Services

Start with profiles:

```bash
# Start with Ollama (local Llama)
docker-compose --profile with-ollama up -d

# Start with pgAdmin (database GUI)
docker-compose --profile with-pgadmin up -d

# Start with both
docker-compose --profile with-ollama --profile with-pgadmin up -d
```

| Service | Port | Access | Profile |
|---------|------|--------|---------|
| **ollama** | 11434 | Local Llama inference | `with-ollama` |
| **pgAdmin** | 5050 | Database GUI at http://localhost:5050 | `with-pgadmin` |

## Common Commands

### Manage Services

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a service
docker-compose restart backend

# View logs
docker-compose logs -f backend
docker-compose logs postgres

# Check service status
docker-compose ps
```

### Database Operations

```bash
# Access PostgreSQL shell
docker-compose exec postgres psql -U trustchain -d trustchain

# Run SQL file
docker-compose exec -T postgres psql -U trustchain -d trustchain < backend/database/schema.sql

# Backup database
docker-compose exec postgres pg_dump -U trustchain trustchain > backup.sql

# Restore database
docker-compose exec -T postgres psql -U trustchain trustchain < backup.sql
```

### Development Workflow

```bash
# Rebuild after code changes
docker-compose up -d --build backend

# View real-time logs
docker-compose logs -f backend

# Execute command in running container
docker-compose exec backend python -c "print('Hello from container')"

# Shell into backend container
docker-compose exec backend /bin/bash
```

## Environment Variables

Key variables in `.env`:

### Required
```bash
ANTHROPIC_API_KEY=sk-ant-...     # Anthropic API key
OPENAI_API_KEY=sk-proj-...       # OpenAI API key
```

### Optional
```bash
POSTGRES_PASSWORD=changeme        # Database password
SECRET_KEY=generate-with-openssl  # JWT secret key
ENVIRONMENT=development           # development | staging | production
DEBUG=True                        # Enable debug mode
LOG_LEVEL=INFO                    # DEBUG | INFO | WARNING | ERROR
```

## Database Schema

The database schema is automatically initialized on first startup from `backend/database/schema.sql`.

### Tables Created:
- `decisions` - Main decision records
- `model_decisions` - Individual AI model responses
- `bias_analyses` - Bias detection results
- `audit_logs` - Immutable audit trail
- `users` - System users (for v1.1)
- `api_keys` - API authentication (for v1.1)

### Access Database:

```bash
# Via psql
docker-compose exec postgres psql -U trustchain -d trustchain

# Via pgAdmin (if enabled)
# Open http://localhost:5050
# Email: admin@trustchain.local
# Password: admin (or your PGADMIN_PASSWORD)
```

## Ollama Setup (Optional)

For local Llama inference without external API calls:

### 1. Start Ollama Service

```bash
docker-compose --profile with-ollama up -d
```

### 2. Pull a Model

```bash
# Pull Llama 3.1 (8B)
docker-compose exec ollama ollama pull llama3.1

# Pull Llama 3.1 (70B) - requires more RAM
docker-compose exec ollama ollama pull llama3.1:70b
```

### 3. Test Ollama

```bash
# Test inference
docker-compose exec ollama ollama run llama3.1 "Hello, how are you?"

# List available models
docker-compose exec ollama ollama list
```

### 4. Configure TrustChain

In `.env`:
```bash
OLLAMA_BASE_URL=http://ollama:11434
```

## Production Deployment

### Security Checklist

Before deploying to production:

- [ ] Change all default passwords in `.env`
- [ ] Generate strong SECRET_KEY: `openssl rand -hex 32`
- [ ] Set `DEBUG=False`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure HTTPS/TLS termination
- [ ] Enable firewall rules
- [ ] Set up log rotation
- [ ] Configure backup strategy
- [ ] Review CORS settings in `backend/app.py`

### Production `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      ENVIRONMENT: production
      DEBUG: "False"
      LOG_LEVEL: WARNING
    volumes:
      - ./backend:/app/backend:ro  # Read-only
    restart: always

  postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # Use strong password
    volumes:
      - /var/lib/trustchain/postgres:/var/lib/postgresql/data  # Persistent storage
    restart: always
```

Run with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Missing API keys in .env
# 2. Database not ready - wait 30 seconds and retry
# 3. Port 8000 already in use - change in docker-compose.yml
```

### Database connection failed

```bash
# Check postgres health
docker-compose ps postgres

# If unhealthy:
docker-compose down
docker volume rm trustchain_postgres_data
docker-compose up -d
```

### API returns 500 errors

```bash
# Check backend logs for details
docker-compose logs backend --tail=100

# Verify API keys are set
docker-compose exec backend env | grep API_KEY
```

### Permission denied errors

```bash
# Fix ownership
docker-compose exec backend chown -R trustchain:trustchain /app

# Or rebuild
docker-compose down
docker-compose up -d --build
```

## Performance Tuning

### Database

```yaml
# In docker-compose.yml, add to postgres service:
command:
  - postgres
  - -c
  - shared_buffers=256MB
  - -c
  - effective_cache_size=1GB
  - -c
  - max_connections=100
```

### Backend

```yaml
# In docker-compose.yml, add to backend service:
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/v1/health

# Database health
docker-compose exec postgres pg_isready -U trustchain

# All services
docker-compose ps
```

### View Metrics

```bash
# Container stats
docker stats

# Service-specific stats
docker stats trustchain-backend
docker stats trustchain-postgres
```

## Data Persistence

### Volumes

Docker volumes persist data across container restarts:

- `postgres_data` - Database files
- `ollama_data` - Ollama models (if used)
- `backend_logs` - Application logs
- `pgadmin_data` - pgAdmin configuration

### Backup Volumes

```bash
# Backup postgres volume
docker run --rm -v trustchain_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz /data

# Restore postgres volume
docker run --rm -v trustchain_postgres_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

## Cleanup

### Stop and Remove Everything

```bash
# Stop services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove images
docker rmi trustchain-backend
```

### Prune Unused Resources

```bash
# Remove all unused containers, networks, images
docker system prune -a

# Remove all unused volumes (WARNING: may delete data)
docker volume prune
```

## Next Steps

After successful Docker setup:

1. Read [COMPLETE_MVP_GUIDE.md](./COMPLETE_MVP_GUIDE.md) for API usage
2. Review [SAFETY_SAFEGUARDS.md](./SAFETY_SAFEGUARDS.md) for bias detection
3. See [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md) for system design
4. Check [FUTURE_IMPROVEMENTS.md](./FUTURE_IMPROVEMENTS.md) for roadmap

## Support

For issues:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review Docker logs: `docker-compose logs -f`
3. Verify environment configuration in `.env`
4. Test API health: `curl http://localhost:8000/api/v1/health`
