---
description: Run dashboard backend unit tests in Docker
---

# Run Dashboard Backend Unit Tests

Execute unit tests for the dashboard backend using Docker container.

## Steps

1. Navigate to the backend directory
```bash
cd /Users/gallon/Documents/hermes/dashboard/backend
```

// turbo
2. Run tests using the existing service image with mount
```bash
docker run --rm -v $(pwd):/app -w /app hermes_dashboard-backend:latest sh -c "pip install pytest pytest-cov httpx==0.25.2 -q && pytest"
```

## Expected Output
- 62+ passed tests
- Coverage >= 70%
- HTML coverage report generated in `htmlcov/`

## Notes
- Uses SQLite in-memory for testing (PostgreSQL-specific tests are skipped)
- Test results include coverage report with per-module breakdown
