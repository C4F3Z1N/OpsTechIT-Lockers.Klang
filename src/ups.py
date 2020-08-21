#!/usr/bin/env python
# -*- coding: utf-8 -*-


from common import (
    cmd_exec,
    date_range,
    format_output,
    getenv,
    parse_datetime,
    table
)


def main():

    headers = ["Date/time", "BCHARGE", "When"]
    data = list()
    path = [
        "/tmp/kiosklogpusher/backup/kioskwatcher.log*",
        "/usr/local/kioskmonitoringtools/kioskwatcher.log*"
    ]

    logsize = int(getenv("LOG_SIZE", 30))

    for d, s, m in read_logs(logsize / 15 or 1, path)[-logsize:]:
        if s >= 50:
            color = "green"
        elif s >= 20:
            color = "yellow"
        else:
            color = "red"

        line = [d, "%s %d%%" % (m, s), parse_datetime(d, humanize=True)]
        data.append([format_output(i, color) for i in line])

    headers = [format_output(text, bold=True) for text in headers]

    print(format_output("[INFO] UPSBatteryPercentMetric:", "yellow"))
    if len(data):
        print(table(data, headers=headers, tablefmt="plain"))

    else:
        print("- Nothing found.")

    print("\n")

    important = ["STATUS", "BCHARGE", "ALARMMSG"]
    data = list()
    source = apcaccess()

    # if "ALARMMSG" in source:
    #     alarm = source.pop("ALARMMSG")

    for k, v in source.items():
        k = format_output(k, "yellow" if k in important else None, True)
        data.append((k, v))

    print(format_output("[INFO] apcaccess:", "yellow"))
    print(table(data, tablefmt="plain"))


def read_logs(days_ago, logs_path):
    from glob import glob
    from gzip import open as gz_open
    from json import loads

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
        if i.split('.')[-1].lower() == "gz":
            f_open = gz_open

        else:
            f_open = open

        for line in f_open(i).readlines():
            if "UPSBatteryPercentMetric" in line:
                line = loads(line.split("metric:")[-1])
                result.append([
                    parse_datetime(int(line["timestamp"])),
                    int(line["percent"]),
                    '~'
                ])

    if result:
        result = sorted(result)
        filtered = [result[0]]
        for r in result:
            if r[1] != filtered[-1][1]:
                r[2] = u"\u2191" if r[1] > filtered[-1][1] else u"\u2193"
                filtered.append(r)

        return filtered


def apcaccess():

    query = cmd_exec("apcaccess", interactive=False)

    if query:
        result = dict()

        for line in query.split("\n"):
            if line:
                key = line.split(':')[0]
                result[key.strip()] = line.split("%s:" % key)[-1].strip()

        alarm_msg = {
            "OVERLOAD": "\
                - Electrical system issue detected. Ask vendor \
                to measure mains with the Martindale tester.",
            "SHUTTING":
                "- Error state detected. \"apcupsd\" will initiate a \
                system shutdown shortly. If the battery levels are \
                not low, restarting the \"apcupsd\" daemon should \
                solve the issue. If state remains the same after \
                daemon restart, UPS might be faulty.",
            "ONBATT":
                "- Kiosk is running on UPS batteries. There is no power \
                coming into the UPS from Mains.",
            "LOWBATT":
                "- Check if BCHARGE is low. If it is 100%, ask vendor to \
                replace faulty UPS because the batteries are damaged.",
            "REPLACEBATT":
                "- UPS batteries are exhausted. \
                Ask vendor to replace the UPS.",
            "NOBATT":
                "- UPS batteries are dead/not detected. \
                UPS should be replaced.",
            "COMMLOST":
                "- UPS is not properly detected or badly configured. \
                Re-seat UPS batteries and cable connections. Disconnect UPS \
                from Mains and check if maintains Locker on batteries."
        }

        message = str()

        if float(result.get("TIMELEFT").split()[0]) >= 300:
            message += "\
                - Please ask the field engineer to connect the power strip \
                to the UPS port labeled \"MASTER\". It is currently \
                connected to the \"Controlled by MASTER\" port."

        for alarm in (
            set(result.get("STATUS").split()).intersection(alarm_msg.keys())
        ):
            message += "\n" + result[alarm]

        if message:
            result["ALARMMSG"] = message.strip()

        return result


if __name__ == "__main__":
    main()
