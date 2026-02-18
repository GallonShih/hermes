---
description: Run dashboard frontend tests and coverage with Vitest
---

# Run Dashboard Frontend Tests

Execute frontend unit/component tests for the dashboard and validate coverage gate.

## Steps

// turbo
1. Install dependencies (if needed)
```bash
cd dashboard/frontend
npm install
```

2. Run frontend test suite
```bash
cd dashboard/frontend
npm run test:run
```

3. Run coverage and verify threshold
```bash
cd dashboard/frontend
npm run test:coverage
```

## Expected Output
- All frontend tests passed
- Coverage >= 70% (Statements/Lines)
- Coverage report generated in `coverage/`

## Notes
- Frontend tests run locally with Vitest (no Docker required)
- Keep Vitest and coverage plugin versions aligned to avoid dependency conflicts
- If coverage is below threshold, prioritize high-line-count files with low coverage
