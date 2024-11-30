# Netcheck API

Based on [MiguelNdeCarvalho/speedtest-exporter](https://github.com/MiguelNdeCarvalho/speedtest-exporter)

Written for [NetCheck](https://github.com/Sandwich1699975/NetCheck)

Simple **Speedtest exporter** for **Prometheus** written in **Python** using the
official CLI from **Ookla**

You can find the forked repo's documentation [here](https://docs.miguelndecarvalho.pt/projects/speedtest-exporter/)

## Setup

> [!IMPORTANT]
> This script requires elevated privlages to run. Creating ping calls cannot be done without it.
>
> **This repository is not meant to be standalone**. See [NetCheck](https://github.com/Sandwich1699975/NetCheck) for supporting code.

However, the exporter can be manually started if needed:
- Install dependencies in `src/requirements.txt`
- Export environment variables for your Grafana Cloud `URL`, `USERNAME` and `API_TOKEN`
- Run `sudo python3 src/main.py`. 

