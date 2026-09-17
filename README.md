# MicroTune (FontLab / WebLab)

The idea: you drop one script tag on your site, tell it what your conversion goal is (a signup, a purchase, whatever), and it keeps proposing tiny, safe design tweaks — font size, spacing, CTA padding, alignment — serving them as A/B variants and quietly figuring out which ones actually move the number. No human sitting there deciding "should the button be blue or green."

Repo's locally called `FontLab`, I've also called it `WebLab` in places, product name is MicroTune. It's a monorepo: SDK, API, dashboard, and the optimization engine all live here.

## Where it actually stands right now

This is early. Here's what's real vs. what's still just the plan:

**Actually built:**
- `packages/sdk` — the browser SDK (`MicroTune.init()`, `MicroTune.goal()`). Fetches the visitor's assigned variant from `/config`, patches the DOM with the CSS changes, and reports impressions/goal completions to `/events` via `sendBeacon`.
- `services/api` — a FastAPI backend with `/health`, `/config` (deterministic hash-based variant assignment, see `app/assignment.py`), and `/events`, backed by a Postgres schema (`Project`, `Goal`, `Experiment`, `Variant`, `MutationConstraint`) with Alembic migrations.

**Scaffolded, not built yet:**
- `services/optimizer` (`microtune_optimizer`) — meant to hold the bandit/Bayesian optimization logic. Right now it's just a package stub.
- `services/shared` (`microtune_shared`) — code shared between api and optimizer. Also just a stub.
- `apps/dashboard` — a Next.js app that's currently the unmodified `create-next-app` starter, not wired to anything yet.

`ARCHITECTURE.md` has the real infra plan I'm building toward (Cloudflare Workers, Neon Postgres, ClickHouse, Fly.io) and what I'm deliberately punting on for now. Everything past this point in this README is the original product pitch/vision that got me excited about building this — think of it as direction, not a list of finished features.

## Running it

JS/TS side is a pnpm workspace via Turborepo:
```bash
pnpm install
pnpm build   # or: pnpm dev
```

Python side is a uv workspace:
```bash
uv sync --all-packages
cp services/api/.env.example services/api/.env   # fill in DATABASE_URL, e.g. a Neon Postgres connection string
uv run --project services/api alembic upgrade head
uv run --project services/api main.py
```

## Why I'm building this

Most A/B testing tools still need a human to come up with the experiment — "should the CTA be green or blue," "should the button move above the fold." The tool runs the test, but it never discovers the test. And there are probably hundreds of small design variables on any given page that quietly affect conversion, way more than any growth team has time to manually test one at a time.

So the question I'm chasing is: what if the website could search its own design space? Treat the whole page as a big parameter vector (font, size, weight, padding, radius, spacing, alignment...) and let an optimizer hill-climb toward whatever the goal metric is, instead of a human hand-picking each variant.

That search space blows up fast — even something modest like 20 tunable properties with 4 options each is over a trillion combinations — so brute force is out. The plan is to grow the optimizer in stages:

1. **Plain A/B tests** — change one property at a time, split traffic 50/50. Boring, but it's the foundation.
2. **Multi-armed bandits** (Thompson sampling, UCB, epsilon-greedy) — once a property has several candidate values, shift traffic toward whichever's winning instead of waiting for a full test to finish.
3. **Bayesian optimization** — treat the whole page as a black-box function from design to conversion rate, and since every evaluation costs real user traffic (expensive), pick the next candidate that's expected to teach you the most.
4. **Evolutionary search** — once there's a real population of variants, evolve them: keep what's working, mutate and recombine, cull what isn't.

A few things I care about getting right along the way:

- **Mutations have to be safe.** Every change stays inside a constrained range (font size ±15%, spacing ±20%, border radius 0-24px, etc.), and some things are just off-limits entirely — payment buttons, legal notices, forms, checkout, auth, nav routes. I never want this randomly breaking someone's site.
- **The design has to stay recognizable.** There should be some notion of visual distance between a candidate and the original, and the optimizer shouldn't be able to wander past it — otherwise you get a "high-converting" page that doesn't look like your brand anymore.
- **Attribution matters.** If ten things change at once and conversions go up, you have no idea what actually caused it. So early on I want mutations to stay sparse — one or two properties changed at a time — so results are interpretable.
- **It shouldn't just optimize clicks at the expense of everything else.** The eventual objective should balance conversion against engagement, bounce, and performance/layout cost, not just chase the one number.

Longer term, the interesting part isn't really CSS generation — it's that this is fundamentally a sequential decision-making problem where every "experiment" costs real user traffic. If it works across enough different sites, there's a genuinely interesting research angle: do certain classes of design changes (centering CTAs, more whitespace, bigger headings on short pages) generalize across sites with similar context, so a brand-new site could skip straight to trying the changes that are likely to work instead of starting from zero? That's the "learned optimization instead of blind optimization" version of this, and it's mathematically a proper multi-armed-bandit / contextual-bandit problem, which is part of what makes it fun.

## Stack

- **SDK**: TypeScript, aiming to stay under 20KB, handles DOM parsing, variant assignment, CSS mutation, and event tracking.
- **Backend**: FastAPI + Postgres now; ClickHouse is the plan for high-volume behavioral events once there's real traffic (see `ARCHITECTURE.md`).
- **Dashboard**: Next.js, React, Tailwind.
- **Optimization**: Python — NumPy, SciPy, scikit-learn, and eventually PyTorch/BoTorch for the Bayesian optimization stage.

## The pitch, if I had to say it in one line

MicroTune continuously discovers and tests tiny website design changes to find the version that converts best. It's not A/B testing software — the goal is for the system to generate the experiment, not just run the one a human already thought of.
