import unittest
from unittest.mock import Mock, patch

import check_update


class FetchRssWithRetryTests(unittest.TestCase):
    @patch("check_update.time.sleep")
    @patch("check_update.requests.get")
    def test_request_timeout_is_retried(self, get, sleep):
        get.side_effect = check_update.requests.exceptions.Timeout()

        result = check_update.fetch_rss_with_retry("https://example.test/feed", retries=2, delay=0)

        self.assertIsNone(result)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args.kwargs["timeout"], (10, 30))
        self.assertEqual(sleep.call_count, 2)

    @patch("check_update.requests.get")
    def test_successful_response_is_parsed(self, get):
        response = Mock(content=b"<rss><channel></channel></rss>")
        response.raise_for_status.return_value = None
        get.return_value = response

        with patch("check_update.feedparser.parse") as parse:
            parse.return_value.entries = [object()]
            result = check_update.fetch_rss_with_retry("https://example.test/feed", retries=1)

        self.assertIs(result, parse.return_value)
        parse.assert_called_once_with(response.content)


if __name__ == "__main__":
    unittest.main()
