import timeit

TUPLE_TYPES = (
    "audit-log-entry",
    "risk-register-row",
    "SoA-row",
    "AISIA-section",
    "role-matrix",
    "review-minutes",
    "nonconformity-record",
    "KPI",
    "gap-assessment",
    "review-package",
    "metrics-report",
    "soa",
    "aisia",
)

FROZENSET_TYPES = frozenset(TUPLE_TYPES)

def benchmark_tuple():
    return "gap-assessment" in TUPLE_TYPES

def benchmark_frozenset():
    return "gap-assessment" in FROZENSET_TYPES

def benchmark_tuple_miss():
    return "non-existent" in TUPLE_TYPES

def benchmark_frozenset_miss():
    return "non-existent" in FROZENSET_TYPES

if __name__ == "__main__":
    iterations = 10_000_000

    tuple_time = timeit.timeit(benchmark_tuple, number=iterations)
    frozenset_time = timeit.timeit(benchmark_frozenset, number=iterations)

    print(f"Tuple lookup time: {tuple_time:.4f}s")
    print(f"Frozenset lookup time: {frozenset_time:.4f}s")
    print(f"Speedup: {tuple_time/frozenset_time:.2f}x")

    print("\nMisses:")
    tuple_miss_time = timeit.timeit(benchmark_tuple_miss, number=iterations)
    frozenset_miss_time = timeit.timeit(benchmark_frozenset_miss, number=iterations)
    print(f"Tuple miss time: {tuple_miss_time:.4f}s")
    print(f"Frozenset miss time: {frozenset_miss_time:.4f}s")
    print(f"Speedup (miss): {tuple_miss_time/frozenset_miss_time:.2f}x")
