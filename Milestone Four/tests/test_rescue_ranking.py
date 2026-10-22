import unittest

from rescue_ranking import calculate_score, rank_candidates, rank_candidates_sorted


class TestRescueRanking(unittest.TestCase):

    # create a valid water rescue candidate for testing
    def setUp(self):
        self.animal = {
            "animal_id": "CS499-TEST-001",
            "animal_type": "Dog",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 78,
        }

    # verify a matching breed and preferred age receive their expected points
    def test_full_suitability_score(self):
        self.assertEqual(calculate_score(self.animal, "water"), 9)

    # verify an eligible animal outside the preferred age receives fewer points
    def test_partial_suitability_score(self):
        animal = {**self.animal, "age_upon_outcome_in_weeks": 130}
        self.assertEqual(calculate_score(animal, "water"), 7)

    # verify missing age data cannot produce a suitability score
    def test_missing_age(self):
        animal = {**self.animal}
        del animal["age_upon_outcome_in_weeks"]
        self.assertEqual(calculate_score(animal, "water"), 0)

    # verify the heap returns no candidates for an empty dataset
    def test_empty_dataset(self):
        self.assertEqual(rank_candidates([], "water", 5), [])

    # verify fewer candidates than requested are returned correctly
    def test_small_dataset(self):
        results = rank_candidates([self.animal], "water", 5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["score"], 9)

    # verify identical scores preserve the original animal order
    def test_identical_scores(self):
        animals = [{**self.animal, "animal_id": str(index)} for index in range(10)]
        results = rank_candidates(animals, "water", 5)
        ids = [result["animal"]["animal_id"] for result in results]
        self.assertEqual(ids, ["0", "1", "2", "3", "4"])

    # verify the heap and sorting algorithms return matching results
    def test_heap_matches_sorting(self):
        animals = [
            {
                **self.animal,
                "animal_id": str(index),
                "age_upon_outcome_in_weeks": 78 if index % 2 == 0 else 130,
            }
            for index in range(10)
        ]
        self.assertEqual(
            rank_candidates(animals, "water", 5),
            rank_candidates_sorted(animals, "water", 5),
        )


if __name__ == "__main__":
    unittest.main()
