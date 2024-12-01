import signal
import requests
import threading
import logging
import os
import flask
import re
import metrics
import datetime
import waitress
from typing import Optional
from classes.metric import Metric
from prometheus_client import make_wsgi_app
from classes.metric_ping import MetricPing
from classes.metric_speedtest import MetricSpeedtest
from classes.metric import Metric
from requests.auth import HTTPBasicAuth


app = flask.Flask("Netcheck-Exporter")
PORT = os.getenv('SPEEDTEST_PORT', 9798)


def initialise_globals() -> None:
    global speedtest_cache_until, ping_cache_until
    speedtest_cache_until = datetime.datetime.fromtimestamp(0)
    ping_cache_until = datetime.datetime.fromtimestamp(0)
    global metric_ping, metric_speedtest
    metric_ping = MetricPing()
    metric_speedtest = MetricSpeedtest(os.environ.get("DEBUG_MODE") == "true")


def initialise_cache_variables() -> None:
    """Initialise the default values of the cache variables
    """
    # Cache metrics for how long (seconds)?
    # Speedtests are rate limited. Do not run more than one per hour per IP address
    SPEEDTEST_GLOBAL_CACHE_SECONDS = int(
        os.environ.get('SPEEDTEST_CACHE_FOR', 3600))
    update_speedtest_delta(SPEEDTEST_GLOBAL_CACHE_SECONDS)

    PING_CACHE_SECONDS = int(os.environ.get('PING_CACHE_FOR', 15))
    update_ping_delta(PING_CACHE_SECONDS)


def update_speedtest_delta(CACHE_SECONDS: int) -> None:
    """Updates the global speedtest cache timedelta object with new second duration

    Args:
        CACHE_SECONDS (int): How long should the cache duration be?
    """
    global speedtest_cache_delta
    speedtest_cache_delta = datetime.timedelta(seconds=CACHE_SECONDS)


def update_ping_delta(CACHE_SECONDS: int) -> None:
    """Updates the global ping cache timedelta object with new second duration

    Args:
        CACHE_SECONDS (int): How long should the cache duration be?
    """
    global PING_CACHE_DELTA
    PING_CACHE_DELTA = datetime.timedelta(seconds=CACHE_SECONDS)


def get_speedtest_cache_time() -> int:
    """Checks with Grafana to see how many devices are online.
    Then it returns the new cache time

    Returns:
        int: The new speedtest cache time in seconds. (-1 indicates error)
    """
    def _get_url() -> Optional[str]:
        """Returns the read URL of Prometheus endpoint

        Returns:
            Optional[str]: Read URL
        """
        url = os.environ.get("URL", None)
        if url is None:
            return None
        PATTERN = r"/api/prom/push$"
        REPLACEMENT = "/api/prom/api/v1/query"
        url = re.sub(PATTERN, REPLACEMENT, url)
        return url

    def _query_grafana_prometheus(URL, USERNAME, API_TOKEN, QUERY) -> Optional[int]:
        """Queries a Grafana Cloud Prometheus endpoint and returns amount of devices online.
        """
        params = {"query": QUERY}
        # Send the GET request with basic authentication
        RESPONSE = requests.get(
            URL, params=params, auth=HTTPBasicAuth(USERNAME, API_TOKEN))
        if RESPONSE.ok:
            RESULT_JSON = RESPONSE.json()
            if RESULT_JSON["status"] == "success":
                ORIGINS = [x["metric"]["origin_prometheus"]
                           for x in RESULT_JSON["data"]["result"]]
                logging.info(f"Found devices online: {ORIGINS}")
                # If 0 devices are reported online, assume 1
                return max(len(ORIGINS), 1)
            else:
                logging.error(
                    f"Valid HTTP JSON response collected, but API returned status: {RESULT_JSON['status']}")
                return None
        else:
            logging.error(
                f"An error occurred requesting endpoint data. Code: {RESPONSE.status_code}")
            return None

    URL = _get_url()
    USERNAME = os.environ.get("USERNAME", None)
    API_TOKEN = os.environ.get("API_TOKEN", None)

    for name, value in (
        ("URL", URL), ("USERNAME", USERNAME), ("API_TOKEN", API_TOKEN)
    ):
        if value is None:
            logging.error(f"Unable to find environment variable: {name}")
            return -1

    BOUNDARY_TOLERACE_SECONDS = 5*60
    LOOK_BACK_TIME_SECONDS = \
        speedtest_cache_delta.total_seconds() + BOUNDARY_TOLERACE_SECONDS

    if (LOOK_BACK_TIME_SECONDS < 60*60):
        logging.warning(
            f"Duration calculated for speedtest seems very low: {LOOK_BACK_TIME_SECONDS}")

    LOOK_BACK_TIME_DURATION = str(round(LOOK_BACK_TIME_SECONDS))
    QUERY = f"speedtest_up[{LOOK_BACK_TIME_DURATION}s]"

    DEVICES_ONLINE = _query_grafana_prometheus(URL, USERNAME, API_TOKEN, QUERY)
    if (DEVICES_ONLINE is None):
        logging.error(
            f"Failed to fetch devices online. Retaining previous wait time of {speedtest_cache_delta.total_seconds()} seconds")
        return -1

    return DEVICES_ONLINE*60*60


