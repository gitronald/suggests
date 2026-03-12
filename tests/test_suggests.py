"""Tests for suggests.suggests module."""

from __future__ import annotations

from unittest.mock import patch

from suggests.suggests import (
    get_bing_url,
    get_google_url,
    get_suggests,
    prepare_qry,
    sleep_random,
)


class TestPrepareQry:
    def test_basic_encoding(self):
        assert prepare_qry("hello world") == "hello+world"

    def test_special_characters(self):
        result = prepare_qry("what is 2+2?")
        assert "+" in result or "%2B" in result
        assert "%3F" in result

    def test_empty_string(self):
        assert prepare_qry("") == ""


class TestGetGoogleUrl:
    def test_default_params(self):
        url = get_google_url()
        assert "google.com/complete/search" in url
        assert "hl=en" in url
        assert "sclient=psy-ab" in url
        assert url.endswith("q=")

    def test_custom_language(self):
        url = get_google_url(hl="de")
        assert "hl=de" in url


class TestGetBingUrl:
    def test_default_params(self):
        url = get_bing_url()
        assert "bing.com/AS/Suggestions" in url
        assert "mkt=en-us" in url
        assert url.endswith("q=")

    def test_custom_market(self):
        url = get_bing_url(mkt="es-es")
        assert "mkt=es-es" in url


class TestSleepRandom:
    @patch("suggests.suggests.time.sleep")
    def test_calls_sleep(self, mock_sleep):
        sleep_random(0.1, 0.2)
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 0.1 <= sleep_time <= 0.2


class TestGetSuggests:
    @patch("suggests.suggests.requester")
    @patch("suggests.suggests.parsing")
    def test_returns_dict_with_metadata(self, mock_parsing, mock_requester):
        mock_requester.return_value = "<html>response</html>"
        mock_parsing.parse_bing.return_value = {
            "suggests": ["dog toys"],
            "self_loops": [],
            "tags": [],
        }

        result = get_suggests("dog", source="bing", sleep=0.01)

        assert result["qry"] == "dog"
        assert result["source"] == "bing"
        assert "datetime" in result
        assert result["suggests"] == ["dog toys"]

    @patch("suggests.suggests.requester")
    @patch("suggests.suggests.parsing")
    def test_google_source(self, mock_parsing, mock_requester):
        mock_requester.return_value = [
            "dog",
            [["dog toys", 0, []]],
            {},
        ]
        mock_parsing.parse_google.return_value = {
            "suggests": ["dog toys"],
            "self_loops": [],
            "tags": [],
        }

        result = get_suggests("dog", source="google", sleep=0.01)
        assert result["source"] == "google"
        mock_parsing.parse_google.assert_called_once()
