# Embeddings — todo

Vector search / semantic matching infrastructure.

- Source: snacks (port)

## What it is

The vector-search primitive an app pulls in for semantic matching over its own data.

## To design

- [ ] Adopt the snacks embeddings module as this platform's implementation.
- [ ] Vector storage: pgvector in the shared Postgres vs. a separate store.
- [ ] Embedding-generation pipeline and which provider(s).
- [ ] Seam with the ontology — embedding an app's objects for search.
