---
title: ADR-0001 Headless Runtime Only
status: active
owner: runtime-core
source_authority: README.md
summary: Decision to remove frontend and visualization ownership from the runtime repo.
---


# ADR-0001 — Headless Runtime Only

## Status

Accepted.

## Decision

VDM RT is a headless runtime repository. The old frontend and visualization adapter are removed from the runtime tree.

## Reason

The frontend was blocking the needed runtime swap. The runtime engine must be separable before replacing decoder output with motor-learning actuation.

## Consequences

- Future frontends must be clients.
- Runtime control belongs behind `control/` or explicit status/run artifacts.
- UI code must not own process launch, filesystem mutation, log tailing, or cognition.
