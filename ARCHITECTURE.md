# MicroTune — System Architecture

## Goals

This architecture is designed to satisfy three constraints simultaneously:

- **Scalable**: must handle the eventual real workload — the spikiest, highest-volume part of this system is *behavioral event ingestion* (every pageview + every click/scroll/conversion event, across potentially many customer sites), not the CRUD/dashboard side.
- **Sustainable / real product-shaped**: multi-tenant from the schema up (`project_id` as a first-class key everywhere), even though only one project (ours) exists at first. Retrofitting multi-tenancy later is expensive; designing for it now is free.
- **Cheap**: near-$0 at idle, and grows via usage-based pricing rather than provisioning fixed clusters. No component should require a standing bill before there's real traffic to justify it.

The resolution to "real scale" vs "cheap" is: pick **serverless / usage-billed managed services that are individually built for scale**, instead of either (a) a single fat VPS that's cheap now but caps out, or (b) a hand-rolled Kafka/ClickHouse cluster on AWS that's scalable but expensive to run idle. Every service below has a free or near-free tier and bills on usage, so cost tracks traffic.

## Overview

```
                                   ┌─────────────────────────┐
                                   │   Customer Website        │
                                   │   <script microtune sdk> │
                                   └────────────┬─────────────┘
                                                │
                     ┌──────────────────────────┼──────────────────────────┐
                     ▼                                                     ▼
        GET /config (variant assignment)                    POST /events (behavior tracking)
                     │                                                     │
                     ▼                                                     ▼
        ┌─────────────────────────────┐                    ┌─────────────────────────────┐
        │  Cloudflare Worker (edge)    │                    │  Cloudflare Worker (edge)    │
        │  - serves SDK from CDN       │                    │  - validates + tags event    │
        │  - reads variant weights     │                    │  - pushes to Queue           │
        │    from Upstash Redis cache  │                    └──────────────┬──────────────┘
        └──────────────┬───────────────┘                                    │
                        │ (cache miss only)                                  ▼
                        ▼                                       ┌─────────────────────────┐
              ┌──────────────────┐                              │  Cloudflare Queue        │
              │  FastAPI (Fly.io) │◄─────────────────────────────│  (buffers/batches)       │
              │  experiment CRUD  │                              └──────────────┬───────────┘
              │  + assignment API │                                             ▼
              └────────┬──────────┘                              ┌─────────────────────────┐
                       │                                          │ Consumer Worker → writes │
                       ▼                                          │ batched rows to ClickHouse│
              ┌──────────────────┐                              └──────────────┬───────────┘
              │   Neon Postgres   │                                             │
              │  (projects, exps, │◄────────────────────────────────────────────┘
              │  variants, arm    │   aggregated stats read back by optimizer
              │  posteriors)      │
              └────────┬──────────┘                              ┌─────────────────────────┐
                       │                                          │  ClickHouse Cloud         │
                       ▼                                          │  (raw event store,       │
              ┌──────────────────┐                                │  funnels, regret calc)   │
              │ Optimization      │◄───────────────────────────────┘
              │ Worker (Fly.io    │  reads aggregates, writes new
              │ scheduled machine,│  arm posteriors / candidate
              │ Python: bandits,  │  mutations back to Postgres
              │ BoTorch later)    │
              └───────────────────┘

              ┌──────────────────┐
              │ Dashboard         │──► reads via FastAPI ──► Postgres + ClickHouse
              │ (Next.js, Vercel) │
              └──────────────────┘
```

## Component Decisions

| Layer | Choice | Why cheap + scalable |
|---|---|---|
| SDK delivery + edge API | **Cloudflare Workers** | Free tier: 100k req/day, then $5/mo for 10M. Runs at the edge globally (low latency for variant assignment), scales automatically with zero ops. |
| Hot-path variant weights cache | **Upstash Redis** | Serverless, pay-per-request, free tier covers dev + small prod. Avoids hitting Postgres on every pageview. |
| Event ingestion buffer | **Cloudflare Queues** | Decouples traffic spikes from the analytical DB write path; consumer batches writes instead of one-row-per-event inserts. Pennies per million messages. |
| Raw behavioral event store | **ClickHouse Cloud** (or Tinybird as a managed alternative) | Purpose-built for exactly this workload (high-volume append-only event analytics, funnel/regret queries over millions of rows). Free tier + usage billing — this is the piece that would be expensive to run "for real" on a VPS but is the whole reason NOT to put raw events in Postgres. |
| Relational source of truth | **Neon Postgres (serverless)** | Projects, experiments, variant/constraint configs, users, arm posterior summaries (aggregated numbers, not raw events). Scales to zero, branch-per-PR for dev, generous free tier. `project_id` on every table from day 1 for multi-tenancy. |
| API backend | **FastAPI on Fly.io** | Cheap always-on-or-scale-to-zero containers, deploy close to Neon's region. Keeps the spec's FastAPI choice; avoids rewriting in JS. |
| Optimization engine | **Python, scheduled Fly Machines** | Bandit updates (Thompson/UCB) are cheap and can run every few minutes; heavier Bayesian optimization / candidate generation runs on a longer interval. Not on the request path — no per-pageview compute cost. |
| Dashboard | **Next.js on Vercel** | Free tier is generous for a low-traffic internal/customer dashboard; reads through the FastAPI API. |
| Monorepo tooling | **pnpm workspaces + Turborepo** for `sdk/` + `dashboard/`; separate `uv`-managed Python project for `api/` + `optimizer/` | Keeps JS and Python tooling idiomatic instead of forcing one build system over both. |

## Key Design Principles

1. **Multi-tenant from day one**: every Postgres table keyed by `project_id`; the edge config cache key is `{project_id}:{experiment_id}`. Costs nothing extra now, avoids a painful migration later.
2. **Separate hot path from cold path**: variant *assignment* (read-heavy, latency-sensitive, must be cheap at scale) is served from Redis/edge cache — never hits Postgres or ClickHouse per request. Event *ingestion* is write-heavy and async via the Queue — never blocks the visitor's page load.
3. **Aggregates in Postgres, raw events in ClickHouse**: keeps Postgres small and fast (it only ever stores rollups: impressions/conversions per arm), while ClickHouse absorbs unbounded raw event volume cheaply.
4. **Optimization is scheduled, not synchronous**: bandit/Bayesian updates never run inline with a user request — this is what keeps compute cost flat regardless of traffic.
5. **No component requires a standing fixed-cost cluster**: every piece above is either edge-serverless or scale-to-zero, so cost is ~$0 until there's real usage, and each piece individually has headroom into millions of events/day before needing a tier upgrade — no architectural rewrite required to go from "side project" to "real product," only config/tier changes.

## Deliberately Deferred

- Auth/billing for multi-tenant customers (Clerk/Supabase Auth are the likely cheap options when needed — noted for later, not built now).
- Multi-region deployment of Fly.io/Neon (single region is fine until latency data says otherwise).
- Visual-distance / screenshot-similarity checks (Playwright-based, run on-demand rather than always-on — worth its own design pass when we build the constraint engine).
