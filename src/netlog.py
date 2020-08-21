#!/usr/bin/env python
# -*- coding: utf-8 -*-


from common import (
    date_range,
    fetch,
    format_output,
    getenv,
    mac_address,
    parse_datetime,
    randrange,
    table
)


def main():

    data = {"modem": mac_address("192.168.15.1")}

    try:
        data.update(connection_info())
    except Exception:
        pass

    data = [(format_output(k, bold=True), v) for k, v in data.items()]

    print(format_output("[INFO] Connection details:", "yellow"))
    print(table(sorted(data), tablefmt="plain"))

    print("\n")

    headers = ["Date/time", "Status", "When"]
    data = list()
    path = [
        "/tmp/kiosklogpusher/backup/traceroute.dat*",
        "/usr/local/kioskmonitoringtools/monlogs/traceroute.dat*"
    ]

    logsize = int(getenv("LOG_SIZE", 30))

    for d, s in read_logs(logsize / 15 or 1, path)[-logsize:]:
        line = [
            d,
            "Online" if s else "Offline",
            parse_datetime(d, humanize=True)
        ]
        color = "green" if s else "red"
        data.append([format_output(i, color) for i in line])

    headers = [format_output(text, bold=True) for text in headers]

    print(format_output("[INFO] Connection logs:", "yellow"))
    if len(data):
        print(table(data, headers=headers, tablefmt="plain"))

    else:
        print("- Nothing found.")


def read_logs(days_ago, logs_path):
    from glob import glob
    from gzip import open as gz_open

    if days_ago > 0:
        days_ago *= -1

    if not isinstance(logs_path, list):
        logs_path = [logs_path]

    processed, included, result = (list(), list(), list())

    for g in map(glob, logs_path):
        processed += g

    for d in map(str, date_range(days_ago)):
        included += [path for path in processed if d in path]

    for i in included:
        if i.split('.')[-1] == "gz":
            f_open = gz_open

        else:
            f_open = open

        for line in f_open(i).readlines():
            if "#UTC_Time:" in line:
                line = line.split()
                result.append((
                    parse_datetime(line[-2], "YYYY-MM-DD-HH-mm-ss"),
                    len(line) > 3
                ))

    if len(result):

        result = sorted(result)
        filtered = [result[0]]
        for r in result:
            if r[1] != filtered[-1][1]:
                filtered.append(r)

        return filtered


def connection_info():

    apis = [
        "http://ip-api.com/json",
        "http://ipinfo.io",
        "http://ipwhois.app/json/"
    ]

    attributes = [
        "country",
        "city",
        "ip",
        "isp",
        "org",
    ]

    queries = [fetch(url) for url in apis]
    queries = [q.json() for q in queries if int(q.status_code) == 200]

    result = list()

    for q in queries:
        if "query" in q:
            q["ip"] = q.pop("query")

        result.append({a: q[a] for a in attributes if a in q})

    if result:
        return result[randrange(len(result))]


if __name__ == "__main__":
    main()
