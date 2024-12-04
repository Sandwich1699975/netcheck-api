
from web import PORT
import requests
import pytest
import time
import re


@pytest.mark.dependency()
def test_port_valid():
    REGEX = r"^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$"
    assert re.match(REGEX, PORT)


@pytest.mark.dependency(depends=["test_port_valid"])
def test_web_starts():
    URL_INDEX = f"http://0.0.0.0:{PORT}"
    try:
        response = requests.get(URL_INDEX, timeout=4)
        assert response.ok
    except requests.RequestException as e:
        print(f"Error: {e}")
        pytest.fail(f"Failed to connect to {URL_INDEX}: {e}", pytrace=True)