def _shutdown_server() -> Optional[int]:
    """Finds and runs the werkzeug shutdown procedure 
    """
    FUNC = requests.request.environ.get('werkzeug.server.shutdown')
    if FUNC is None:
        logging.error('Not running with the Werkzeug Server')
        return -1
    FUNC()


@app.get('/shutdown-werkzeug')
def _shutdown() -> str:
    """Flask endpoint for shutdown request

    Returns:
        str: Shutdown message
    """
    if _shutdown_server() == -1:
        return "Server failed to shut down"
    return 'Server shut down'


def graceful_exit(SIGNUM: signal.Signals, FRAME) -> None:
    """Runs shutdown procedure for SIGABRT and SIGINT signals. Exits program

    Args:
        SIGNUM (signal.Signals): Signal number
        FRAME (): 
    """
    logging.info(f"Caught signal: {SIGNUM}")
    logging.info("Shutting down...")

    shutdown_thread = threading.Thread(target=lambda: requests.get(
        f"http://localhost:{PORT}/shutdown-werkzeug", timeout=2))
    shutdown_thread.daemon = False
    shutdown_thread.start()
    shutdown_thread.join(timeout=2)

    logging.info("Cleanup complete. Exiting.")
    os._exit(0)


@app.route("/metrics")
def updateResults() -> None:
    global speedtest_cache_until
    global ping_cache_until

    if datetime.datetime.now() > ping_cache_until:
        logging.info("Starting ping...")
        metric_ping.refresh()
        metrics.ping_up.set(metric_ping.get_success())
        metrics.custom_ping.set(metric_ping.get_avg_ms())
        metrics.custom_packet_loss.set(metric_ping.get_packet_loss())

        logging.info(str(metric_ping))

        ping_cache_until = datetime.datetime.now() + PING_CACHE_DELTA
    else:
        logging.info("Request for ping too quick. Returning cached values")
        metrics.ping_up.set(Metric.Status.CACHED_UP)
        metrics.custom_ping.set(Metric.Status.INVALID)
        metrics.custom_packet_loss.set(Metric.Status.INVALID)

    send_cached_speedtest = False
    if datetime.datetime.now() > speedtest_cache_until:
        # Query server to see how many devices are online
        OLD_WAIT_DELTA = speedtest_cache_delta
        update_speedtest_delta(get_speedtest_cache_time())
        if (OLD_WAIT_DELTA != speedtest_cache_delta):
            logging.info(
                f"Wait time changed from {OLD_WAIT_DELTA} to {speedtest_cache_delta}")
        # Check condition again after updating value with new difference.
        # Initial boot will run because speedtest_cache_until starts at epoc 0
        speedtest_cache_until += speedtest_cache_delta - OLD_WAIT_DELTA
        if (datetime.datetime.now() > speedtest_cache_until):
            logging.info("Starting SpeedTest...")
            metric_speedtest.refresh()
            metrics.server.set(metric_speedtest.get_server())
            metrics.download_speed.set(metric_speedtest.get_download())
            metrics.upload_speed.set(metric_speedtest.get_upload())
            metrics.speedtest_up.set(metric_speedtest.get_success())
            logging.info(str(metric_speedtest))

            speedtest_cache_until = datetime.datetime.now() + speedtest_cache_delta
        else:
            send_cached_speedtest = True
    else:
        send_cached_speedtest = True

    if send_cached_speedtest:
        logging.info(
            "Request for speedtest too quick. Returning cached values")
        metrics.speedtest_up.set(Metric.Status.CACHED_UP)
        metrics.server.set(Metric.Status.INVALID)
        metrics.download_speed.set(Metric.Status.INVALID)
        metrics.upload_speed.set(Metric.Status.INVALID)

    return make_wsgi_app()


@app.route("/")
def mainPage():
    return ("<h1>Welcome to NetCheck API exporter.</h1>" +
            "Forked from <a href='https://github.com/MiguelNdeCarvalho/speedtest-exporter'>MiguelNdeCarvalho/speedtest-exporter</a>" +
            "<br>" +
            "Click <a href='/metrics'>here</a> to see metrics.")


def initialise_signal_handlers():
    signal.signal(signal.SIGTERM, graceful_exit)
    signal.signal(signal.SIGINT, graceful_exit)


def run_app() -> None:
    initialise_cache_variables()
    initialise_globals()
    initialise_signal_handlers()
    logging.info(f"Starting Netcheck-Exporter on http://localhost:{PORT}")
    waitress.serve(app, host='0.0.0.0', port=PORT)
