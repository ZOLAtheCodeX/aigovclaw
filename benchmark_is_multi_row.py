import timeit
import dis

def original_is_multi_row(artifact_type: str) -> bool:
    return artifact_type in (
        "risk-register",
        "soa",
        "nonconformity-register",
    )

def optimized_is_multi_row(artifact_type: str) -> bool:
    return artifact_type in {
        "risk-register",
        "soa",
        "nonconformity-register",
    }

print("--- Original bytecode ---")
dis.dis(original_is_multi_row)
print("--- Optimized bytecode ---")
dis.dis(optimized_is_multi_row)

print("\n--- Benchmark ---")
n = 10_000_000

t_orig_hit = timeit.timeit('original_is_multi_row("soa")', globals=globals(), number=n)
t_orig_miss = timeit.timeit('original_is_multi_row("other")', globals=globals(), number=n)
t_opt_hit = timeit.timeit('optimized_is_multi_row("soa")', globals=globals(), number=n)
t_opt_miss = timeit.timeit('optimized_is_multi_row("other")', globals=globals(), number=n)

print(f"Original (hit):  {t_orig_hit:.4f}s")
print(f"Original (miss): {t_orig_miss:.4f}s")
print(f"Optimized (hit): {t_opt_hit:.4f}s")
print(f"Optimized (miss): {t_opt_miss:.4f}s")
