"""
Checks on data/README.md against the brief's Outputs line: "data/README.md
-- exact Kaggle dataset URL, expected filenames, where to place them" and
Inputs: "the 9 Olist CSV files, manually downloaded from Kaggle by the
user ... Kaggle auth is a manual, out-of-band step -- documented, not
scripted".
"""
import unittest

from _pg_helpers import DATA_DIR, all_csv_files

README_FILE = DATA_DIR / "README.md"


class DataReadmeTests(unittest.TestCase):
    def test_data_readme_exists(self):
        self.assertTrue(README_FILE.exists(), "data/README.md is missing")

    def test_mentions_a_kaggle_url(self):
        text = README_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "kaggle.com",
            text.lower(),
            "data/README.md does not reference a kaggle.com dataset URL",
        )

    def test_lists_every_expected_csv_filename(self):
        # Derived from the actual files already in data/ so this doesn't
        # hardcode a name the brief never specifies.
        csv_files = all_csv_files()
        self.assertTrue(csv_files, "no CSVs found in data/ to compare README against")
        text = README_FILE.read_text(encoding="utf-8")
        missing = [f.name for f in csv_files if f.name not in text]
        self.assertEqual(
            missing,
            [],
            f"data/README.md does not mention expected filenames: {missing}",
        )

    def test_mentions_where_to_place_the_files(self):
        text = README_FILE.read_text(encoding="utf-8")
        self.assertTrue(
            "data/" in text or "data\\" in text,
            "data/README.md does not say where to place the downloaded CSVs",
        )


if __name__ == "__main__":
    unittest.main()
