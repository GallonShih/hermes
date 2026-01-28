---
name: Docker Compose Development
description: Master the workflow for developing applications using Docker Compose with source code mounting.
---

# Docker Compose Development Skill

This skill provides best practices and workflows for developing applications running in Docker Compose, specifically focusing on services that mount source code for development (hot-reload).

## 1. Context Awareness (First Step)

Before taking any action, ALWAYS analyze the `docker-compose.yml` file to understand the environment.

**Checklist:**
1.  **Identify Services**: What services are defined?
2.  **Check Volumes**: fast checks for volumes that mount local source code (e.g., `./backend:/app`).
    *   *If mounted*: Code changes usually reflect immediately (Hot Reload).
    *   *If NOT mounted*: Code changes require image rebuild.
3.  **Check Service State**:
    ```bash
    docker compose ps
    ```

## 2. Development Workflow

### A. Code Changes (Hot Reload)
If a service mounts source code (e.g., `volumes: - ./src:/app`), **DO NOT REBUILD** the container for simple code changes.

1.  **Edit the code** locally.
2.  **Wait** a moment for auto-reload (if the framework supports it, like FastAPI/Next.js).
3.  **Verify** the change (e.g., check logs or refresh browser).

### B. Dependency Changes
If you modify `requirements.txt`, `package.json`, `Dockerfile`, or unmounted files:

**Action:** Rebuild ONLY the specific service.
```bash
docker compose up -d --build <service_name>
```
*Note: This is faster than rebuilding everything.*

### C. Adding New Files
If you create a new file, ensure it is within the mounted directory.
*   If valid: No action needed.
*   If outside mount: You may need to adjust `docker-compose.yml` or rebuild.

## 3. Running Tests

**CRITICAL**: Always run tests **INSIDE** the container to ensure the environment matches production/CI. DO NOT run tests locally unless explicitly asked.

**Syntax:**
```bash
docker compose exec <service_name> <test_command>
```

**Common Examples:**
*   **Python/Pytest**:
    ```bash
    docker compose exec <backend_service_name> pytest tests/ -v
    ```
*   **Node/Jest**:
    ```bash
    docker compose exec <frontend_service_name> npm test
    ```

## 4. Troubleshooting & Operations

### View Logs
To check for errors or verify startup:
```bash
docker compose logs --tail=100 -f <service_name>
```

### Access Shell
To explore the container filesystem or debug manually:
```bash
docker compose exec <service_name> /bin/bash
# If bash is missing, try:
docker compose exec <service_name> sh
```

### Restart Service
If hot-reload fails or application hangs:
```bash
docker compose restart <service_name>
```

---

## Example Scenario

**Scenario**: You added a new endpoint to `backend` service (FastAPI).

1.  **Edit code**: `app/routers/new_api.py` (Local file).
2.  **No Build Needed**: Because `./app` is mounted to container.
3.  **Check Logs**: `docker compose logs -f backend` to see if it reloaded.
4.  **Test**: `docker compose exec backend pytest tests/test_new_api.py`.
