# Netcheck API
![Tests](https://github.com/Sandwich1699975/netcheck-api/actions/workflows/tests.yml/badge.svg)

Written for [NetCheck](https://github.com/Sandwich1699975/NetCheck)

Simple **Speedtest exporter** for **Prometheus** written in **Python** using the
official CLI from **Ookla**

Based on [MiguelNdeCarvalho/speedtest-exporter](https://github.com/MiguelNdeCarvalho/speedtest-exporter)

> [!IMPORTANT]
> **This repository is not meant to be standalone**. See [NetCheck](https://github.com/Sandwich1699975/NetCheck) for supporting code.


## Setup

> [!IMPORTANT]
> This script requires elevated privlages to run. Creating ping calls cannot be done without it.

However, the exporter can be manually started if needed:
- Install dependencies in `src/requirements.txt`
- Export environment variables for your Grafana Cloud `URL`, `USERNAME` and `API_TOKEN`
- Run `sudo python3 src/main.py`. 

## Testing


You can run tests locally using 

```terminal
$ bash run_tests.sh 
```

You can also pass the `--use-container` flag to run the tests with Docker and Act.