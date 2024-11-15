import prometheus_client as prom

# Create Metrics
server = prom.Gauge(
    'speedtest_server_id',
    'Speedtest server ID used to test',
)
download_speed = prom.Gauge(
    'speedtest_download_bits_per_second',
    'Speedtest current Download Speed in bit/s',
)
upload_speed = prom.Gauge(
    'speedtest_upload_bits_per_second',
    'Speedtest current Upload speed in bits/s',
)
speedtest_up = prom.Gauge(
    'speedtest_up',
    'Speedtest status whether the scrape worked',
)

ping_up = prom.Gauge(
    'ping_up',
    'Status whether the custom ping worked',
)
custom_ping = prom.Gauge(
    'custom_ping_latency_milliseconds',
    'Current ping in ms from custom server',
)
custom_packet_loss = prom.Gauge(
    'custom_packet_loss',
    'Custom server packet loss',
)
