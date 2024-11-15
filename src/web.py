import signal
import requests
import threading
import logging
import os
import flask
import metrics
import datetime
import waitress
from typing import Optional
from classes.metric import Metric
from prometheus_client import make_wsgi_app
from classes.metric_ping import MetricPing
from classes.metric_speedtest import MetricSpeedtest
from classes.metric import Metric


app = flask.Flask("Netcheck-Exporter")
PORT = os.getenv('SPEEDTEST_PORT', 9798)


def initialise_globals() -> None:
    global speedtest_cache_until, ping_cache_until
    speedtest_cache_until = datetime.datetime.fromtimestamp(0)
    ping_cache_until = datetime.datetime.fromtimestamp(0)
    global metric_ping, metric_speedtest
    metric_ping = MetricPing()
    metric_speedtest = MetricSpeedtest(os.environ.get("DEBUG_MODE") == "true")


def initialise_constants() -> None:
    """Generate constants that are not dependant on anything else
    """
    # Cache metrics for how long (seconds)?
    # Speedtests are rate limited. Do not run more than one per hour per IP address
    SPEEDTEST_CACHE_SECONDS = int(os.environ.get('SPEEDTEST_CACHE_FOR', 3600))
    global SPEEDTEST_CACHE_DELTA
    SPEEDTEST_CACHE_DELTA = datetime.timedelta(seconds=SPEEDTEST_CACHE_SECONDS)

    PING_CACHE_SECONDS = int(os.environ.get('PING_CACHE_FOR', 15))
    global PING_CACHE_DELTA
    PING_CACHE_DELTA = datetime.timedelta(seconds=PING_CACHE_SECONDS)


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

    if datetime.datetime.now() > speedtest_cache_until:
        logging.info("Starting SpeedTest...")
        metric_speedtest.refresh()
        metrics.server.set(metric_speedtest.get_server())
        metrics.download_speed.set(metric_speedtest.get_download())
        metrics.upload_speed.set(metric_speedtest.get_upload())
        metrics.speedtest_up.set(metric_speedtest.get_success())
        logging.info(str(metric_speedtest))

        speedtest_cache_until = datetime.datetime.now() + SPEEDTEST_CACHE_DELTA
    else:
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
    initialise_constants()
    initialise_globals()
    initialise_signal_handlers()
    logging.info(f"Starting Netcheck-Exporter on http://localhost:{PORT}")
    waitress.serve(app, host='0.0.0.0', port=PORT)
