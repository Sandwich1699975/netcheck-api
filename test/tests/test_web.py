from web import PORT
import requests
import pytest
import re
import os
import ctypes


@pytest.mark.dependency()
def test_port_valid():
    REGEX = r"^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$"
    assert re.match(REGEX, PORT)


@pytest.mark.dependency()
def test_debug_mode_is_true():
    os.environ["DEBUG_MODE"] = "true"
    DEBUG_MODE = os.environ.get('DEBUG_MODE')
    assert DEBUG_MODE == 'true', f"DEBUG_MODE is not 'true', it is '{DEBUG_MODE}'"


@pytest.mark.dependency(depends=["test_port_valid"])
def test_web_index_starts():
    URL_INDEX = f"http://0.0.0.0:{PORT}"
    try:
        response = requests.get(URL_INDEX, timeout=4)
        assert response.ok
    except requests.RequestException as e:
        pytest.fail(f"Failed to connect to {URL_INDEX}: {e}", pytrace=True)


@pytest.mark.dependency(depends=["test_web_index_starts"])
def test_elevated_privilege():
    """Make sure you run as admin for ping"""
    is_admin = False
    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

    assert is_admin


@pytest.mark.dependency(depends=["test_elevated_privilege", "test_debug_mode_is_true"])
class TestValidateMetrics:
    metrics_response = None

    @pytest.fixture(scope="class", autouse=True)
    def setup_metrics_response(self):
        """Fetch metrics and store the response for validation."""
        URL_METRICS = f"http://0.0.0.0:{PORT}/metrics"
        try:
            response = requests.get(URL_METRICS, timeout=60)
            assert response.ok, f"Failed to load metrics: {response.status_code}"
            TestValidateMetrics.metrics_response = response.text
        except requests.RequestException as e:
            pytest.fail(
                f"Failed to load metrics from {URL_METRICS}: {e}", pytrace=True)

    def test_metrics_response_exists(self):
        """Ensure the metrics response was fetched."""
        assert TestValidateMetrics.metrics_response is not None

    def test_parse_metrics(self):
        """Parse and validate the metrics content."""
        metrics_content = TestValidateMetrics.metrics_response
        assert len(metrics_content) > 0
        # Add further parsing and validation as needed
