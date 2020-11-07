#!/usr/bin/env python
# -*- coding: utf-8 -*-


from common import (
    cmd_exec,
    fetch,
    format_output,
    getenv,
    logger,
    mac_address,
    path,
    parse_datetime,
    read_logs,
    table
)


def main():

    log_size = int(getenv("LOG_SIZE", 30))

    route_ip = False
    for line in str(cmd_exec("ip route", interactive=False)).split("\n"):
        if "default" in line:
            route_ip = line.split()[2]
            break

    print(format_output("[INFO] Connection details:", "yellow"))
    data = {"modem": mac_address(route_ip or "192.168.15.1")}

    try:
        data.update(connection_info())

    except Exception as exception:
        logger.debug(exception)

    data = [(format_output(k, bold=True), data[k]) for k in data]
    print(table(sorted(data)))

    print

    data = list()
    log_path = (path.join(p, "traceroute.dat*") for p in (
        "/tmp/kiosklogpusher/backup",
        "/usr/local/kioskmonitoringtools/monlogs"
    ))

    print(format_output("[INFO] Connection logs:", "yellow"))

    for d, s in logs(log_path, log_size / 15 or 1)[-log_size:]:
        line = [
            d,
            "Online" if s else "Offline",
            parse_datetime(d, humanize=True)
        ]
        color = "green" if s else "red"
        data.append([format_output(i, color) for i in line])

    headers = (
        format_output(w, bold=True)
        for w in ("Timestamp", "Status", "When")
    )

    print(table(data, headers=headers) if data else "- Nothing found.")


def logs(log_path, days_ago):

    result = list()

    for line in read_logs(log_path, days_ago):
        if "#UTC_Time:" in line:
            line = line.split()
            result.append((
                parse_datetime(line[-2], "YYYY-MM-DD-HH-mm-ss"),
                len(line) > 3
            ))

    if result:
        result = sorted(result)
        filtered = [result[0]]
        for r in result:
            if r[1] != filtered[-1][1]:
                filtered.append(r)

        return filtered


def connection_info():

    api = "http://ip-api.com/json"

    attributes = [
        "country",
        "city",
        "ip",
        "query",
        "isp",
        "org",
    ]

    result = fetch(api)

    if int(result.status_code) == 200:
        result = {
            key: value
            for key, value in result.json().items()
            if key in attributes
        }

        if "query" in result:
            result["ip"] = result.pop("query")

        result["source"] = api

        return result


if __name__ == "__main__":
    main()
