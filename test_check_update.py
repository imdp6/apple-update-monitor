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
        self.assertEqual(sleep.call_count, 1)

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


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.item = check_update.feedparser.FeedParserDict(
            id="new-id", title="iOS / iPadOS? #1", link="https://example.test/?a=1&b=2",
            published="Thu, 22 Oct 2026", published_parsed=(2026, 10, 22, 0, 0, 0, 0, 0, 0)
        )

    @patch("check_update.requests.get")
    def test_notification_encodes_path_and_query(self, get):
        get.return_value.json.return_value = {"code": 200}
        check_update.push_update("test-key", self.item)
        url = get.call_args.args[0]
        self.assertIn("iOS%20%2F%20iPadOS%3F%20%231", url)
        self.assertEqual(get.call_args.kwargs["params"],
                         {"url": self.item.link, "group": "AppleUpdate"})

    @patch("check_update.requests.get")
    def test_http_error_does_not_expose_secret(self, get):
        get.return_value.raise_for_status.side_effect = check_update.requests.HTTPError(
            "https://api.day.app/secret-key/title"
        )
        with self.assertRaises(RuntimeError) as error:
            check_update.push_update("secret-key", self.item)
        self.assertNotIn("secret-key", str(error.exception))

    @patch("check_update.requests.get")
    def test_api_rejection_and_invalid_json_are_failures(self, get):
        for result in ({"code": 400}, [], ValueError("invalid JSON")):
            with self.subTest(result=result):
                get.return_value.json.side_effect = result if isinstance(result, Exception) else None
                get.return_value.json.return_value = result
                with self.assertRaises(RuntimeError):
                    check_update.push_update("test-key", self.item)

    @patch.dict("os.environ", {"BARK_KEY": "test-key"})
    @patch("check_update.save_last_id")
    @patch("check_update.load_last_id", return_value="old-id")
    @patch("check_update.fetch_rss_with_retry")
    @patch("check_update.requests.get")
    def test_failed_batch_keeps_previous_id_for_retry(self, get, fetch, load, save):
        older = check_update.feedparser.FeedParserDict(self.item, id="older-id")
        fetch.return_value.entries = [self.item, older]
        success = Mock()
        success.json.return_value = {"code": 200}
        get.side_effect = [success, check_update.requests.Timeout("secret URL")]
        with self.assertRaises(RuntimeError):
            check_update.main()
        self.assertEqual(get.call_count, 2)
        save.assert_not_called()

    @patch.dict("os.environ", {"BARK_KEY": "test-key"})
    @patch("check_update.save_last_id")
    @patch("check_update.load_last_id", return_value="old-id")
    @patch("check_update.fetch_rss_with_retry")
    @patch("check_update.requests.get")
    def test_successful_batch_advances_id(self, get, fetch, load, save):
        fetch.return_value.entries = [self.item]
        get.return_value.json.return_value = {"code": 200}
        check_update.main()
        save.assert_called_once_with("new-id")

    @patch("check_update.save_last_id")
    @patch("check_update.fetch_rss_with_retry", return_value=None)
    def test_rss_failure_is_reported(self, fetch, save):
        with self.assertRaisesRegex(RuntimeError, "Failed to fetch RSS"):
            check_update.main()
        save.assert_not_called()

    @patch.dict("os.environ", {}, clear=True)
    @patch("check_update.load_last_id", return_value="old-id")
    @patch("check_update.fetch_rss_with_retry")
    def test_missing_key_is_reported(self, fetch, load):
        fetch.return_value.entries = [self.item]
        with self.assertRaisesRegex(RuntimeError, "BARK_KEY"):
            check_update.main()


if __name__ == "__main__":
    unittest.main()
