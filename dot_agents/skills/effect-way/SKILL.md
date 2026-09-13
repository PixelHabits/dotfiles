---
name: effect-way
description: Effect v4 conventions for TypeScript server code. Schema at every edge, Config over process.env, the language service switched on and obeyed, and the hidden gotchas. Use when writing or reviewing Effect code, schemas, config loading, generated vendor clients, or when setting up the Effect LSP in a repository.
---

# Effect, the way I use it

Effect v4. Exact pins, no caret. Read the version from the lockfile. Never assume one. Read the installed `node_modules/effect` source over memory; the API moves between release candidates.

## Firm

- Effect Schema is the one model. The same Schema serves the HTTP edge, the form edge, and the database row. Form input type is the Encoded side, domain type is the Type side. `Schema.toStandardSchemaV1` feeds TanStack Form and Router. Database row Schemas derive from tables (`drizzle-orm/effect-schema`), never hand-written.
- Config, not environment reads. Server keys come through `Config.*` (the Effect answer to t3-env): one composition root, fail at boot, redacted where secret. Browser build-time keys stay a separate typed module.
- Language service on, and obeyed. `@effect/language-service` as a tsconfig plugin on the native compiler, `effect-tsgo patch` in `prepare`, every diagnostic at warning, warnings fail typecheck. Per-file `overrides` only for real Promise hosts (test files, workflow step bodies). Never `*:skip-file` on code you own. A diagnostic is a design signal, not noise.
- Dates: a `Temporal.PlainDate` codec at the boundary; an impossible date is a validation problem. Effect has no Temporal Schema; write the codec (`Schema.declare` plus `decodeTo`).
- Wire numbers: `Schema.Finite` or an int check, never bare `Schema.Number`. Identifier codes are `Schema.String`.

## Direction, adopt per repository

- Server code Effect end to end. One Promise door per host edge (HTTP handler, scheduled task, workflow step). No `runPromise` inside modules. No dual Promise and Effect surfaces. The browser stays Promise on purpose.
- HTTP API as `HttpApi` groups. RFC 9457 problem responses for every non-2xx. Two caller outcomes only: success and needs-review. Everything else is an operator fault that alerts.
- Vendor clients generated from OpenAPI with `@effect/openapi-generator`, corrected with `--patch` JSON patches that live in the package's generate script. The package is the boundary; its typed exports are the canonical shape.
- Telemetry through the Sentry Effect tracer and logger layers over one SDK init. Failed root programs get captured by a tracer decorator, not by per-call code.

## Hidden gotchas

- Effect `Random` is not cryptographic. Secrets, state, nonces, PKCE: Web Crypto. The `cryptoRandomUUID` diagnostic is about injectability, not this.
- `Effect.timeout` must wrap execute plus body decode. A header-only response hangs past the deadline otherwise.
- `Effect.fork` is gone: `forkChild`, `forkScoped`, `forkDetach`, `forkIn`.
- `FetchHttpClient.Fetch` caches the first fetch per runtime. Test layers provide a call-time lookup.
- Rounding defaults to half-from-zero. Pass half-even explicitly for money.
- `optionalKey` rejects a present key holding `undefined`. Spread conditionally.
- `TaggedUnion` hardcodes `_tag`. A discriminator with another name needs `Union` of literal structs.
- Generated clients: `default` never makes a member required; schemaless error responses generate void successes; patch both.
- `toStandardJSONSchemaV1` describes the decoded side. Response models need `toEncoded` or the OpenAPI document lies about the wire.
- `Schema.Error` with an `httpApiStatus` annotation is how a typed failure becomes a status. Annotate in server-only files, never in isomorphic error modules.

## Verify before relying

- Pinned version: `grep -o '"effect@[^"]*"' bun.lock | sort -u`
- Diagnostics alive: run the repository typecheck and expect language-service output.
- Behavior of a helper: open the installed source file, not a doc from memory.
