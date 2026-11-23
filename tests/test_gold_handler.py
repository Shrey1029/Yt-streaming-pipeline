import unittest
from unittest.mock import patch

from src.gold import handler as gold_handler


class TestGoldHandler(unittest.TestCase):
    def test_lambda_handler_requires_dt(self):
        with self.assertRaisesRegex(ValueError, "Missing required 'dt'"):
            gold_handler.lambda_handler({}, None)

    def test_lambda_handler_skips_when_rows_exist(self):
        with patch.object(
            gold_handler, "_partition_has_rows", return_value=100
        ), patch.object(gold_handler, "_run_and_wait") as mock_run:
            result = gold_handler.lambda_handler({"dt": "2026-11-19"}, None)

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["existing_rows"], 100)
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()