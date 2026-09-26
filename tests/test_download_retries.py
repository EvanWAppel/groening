"""Network failures should not discard an otherwise successful warehouse build."""

import io
import urllib.error
from email.message import Message

import pytest

import build_warehouse


def http_error(code):
    return urllib.error.HTTPError("https://example.test/data", code, "upstream error", Message(), io.BytesIO())


@pytest.mark.parametrize("code", [500, 502, 503, 504])
def test_transient_server_error_recovers(network, caplog, code):
    opener, sleep = network
    response = io.BytesIO(b"test response")
    opener.side_effect = [http_error(code), response]
    result = build_warehouse._urlopen("https://example.test/data", {"User-Agent": "test"}, 12)
    assert result is response
    assert opener.call_count == 2
    sleep.assert_called_once_with(5)
    request = opener.call_args.args[0]
    assert request.full_url == "https://example.test/data"
    assert request.get_header("User-agent") == "test"
    assert opener.call_args.kwargs["timeout"] == 12
    assert str(code) in caplog.text


def test_persistent_outage_preserves_original_error(network):
    opener, sleep = network
    error = http_error(503)
    opener.side_effect = error
    with pytest.raises(urllib.error.HTTPError) as raised:
        build_warehouse._urlopen("https://example.test/data")
    assert raised.value is error
    assert opener.call_count == 4
    assert [call.args[0] for call in sleep.call_args_list] == [5, 10, 20]


@pytest.mark.parametrize("code", [400, 401, 403, 404, 429])
def test_other_http_errors_fail_immediately(network, code):
    opener, sleep = network
    error = http_error(code)
    opener.side_effect = error
    with pytest.raises(urllib.error.HTTPError) as raised:
        build_warehouse._urlopen("https://example.test/data")
    assert raised.value is error
    assert opener.call_count == 1
    sleep.assert_not_called()


def test_success_does_not_wait(network):
    opener, sleep = network
    assert build_warehouse._urlopen("https://example.test/data") is opener.return_value
    opener.assert_called_once()
    sleep.assert_not_called()


def test_certificate_error_is_not_retried(network):
    opener, sleep = network
    error = urllib.error.URLError("certificate verify failed")
    opener.side_effect = error
    with pytest.raises(urllib.error.URLError) as raised:
        build_warehouse._urlopen("https://example.test/data")
    assert raised.value is error
    opener.assert_called_once()
    sleep.assert_not_called()
