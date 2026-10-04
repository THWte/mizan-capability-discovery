# MIZAN Project Evaluation: Graphiti

## Project
- Name: Graphiti
- Repository: https://github.com/getzep/graphiti
- License: Apache-2.0
- Primary domain: Temporal Knowledge Graph for AI agents
- Decision: **EVALUATE STRONGLY (candidate for EXTEND)**

## 1. Capability fit
- Builds real-time knowledge graphs that evolve over time — entities, relationships,
  facts, and temporal validity windows.
- Affects MIZAN's **knowledge graph / case-knowledge-evolution layer** — directly
  matches the vision of "entity + relationship + fact + time + knowledge change as a
  case progresses."
- Fills a real, currently unaddressed gap: MIZAN has no temporal knowledge graph today.

## 2. Technical quality
- Apache-2.0, actively maintained by Zep.
- Designed specifically for agent memory with incremental, non-destructive updates
  (facts are invalidated over time rather than overwritten).
- Documentation and examples are reasonably mature; growing community adoption.

## 3. Security and privacy
- Can be self-hosted; works with graph databases (e.g., Neo4j) that can run locally.
- No inherent cloud dependency, but requires standing up a graph database.
- Needs its own data-handling review since it will store case-sensitive entities and
  relationships.

## 4. Integration fit
- Python-native, async-first — compatible with MIZAN's stack.
- Requires a graph DB backend (adds operational complexity).
- API is graph/entity-centric; will need an adapter layer to map MIZAN's case/document
  model into Graphiti's entity-episode-fact model.

## 5. Operational fit
- Local/offline: possible if the backing graph DB is self-hosted.
- Deployment complexity: medium-high (graph DB + service).
- Monitoring: standard observability still needed on top (pair with Langfuse).

## 6. Language / domain fit
- No Arabic-specific features; this is backend-agnostic graph infrastructure, so
  Arabic/legal entity quality depends entirely on MIZAN's own entity-extraction layer
  feeding it.

## 7. What MIZAN should take
- Temporal graph modeling approach (entity + relationship + fact + time)
- Fact invalidation-over-time pattern instead of destructive overwrites
- Agent-memory-as-graph architecture pattern

## 8. What MIZAN should ignore
- Any assumption that this becomes the *entire* agent memory system — adopt only the
  temporal graph layer that serves case knowledge, not a full memory platform swap

## 9. Strategic recommendation
### Decision: EVALUATE STRONGLY → likely EXTEND
### Why:
This is the closest existing match to MIZAN's core vision of time-aware legal
knowledge. It deserves a deep architectural evaluation before Phase 2 prototyping.

### Risks:
- Integration risk: medium (new graph DB operational dependency)
- Maintenance risk: low-medium (younger project than Docling/Langfuse)
- Data privacy risk: medium (stores sensitive case entities/relationships — needs
  explicit local-hosting validation)

### Suggested next step:
Architectural deep-dive + small sandbox prototype: model one real (anonymized) legal
case as entities/relationships/facts over time and evaluate query ergonomics.
