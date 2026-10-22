import random
import sys
import time
import tracemalloc
from pathlib import Path

# add the project root so the ranking module can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# import both ranking algorithms for performance comparison
from rescue_ranking import rank_candidates, rank_candidates_sorted

# use a fixed seed for reproducible benchmark datasets
random.seed(42)


# generate eligible water rescue candidates with different ages
def generate_animals(count):
    breeds = ["Labrador Retriever", "Newfoundland", "Chesapeake Bay Retriever"]

    return [
        {
            "animal_id": str(index),
            "animal_type": "Dog",
            "breed": random.choice(breeds),
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": random.randint(26, 156),
        }
        for index in range(count)
    ]


# measure execution time and peak memory usage
def measure_performance(algorithm, animals, category, k):
    tracemalloc.start()
    start = time.perf_counter()

    results = algorithm(animals, category, k)

    elapsed = time.perf_counter() - start
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return results, elapsed, peak_memory / 1024


# compare both algorithms across increasing dataset sizes
for size in [100, 1000, 10000]:
    animals = generate_animals(size)

    heap_results, heap_time, heap_memory = measure_performance(
        rank_candidates, animals, "water", 5
    )

    sorted_results, sorted_time, sorted_memory = measure_performance(
        rank_candidates_sorted, animals, "water", 5
    )

    # verify ranking consistency before reporting performance
    assert heap_results == sorted_results, "Ranking results do not match."

    print(f"\nDataset: {size:,} animals")
    print(f"Min-heap: {heap_time:.6f}s | {heap_memory:.2f} KB")
    print(f"Sorting:  {sorted_time:.6f}s | {sorted_memory:.2f} KB")
    print("Results match: True")
