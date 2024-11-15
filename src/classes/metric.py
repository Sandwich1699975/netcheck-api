import abc


class Metric():
    class Status():
        INVALID = -1
        UNINITIALISED = None
        DOWN = 0
        UP = 1
        CACHED_DOWN = 10
        CACHED_UP = 11

    def __init__(self):
        super().__init__()
        self._metric_initialised = False

    @abc.abstractmethod
    def __str__(self):
        pass

    @abc.abstractmethod
    def refresh(self) -> None:
        """Updates metric values
        """

    @abc.abstractmethod
    def _invalidate_metric_values(self) -> None:
        """Set all metric values to invalid
        """
