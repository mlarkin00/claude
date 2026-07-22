# Design Deep Dives

Reference material for specific design concerns. Read the relevant section when a design requires depth in that area — do not load the entire file for every design.

## Table of Contents

1. [System Architecture Patterns](#system-architecture-patterns)
2. [Data Model Design](#data-model-design)
3. [API Design](#api-design)
4. [Scalability Planning](#scalability-planning)
5. [Design Pattern Selection](#design-pattern-selection)

---

## System Architecture Patterns

### Monolith vs. Services

Use a monolith when:

- The team is small (< 5 engineers)
- The domain is not yet well understood
- Deployment simplicity matters more than independent scaling

Use services when:

- Different components have fundamentally different scaling needs
- Teams need to deploy independently
- The domain boundaries are well understood and stable

The most common mistake is splitting too early. A well-structured monolith with clear module boundaries can be split later with less pain than premature services cause upfront.

### Layered Architecture

Standard layers and their responsibilities:

| Layer                 | Responsibility                                      | Depends On              |
| :-------------------- | :-------------------------------------------------- | :---------------------- |
| Presentation / API    | Request parsing, response formatting, auth          | Application             |
| Application / Service | Business logic orchestration, use case coordination | Domain                  |
| Domain / Model        | Core business rules, entities, value objects        | Nothing                 |
| Infrastructure        | Database, external APIs, file system, messaging     | Domain (via interfaces) |

The critical rule: dependencies point inward. Infrastructure implements interfaces defined by the domain, never the reverse.

### Event-Driven Architecture

Use when:

- Operations can be processed asynchronously
- Multiple consumers need to react to the same event
- Decoupling producers from consumers matters

Key decisions:

- **Event bus vs. message queue**: Event buses (pub/sub) for fan-out; message queues for work distribution
- **Event schema**: Define schemas upfront. Schema evolution is harder to retrofit than to plan
- **Ordering guarantees**: Know whether your system requires ordered processing. Most don't — and paying for ordering you don't need adds complexity

---

## Data Model Design

### Schema Design Checklist

- [ ] Every table has a primary key strategy defined (auto-increment, UUID, ULID, etc.)
- [ ] Foreign key relationships have explicit ON DELETE behavior
- [ ] Timestamps use UTC and include timezone information
- [ ] Nullable columns are justified — default to NOT NULL
- [ ] Indexes exist for every WHERE clause in known query patterns
- [ ] Composite indexes match query column order (leftmost prefix rule)
- [ ] Enums are stored as strings, not integers (readability and migration safety)
- [ ] JSON columns are justified — structured columns are preferred for queryable data

### Normalization Guidance

- **3NF by default.** Denormalize only when you have measured performance data showing a join is the bottleneck.
- **Denormalization candidates:** Read-heavy data accessed together, aggregated counts, cached computations. Always document what is denormalized and what process keeps it in sync.

### Migration Safety

- Never rename a column in production in one step. Add the new column, backfill, update code, drop the old column.
- Never add a NOT NULL column without a default to a populated table.
- Test migrations against a copy of production data, not an empty schema.
- Migrations must be reversible. If a migration cannot be reversed, document why and get explicit approval.

---

## API Design

### REST Endpoint Conventions

```
GET    /resources          → List (with pagination, filtering)
POST   /resources          → Create
GET    /resources/{id}     → Read one
PUT    /resources/{id}     → Full replace
PATCH  /resources/{id}     → Partial update
DELETE /resources/{id}     → Delete

GET    /resources/{id}/subresources → List related
```

### Request/Response Patterns

**Successful response:**

```json
{
  "data": { ... },
  "meta": { "request_id": "abc123" }
}
```

**List response with pagination:**

```json
{
  "data": [ ... ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 142
  }
}
```

**Error response:**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable explanation",
    "details": [
      { "field": "email", "message": "Must be a valid email address" }
    ]
  }
}
```

### Status Code Quick Reference

| Code | When to Use                                          |
| :--- | :--------------------------------------------------- |
| 200  | Successful GET, PUT, PATCH, DELETE                   |
| 201  | Successful POST that created a resource              |
| 204  | Successful DELETE with no response body              |
| 400  | Malformed request (bad JSON, missing required field) |
| 401  | Missing or invalid authentication                    |
| 403  | Authenticated but not authorized                     |
| 404  | Resource does not exist                              |
| 409  | Conflict (duplicate, version mismatch)               |
| 422  | Request is well-formed but fails validation          |
| 429  | Rate limited                                         |

### Versioning

Prefer URL-based versioning (`/v1/resources`) for external APIs. For internal APIs, avoid versioning — change the contract and update all consumers.

---

## Scalability Planning

### Capacity Estimation Template

Use when the design must justify infrastructure choices:

```
Users:          _____ DAU
Requests/user:  _____ per day
Total requests: _____ per day → _____ RPS (÷ 86400)
Peak RPS:       _____ (typically 3x average)

Storage per record: _____ bytes
Records per day:    _____
Daily growth:       _____ MB
1-year projection:  _____ GB
```

### Scaling Strategies by Bottleneck

| Bottleneck      | First Response                      | Second Response                  |
| :-------------- | :---------------------------------- | :------------------------------- |
| CPU             | Horizontal scaling (more instances) | Algorithm optimization           |
| Memory          | Caching strategy (Redis/Memcached)  | Data structure optimization      |
| Database reads  | Read replicas + caching             | Denormalization                  |
| Database writes | Write batching                      | Sharding by tenant/partition key |
| Network         | CDN for static assets               | Compression, payload reduction   |
| Storage         | Object storage (S3/GCS)             | Tiered storage, archival         |

### Caching Decision Tree

1. Is the data read more than 10x for every write? → Cache candidate
2. Can the application tolerate stale data? → If yes, use TTL-based expiration
3. Can stale data cause correctness problems? → If yes, use write-through or invalidation
4. Is the computation expensive (> 100ms)? → Cache the result

---

## Design Pattern Selection

Only reach for a pattern when you have a specific problem it solves. The table below maps problems to patterns.

### Object Creation Problems

| Problem                                     | Pattern   | Example                             |
| :------------------------------------------ | :-------- | :---------------------------------- |
| Too many constructor parameters             | Builder   | Config objects, query construction  |
| Need different variants of the same thing   | Factory   | User types, notification channels   |
| Object creation is expensive and repetitive | Prototype | Game characters, document templates |

### Structure Problems

| Problem                                              | Pattern   | Example                                         |
| :--------------------------------------------------- | :-------- | :---------------------------------------------- |
| Incompatible interfaces that must work together      | Adapter   | Third-party library integration                 |
| Need to add behavior without modifying existing code | Decorator | Logging, caching, auth wrappers                 |
| Complex subsystem needs a simple entry point         | Facade    | Email service wrapping SMTP + templates + queue |
| Need controlled access to an object                  | Proxy     | Caching proxy, auth proxy, lazy loading         |

### Behavior Problems

| Problem                                     | Pattern                 | Example                                 |
| :------------------------------------------ | :---------------------- | :-------------------------------------- |
| Multiple algorithms for the same task       | Strategy                | Shipping calculators, auth providers    |
| One event needs to notify many listeners    | Observer                | Webhooks, UI event systems              |
| Need undo/redo or operation queueing        | Command                 | Text editors, task queues               |
| Multiple handlers for a request in sequence | Chain of Responsibility | Middleware stacks, validation pipelines |
| Algorithm skeleton with varying steps       | Template Method         | Data parsers, report generators         |

### When NOT to Use Patterns

- The code is simple and works. Three similar `if` branches do not need a Strategy pattern.
- Only one implementation exists today. Do not abstract for hypothetical future variants.
- The pattern adds more code than it saves. Patterns are tools, not goals.
