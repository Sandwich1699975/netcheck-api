import json
from numbers import Number
import os
from classes.metric import Metric
import subprocess
import json
import os
import logging
from numbers import Number


class MetricSpeedtest(Metric):

    def __init__(self, TEST_MODE=False):
        super().__init__()
        self._CUSTOM_SERVER_ID = os.environ.get('SPEEDTEST_SERVER')
        self._SPEEDTEST_TIMEOUT = int(os.environ.get('SPEEDTEST_TIMEOUT', 90))
        self._CMD_ARGS = [
            "speedtest", "--format=json-pretty", "--progress=no",
            "--accept-license", "--accept-gdpr"
        ]
        if self._CUSTOM_SERVER_ID:
            self._CMD_ARGS.append(f"--server-id={self._CUSTOM_SERVER_ID}")
        self._TEST_MODE = TEST_MODE

        self._actual_server = Metric.Status.UNINITIALISED
        self._success = False
        self._download_bits_per_second = Metric.Status.UNINITIALISED
        self._upload_bits_per_second = Metric.Status.UNINITIALISED

    def __str__(self):
        if not self._metric_initialised:
            return "No value. Please refresh."
        UPLOAD_MBPS = self.bits_to_megabits(self._upload_bits_per_second)
        DOWNLOAD_MBPS = self.bits_to_megabits(self._download_bits_per_second)
        return f"Status={self._success} Server={self._actual_server} Upload={UPLOAD_MBPS}Mbps Download={DOWNLOAD_MBPS}Mbps"

    @staticmethod
    def bytes_to_bits(bytes_per_sec: Number) -> Number:
        return bytes_per_sec * 8

    @staticmethod
    def bits_to_megabits(bits_per_sec: Number) -> Number:
        return round(bits_per_sec * (10**-6), 2)

    @staticmethod
    def is_json(myjson: str) -> bool:
        try:
            json.loads(myjson)
        except ValueError:
            return False
        return True

    def _invalidate_metric_values(self):
        self._actual_server = Metric.Status.INVALID
        self._success = False
        self._download_bits_per_second = Metric.Status.INVALID
        self._upload_bits_per_second = Metric.Status.INVALID

    def refresh(self):
        """Runs a speed test and updates metric values
        """
        if (not self._TEST_MODE):
            self._run_speed_test()
        else:
            # Dummy values to avoid ratelimiting
            logging.info(
                "TEST_MODE environment variable set. Using test values")
            self._download_bits_per_second = 1.23e+8
            self._upload_bits_per_second = 1.23e+8
            self._success = True
            self._actual_server = 123
        self._metric_initialised = True

    def _run_speed_test(self) -> bool:
        try:
            output = subprocess.check_output(
                self._CMD_ARGS, timeout=self._SPEEDTEST_TIMEOUT)
        except subprocess.CalledProcessError as e:
            output = e.output
            if not self.is_json(output):
                if len(output) > 0:
                    logging.error('Speedtest CLI Error occurred that' +
                                  'was not in JSON format')
                self._invalidate_metric_values()
                return False
        except subprocess.TimeoutExpired:
            logging.error('Speedtest CLI process took too long to complete ' +
                          'and was killed.')
            self._invalidate_metric_values()
            return False

        if self.is_json(output):
            DATA = json.loads(output)
            if "error" in DATA:
                # Socket error
                logging.error('Something went wrong')
                logging.error(DATA['error'])
                self._invalidate_metric_values()
                return False
            if "type" in DATA:
                if DATA['type'] == 'log':
                    print(f"{DATA['timestamp']} - {DATA['message']}")
                if DATA['type'] == 'result':
                    self._actual_server = int(DATA['server']['id'])
                    self._download_bits_per_second = \
                        self.bytes_to_bits(DATA['download']['bandwidth'])
                    self._upload_bits_per_second = \
                        self.bytes_to_bits(DATA['upload']['bandwidth'])
                    self._success = True
                    return True
        return False

    def _getter_base(self):
        if (not self._metric_initialised):
            logging.info(
                "Collecting initial speedtest metrics. Called by getter")
            self.refresh()

    def get_success(self) -> bool:
        self._getter_base()
        return self._success

    def get_server(self) -> bool:
        self._getter_base()
        return self._actual_server

    def get_download(self) -> bool:
        self._getter_base()
        return self._download_bits_per_second

    def get_upload(self) -> bool:
        self._getter_base()
        return self._upload_bits_per_second
