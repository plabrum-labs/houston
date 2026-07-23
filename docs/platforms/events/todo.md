# Events — todo

Event bus / audit log — auto-fired on CRUD and state-machine transitions; the pub/sub backbone
other platforms subscribe to.

- Source: snacks (promoted to core platform)

## What it is

Already emitted off CRUD / state-machine transitions in snacks for audit. Promoted because it is
also the backbone Automate, Approvals, Notifications, and Writeback subscribe to once built.

## To design

- [ ] Port the snacks event / audit emission to Go.
- [ ] The subscription / pub-sub surface other platforms consume.
- [ ] Delivery guarantees, ordering, and replay / audit-query model.
- [ ] Seam with the ontology's actions and state machines as event sources.

## Open questions

- Transport: Redis-backed, Postgres-backed, or both.
