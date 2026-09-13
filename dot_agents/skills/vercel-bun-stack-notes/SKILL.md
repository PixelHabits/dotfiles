---
name: vercel-bun-stack-notes
description: Field notes from running TanStack Start plus Nitro on Vercel's Bun runtime with Workflow DevKit. Use when deploying to Vercel, configuring Nitro or Start, debugging cold starts, crons, durable workflows, or a function that dies at boot. These notes record what happened, not permanent law. Verify against current docs and installed source.
---

# Vercel, Bun, Start, Nitro: field notes

Each note below was true when written. The platform and the frameworks move fast. Re-verify the mechanism in the installed source or the docs page dated today before building on it.

## Shape that worked

- One TanStack Start app on Vite with the Nitro Vite plugin. Nitro is the host: handlers for machine routes, scheduled tasks, function rules, route rules, server assets. Start is UI plus server functions only.
- `vercel.json` stayed minimal: `bunVersion`, `buildCommand`, `framework: null`. Routing came from the Build Output API config that Nitro emits.
- Machine routes as Nitro handlers on a prefix. Router lookup preferred the specific prefix over the catch-all regardless of registration order.
- Route rules compiled to CDN rewrites and redirects with no function invocation. Useful for an analytics reverse proxy and for old-path redirects.
- Scheduled tasks compiled to Vercel crons that all hit one cron path with a secret header. One function rule covered every task's duration.
- Workflow DevKit ran on Bun once each generated function directory had a `node_modules` stub and the workflow runtime was set explicitly. Steps returned summaries, never large payloads.
- Server routes, `-`-prefixed co-located files, pathless layout routes for auth groups, and import protection for `*.server.ts` all came straight from the router source. Reading the local framework clone beat the web docs every time.

## What bit

- Nitro's Vercel preset emitted an older Bun runtime whenever `bunVersion` was set, unless the function runtime was also set explicitly in the Nitro config. Check the deployed runtime, not the build log.
- A deployment marked READY did not mean the function booted. The bundler left a live CommonJS `require` of an external in the SSR bundle; with no `node_modules` on the function the first request died before the error SDK initialized. Runtime logs were the only signal. Grep the built output for `require("...")` of non-builtins before shipping.
- A custom Start instance file silently disabled the framework's default CSRF middleware for server functions. Deleting the file restored it.
- SSR opt-outs cascade down the route tree; opt-ins do not. A parent set to client-only forces every child client-only.
- Configured Nitro handlers were static imports, so every function copy booted the whole API graph. Lazy handlers or scanned route files avoid that.
- The Nitro server entry was a catch-all route chained before the renderer, not a pre-router hook. A 404 from it fell through to the app's not-found page.
- Dashboard traps on a new project: a wrong framework preset aborted builds instantly; an unset Root Directory ignored the app's config and installed with an older Bun that could not read the lockfile.
- Dated beta Nitro releases changed behavior between builds. Pinning `compatibilityDate` and auditing each bump against the dist diff kept deploys reproducible.
- The Workflow builder bundled native add-ons and failed. Forwarding an `externalPackages` list needed a patch to the Nitro module at the time.
- Outbound OAuth token fetches with no timeout hung a task to its maximum duration with zero logs. Every outbound call gets a timeout.
- A "hung" task was a legitimate long run seen through short curl timeouts. Compute worst-case retry math before calling anything hung.
- Env changes needed a redeploy. A 401 from an alias meant the deployment predated the env change.
- Function-level alerts named the catch-all function and nothing else. Splitting functions by route prefix was the only way to get attribution.

## Platform features worth checking before designing

Fluid Compute with Active CPU pricing, Bun and Rust runtimes, containers via `Dockerfile.vercel`, Services (several services in one project), Cron Jobs, Workflow DevKit, Queues, Runtime Cache with tag invalidation, Routing Middleware on Bun, private Blob, Edge Config, Marketplace databases (Neon, Upstash), `vercel.ts` typed config, Rolling Releases, Sandbox, Connect for outbound OAuth. Availability and plan gating change. Read the docs page dated today.
