import unittest
from src.validator import validate


class TestDatasetValidation(unittest.TestCase):

    def test_validation_after_generation(self):
        # Run after generating the dataset from the repository root.
        errors, counts = validate()

        self.assertFalse(errors, errors)
        self.assertGreater(counts.get("tickets", 0), 0)


if __name__ == "__main__":
    unittest.main()