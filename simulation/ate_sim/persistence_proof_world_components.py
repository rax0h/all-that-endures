"""Bounded routing only; existing validators retain all proof authority."""
from . import persistence_lazy_identity_catalog as catalog

MAX_SOURCE_ROWS = 512
MAX_CATALOG_ROWS = 512
MAX_FRONTIER_ROWS = 512


def semantic_versions(versions, leases):
    # Prepared input may be a streamed SQL view. Never materialize an
    # unbounded batch merely to discover that its components exceed budget.
    if not leases or len(versions)-len(leases) > MAX_SOURCE_ROWS+MAX_CATALOG_ROWS:
        return versions
    return tuple(i for i in versions if (i['namespace'], i['typed_key']) not in leases)


def frontier_versions(versions):
    if len(versions) > MAX_SOURCE_ROWS+MAX_CATALOG_ROWS:
        return ()
    rows = []
    for item in versions:
        ns = item['namespace']
        if ns not in catalog.CATALOG_NAMESPACES or ns == catalog.OWNER_NAMESPACE:
            if len(rows) >= MAX_FRONTIER_ROWS:
                return ()
            rows.append(item)
    return tuple(rows)


def insertion_within_limits(versions, ordinary):
    if len(ordinary) > MAX_SOURCE_ROWS or len(versions) > MAX_SOURCE_ROWS+MAX_CATALOG_ROWS:
        return False
    sources, catalogs = len(ordinary), 0
    for item in versions:
        if item['namespace'] in catalog.CATALOG_NAMESPACES:
            catalogs += 1
        else:
            sources += 1
        if sources > MAX_SOURCE_ROWS or catalogs > MAX_CATALOG_ROWS:
            return False
    return True
