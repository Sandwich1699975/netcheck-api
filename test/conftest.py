import pytest
from multiprocessing import Process
from main import initialise_logging
from web import run_app
from threading import Thread
import time


@pytest.fixture(scope="session", autouse=True)
def start_web_app():
    initialise_logging()

    thread = Thread(target=run_app, daemon=True)
    thread.start()

    # Wait briefly to ensure the app is running
    time.sleep(2)

    yield  # Test execution happens here
