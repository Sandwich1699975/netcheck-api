import subprocess
import json
import os
import logging
import datetime
from prometheus_client import make_wsgi_app, Gauge
from flask import Flask
from waitress import serve
from shutil import which
from pythonping import ping, executor
import ctypes


app = Flask("Netcheck-Exporter")  # Create flask app

# Setup logging values
format_string = 'level=%(levelname)s datetime=%(asctime)s %(message)s'
logging.basicConfig(encoding='utf-8',
                    level=logging.DEBUG,
                    format=format_string)

# Disable Waitress Logs
log = logging.getLogger('waitress')
log.disabled = True

# Create Metrics
server = Gauge('speedtest_server_id', 'Speedtest server ID used to test')
download_speed = Gauge('speedtest_download_bits_per_second',
                       'Speedtest current Download Speed in bit/s')
upload_speed = Gauge('speedtest_upload_bits_per_second',
                     'Speedtest current Upload speed in bits/s')
speedtest_up = Gauge(
    'speedtest_up', 'Speedtest status whether the scrape worked')
ping_up = Gauge(
    'ping_up', 'Status whether the custom ping worked')
custom_ping = Gauge('custom_ping_latency_milliseconds',
                    'Current ping in ms from custom server')
custom_packet_loss = Gauge('custom_packet_loss',
                           'Custom server packet loss')


# Cache metrics for how long (seconds)?
# Speedtests are rate limited. Do not run more than one per hour per IP address
speedtest_cache_seconds = int(os.environ.get('SPEEDTEST_CACHE_FOR', 3600))
ping_cache_seconds = int(os.environ.get('PING_CACHE_FOR', 5))
speedtest_cache_until = datetime.datetime.fromtimestamp(0)
ping_cache_until = datetime.datetime.fromtimestamp(0)


def bytes_to_bits(bytes_per_sec):
    return bytes_per_sec * 8


def bits_to_megabits(bits_per_sec):
    megabits = round(bits_per_sec * (10**-6), 2)
    return str(megabits) + "Mbps"


def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError:
        return False
    return True


def runPing():
    # Ping google as default
    DEFAULT_ADDRESS = '8.8.8.8'
    PING_ADDRESS = os.environ.get('PING_ADDRESS', DEFAULT_ADDRESS)

    try:
        PING_RESPONSE = ping(PING_ADDRESS, verbose=False)
    except Exception as E:
        logging.error("No wifi or invalid permissions: " + E)
        return (0, -1, -1)

    return (
        PING_RESPONSE.success(executor.SuccessOn.Most),
        PING_RESPONSE.rtt_avg_ms,
        PING_RESPONSE.packet_loss
    )


def runSpeedTest():
    serverID = os.environ.get('SPEEDTEST_SERVER')
    timeout = int(os.environ.get('SPEEDTEST_TIMEOUT', 90))

    cmd = [
        "speedtest", "--format=json-pretty", "--progress=no",
        "--accept-license", "--accept-gdpr"
    ]
    if serverID:
        cmd.append(f"--server-id={serverID}")
    try:
        output = subprocess.check_output(cmd, timeout=timeout)
    except subprocess.CalledProcessError as e:
        output = e.output
        if not is_json(output):
            if len(output) > 0:
                logging.error('Speedtest CLI Error occurred that' +
                              'was not in JSON format')
            return (0, 0, 0, 0)
    except subprocess.TimeoutExpired:
        logging.error('Speedtest CLI process took too long to complete ' +
                      'and was killed.')
        return (0, 0, 0, 0)

    if is_json(output):
        data = json.loads(output)
        if "error" in data:
            # Socket error
            print('Something went wrong')
            print(data['error'])
            return (0, 0, 0, 0)  # Return all data as 0
        if "type" in data:
            if data['type'] == 'log':
                print(str(data["timestamp"]) + " - " + str(data["message"]))
            if data['type'] == 'result':
                actual_server = int(data['server']['id'])
                download = bytes_to_bits(data['download']['bandwidth'])
                upload = bytes_to_bits(data['upload']['bandwidth'])
                return (actual_server, download, upload, 1)


@app.route("/metrics")
def updateResults():
    global speedtest_cache_until
    global ping_cache_until

    if datetime.datetime.now() > ping_cache_until:
        logging.info("Starting ping...")
        r_status, r_ping, r_packet_loss = runPing()
        print(r_status, r_ping, r_packet_loss)
        ping_up.set(r_status)
        custom_ping.set(r_ping)
        custom_packet_loss.set(r_packet_loss)

        logging.info("Status=" + str(r_status) + " Ping=" +
                     str(r_ping) + " Packet Loss% =" + str(r_packet_loss))

        ping_cache_until = datetime.datetime.now() + datetime.timedelta(
            seconds=ping_cache_seconds)
    else:
        logging.info("Request for ping too quick. Returning NaN")
        ping_up.set(float('nan'))
        custom_ping.set(float('nan'))
        custom_packet_loss.set(float('nan'))

    if datetime.datetime.now() > speedtest_cache_until:
        logging.info("Starting SpeedTest...")
        r_server, r_download, r_upload, r_status = (
            123, 123, 123, 1)  # runSpeedTest()
        server.set(r_server)
        download_speed.set(r_download)
        upload_speed.set(r_upload)
        speedtest_up.set(r_status)
        logging.info("Server=" + str(r_server) + " Download=" +
                     bits_to_megabits(r_download) + " Upload=" +
                     bits_to_megabits(r_upload))

        speedtest_cache_until = datetime.datetime.now() + datetime.timedelta(
            seconds=speedtest_cache_seconds)
    else:
        logging.info("Request for speedtest too quick. Returning NaN")
        server.set(float('nan'))
        download_speed.set(float('nan'))
        upload_speed.set(float('nan'))
        speedtest_up.set(float('nan'))

    return make_wsgi_app()


@app.route("/")
def mainPage():
    return ("<h1>Welcome to NetCheck API exporter.</h1>" +
            "Forked from <a href='https://github.com/MiguelNdeCarvalho/speedtest-exporter'>MiguelNdeCarvalho/speedtest-exporter</a>" +
            "<br>" +
            "Click <a href='/metrics'>here</a> to see metrics.")


def checkForBinary():
    if which("speedtest") is None:
        logging.error("Speedtest CLI binary not found. Please install it by" +
                      " going to the official website.\n" +
                      "https://www.speedtest.net/apps/cli")
        exit(1)
    speedtestVersionDialog = (subprocess.run(['speedtest', '--version'],
                              capture_output=True, text=True))
    if "Speedtest by Ookla" not in speedtestVersionDialog.stdout:
        logging.error("Speedtest CLI that is installed is not the official" +
                      " one. Please install it by going to the official" +
                      " website.\nhttps://www.speedtest.net/apps/cli")
        exit(1)


def checkAdmin():
    """Aborts the program if it is not run with elevated privalges
    """
    isAdmin = False
    try:
        isAdmin = os.getuid() == 0
    except AttributeError:
        isAdmin = ctypes.windll.shell32.IsUserAnAdmin() != 0

    if not isAdmin:
        logging.error("You must run this exporter as admin.")
        exit(1)


if __name__ == '__main__':
    checkAdmin()
    checkForBinary()
    PORT = os.getenv('SPEEDTEST_PORT', 9798)
    logging.info("Starting Netcheck-Exporter on http://localhost:" +
                 str(PORT))
    serve(app, host='0.0.0.0', port=PORT)
