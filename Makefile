COMPOSE = docker compose
CHECKS = docker compose -f docker-compose.yml -f docker-compose.checks.yml

.PHONY: up down build logs backend-test frontend-test lint format typecheck db-upgrade db-downgrade check connectivity auth-smoke business-smoke tracked-site-smoke ranking-smoke provider-routing-smoke serpapi-smoke serper-smoke

up:
	$(COMPOSE) up --build -d --wait
down:
	$(COMPOSE) down
build:
	$(COMPOSE) build
logs:
	$(COMPOSE) logs -f
backend-test:
	$(COMPOSE) run --rm backend pytest
frontend-test:
	$(CHECKS) run --build --rm --no-deps frontend npm test
lint:
	$(COMPOSE) run --rm --no-deps backend ruff check .
	$(COMPOSE) run --rm --no-deps backend ruff format --check .
	$(CHECKS) run --build --rm --no-deps frontend npm run lint
	$(CHECKS) run --rm --no-deps frontend npm run format:check
format:
	$(COMPOSE) run --rm --no-deps --user "$(shell id -u):$(shell id -g)" -v "$(CURDIR)/backend:/source" -w /source backend ruff format .
	$(COMPOSE) run --rm --no-deps --user "$(shell id -u):$(shell id -g)" -v "$(CURDIR)/backend:/source" -w /source backend ruff check --fix .
	$(CHECKS) run --build --rm --no-deps --user "$(shell id -u):$(shell id -g)" -v "$(CURDIR)/frontend:/source" -w /source frontend /app/node_modules/.bin/prettier --write .
typecheck:
	$(COMPOSE) run --rm --no-deps backend mypy
	$(CHECKS) run --build --rm --no-deps frontend npm run typecheck
db-upgrade:
	$(COMPOSE) run --rm backend alembic upgrade head
db-downgrade:
	$(COMPOSE) run --rm backend alembic downgrade -1
connectivity:
	$(COMPOSE) exec -T backend python -c "import urllib.request; [urllib.request.urlopen('http://127.0.0.1:8000' + path) for path in ['/health', '/health/db', '/health/redis', '/docs', '/openapi.json']]"
	$(COMPOSE) exec -T frontend node -e "Promise.all(['http://backend:8000/health', 'http://backend:8000/health/db', 'http://backend:8000/health/redis', 'http://127.0.0.1:3000/', 'http://127.0.0.1:3000/health'].map(async url => { const r = await fetch(url); if (!r.ok) throw new Error(url); })).catch(() => process.exit(1))"
check: backend-test frontend-test lint typecheck connectivity
auth-smoke:
	$(COMPOSE) exec -T backend python -m scripts.smoke_auth
business-smoke:
	$(COMPOSE) exec -T backend python -m scripts.smoke_projects
tracked-site-smoke:
	$(COMPOSE) exec -T backend python -m scripts.smoke_tracked_sites
ranking-smoke:
	$(COMPOSE) exec -T backend python -m scripts.smoke_rankings
provider-routing-smoke:
	$(COMPOSE) exec -T backend python -m scripts.smoke_provider_routing
serpapi-smoke:
	@echo "WARNING: this command may consume one real SerpApi search credit."
	$(COMPOSE) run --rm -e RUN_REAL_SERP_SMOKE=$(RUN_REAL_SERP_SMOKE) backend python -m scripts.smoke_serpapi
serper-smoke:
	@echo "WARNING: this command may consume one real Serper search credit."
	$(COMPOSE) run --rm -e RUN_REAL_SERPER_SMOKE=$(RUN_REAL_SERPER_SMOKE) backend python -m scripts.smoke_serper
