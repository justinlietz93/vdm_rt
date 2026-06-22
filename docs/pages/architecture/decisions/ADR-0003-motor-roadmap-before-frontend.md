---
title: ADR-0003 Motor Roadmap Before Frontend
status: active
owner: runtime-core
source_authority: docs/pages/roadmap/motor-learning-roadmap.md
summary: Decision to implement motor-learning proof before a new frontend.
---


# ADR-0003 — Motor Roadmap Before Frontend

## Status

Accepted.

## Decision

The motor-learning upgrade should be implemented and tested in the headless runtime before any new frontend is built.

## Reason

A frontend can easily hide decoder-like shortcuts by presenting polished output. The headless runtime must first prove trace formation, release, rendering, reafference, and correction as separate channels.

## Consequences

- Build proof through tests and run artifacts first.
- A future frontend is only a viewer/control client.
- No UI feature can become a substitute for actuator learning.
