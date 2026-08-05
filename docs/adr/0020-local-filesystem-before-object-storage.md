# ADR 0020: Local filesystem lake before object storage
## Context
The platform needs to prove storage and lineage contracts before adopting cloud operations.
## Problem
Starting with S3, Blob, GCS, or an object-storage server would mix semantics with credentials, networking, and deployment.
## Alternatives considered
Cloud SDKs, MinIO, database blobs, and repository-local files were considered.
## Decision
Implement only `LocalFilesystemLakeStore` behind a narrow storage-neutral protocol.
## Consequences
Tests are fast and isolated; production durability and multi-host access are intentionally absent.
## Tradeoffs
Atomic rename is local-filesystem behavior and must later map to object-store conditional writes and pointer publication.
## Future migration implications
An object-store adapter must preserve paths, checksums, immutability, manifests, and activation semantics without changing transformations.
