# Netcheck API

> [!IMPORTANT]
> Work In Progress

Based on [MiguelNdeCarvalho/speedtest-exporter](https://github.com/MiguelNdeCarvalho/speedtest-exporter)

Written for [NetCheck](https://github.com/Sandwich1699975/NetCheck)

Simple **Speedtest exporter** for **Prometheus** written in **Python** using the
official CLI from **Ookla**

You can find the old documentation [here](https://docs.miguelndecarvalho.pt/projects/speedtest-exporter/)

## Setup

> [!IMPORTANT]
> This script requires elevated privlages to run. Creating ping calls cannot be done without it.

Simply install dependencies in `src/requirements.txt` and run `sudo python3 src/main.py`. 

This repository is not meant to be standalone. See [NetCheck](https://github.com/Sandwich1699975/NetCheck) for supporting code.
