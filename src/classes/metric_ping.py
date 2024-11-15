from classes.metric import Metric
import os
import pythonping
import logging


class MetricPing(Metric):
    # Ping google as default
    DEFAULT_ADDRESS = '8.8.8.8'

    def __init__(self):
        super().__init__()
        self.PING_ADDRESS = os.environ.get(
            'PING_ADDRESS', MetricPing.DEFAULT_ADDRESS)
        self._success = False
        self._rtt_avg_ms = Metric.Status.UNINITIALISED
        self._packet_loss = Metric.Status.UNINITIALISED

    def __str__(self):
        if not self._metric_initialised:
            return "No value. Please refresh."
        return f"Status={self._success} Ping={self._rtt_avg_ms} Packet Loss% ={self._packet_loss}"

    def _invalidate_metric_values(self):
        self._success = False
        self._rtt_avg_ms = Metric.Status.INVALID
        self._packet_loss = Metric.Status.INVALID

    def _run_ping(self) -> bool:
        self._ping_errored = False
        try:
            PING_RESPONSE = pythonping.ping(self.PING_ADDRESS, verbose=False)
        except Exception as E:
            logging.error("No wifi or invalid permissions: " + E)
            self._invalidate_metric_values()

            self._ping_errored = True
            return False

        self._success = \
            PING_RESPONSE.success(pythonping.executor.SuccessOn.Most)
        self._rtt_avg_ms = PING_RESPONSE.rtt_avg_ms
        self._packet_loss = PING_RESPONSE.packet_loss
        return True

    def refresh(self):
        """Runs a ping test and updates metric values
        """
        self._run_ping()
        self._metric_initialised = True

    def _getter_base(self):
        if (not self._metric_initialised):
            logging.info("Collecting initial ping metrics. Called by getter")
            self.refresh()

    def get_success(self) -> bool:
        self._getter_base()
        return self._success

    def get_avg_ms(self) -> bool:
        self._getter_base()
        return self._rtt_avg_ms

    def get_packet_loss(self) -> bool:
        self._getter_base()
        return self._packet_loss
