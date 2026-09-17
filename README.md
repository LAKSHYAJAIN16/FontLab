# MicroTune (FontLab / WebLab)

> Drop in a script tag, tell it your conversion goal, and it keeps proposing tiny design tweaks as A/B variants to find what actually moves the number — no human picking "should the button be blue or green."

Most A/B testing tools run the experiment a human already thought of; they never discover it. There are hundreds of small design variables on any page that quietly affect conversion — MicroTune treats the whole page as a parameter vector (font, size, weight, padding, spacing, alignment...) and lets an optimizer hill-climb toward the goal metric instead. Repo's called `FontLab` locally, also `WebLab` in places, product name is MicroTune. It's a monorepo: SDK, API, dashboard, and optimization engine.

## Status
**Built:**
- `packages/sdk` — browser SDK (`MicroTune.init()`, `MicroTune.goal()`); fetches the assigned variant from `/config`, patches the DOM, reports events to `/events` via `sendBeacon`
- `services/api` — FastAPI backend: `/health`, `/config` (deterministic hash-based assignment), `/events`, Postgres + Alembic

**Scaffolded, not built:**
- `services/optimizer` — bandit/Bayesian optimization logic, currently a stub
- `services/shared` — code shared between api and optimizer, currently a stub
- `apps/dashboard` — unmodified `create-next-app` starter, not wired up

`ARCHITECTURE.md` has the real infra plan (Cloudflare Workers, Neon Postgres, ClickHouse, Fly.io).

## Running it
JS/TS (pnpm workspace via Turborepo):
```bash
pnpm install
pnpm build   # or: pnpm dev
```

Python (uv workspace):
```bash
uv sync --all-packages
cp services/api/.env.example services/api/.env   # fill in DATABASE_URL
uv run --project services/api alembic upgrade head
uv run --project services/api main.py
```

## Where the optimizer is headed
The search space is huge (20 tunable properties x 4 options each is already over a trillion combinations), so it grows in stages:
1. **Plain A/B tests** — one property at a time, 50/50 split
2. **Multi-armed bandits** (Thompson sampling, UCB, epsilon-greedy) — shift traffic toward winners early
3. **Bayesian optimization** — treat the page as a black-box function, pick the next candidate expected to teach the most
4. **Evolutionary search** — mutate/recombine/cull a real population of variants

Constraints that matter along the way: mutations stay in a safe range (font size +/-15%, spacing +/-20%, etc.) and never touch payment/legal/forms/checkout/auth/nav; candidates stay visually close to the original brand; changes stay sparse (one or two properties at a time) so results are attributable; the objective balances conversion against engagement, bounce, and performance, not just clicks.

Longer term, the interesting question is whether certain design changes generalize across sites with similar context — a contextual-bandit problem where a new site could skip straight to changes likely to work instead of starting from zero.

## Stack
- **SDK**: TypeScript, aiming to stay under 20KB
- **Backend**: FastAPI + Postgres, ClickHouse planned for high-volume events
- **Dashboard**: Next.js, React, Tailwind
- **Optimization**: NumPy, SciPy, scikit-learn, eventually PyTorch/BoTorch
