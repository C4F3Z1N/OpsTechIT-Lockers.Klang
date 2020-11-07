#!/usr/bin/env python
# -*- coding: utf-8 -*-


from common import (
    cmd_exec,
    format_output,
    getenv,
    logger,
    parse_datetime,
    path,
    read_logs,
    table
)
from time import sleep


f_datetime = "YYYY-MM-DD HH:mm:ss Z"


def main():

    logsize = int(getenv("LOG_SIZE", 30))

    print(format_output("[INFO] apcupsd service:", "yellow"))
    assert cmd_exec("sudo service apcupsd restart")

    print("\n")

    print(format_output("[INFO] apcupsd events:", "yellow"))

    headers = (
        format_output(text, bold=True)
        for text in ("Timestamp", "Message")
    )
    data = events()[-logsize:]

    print(table(data, headers=headers) if data else "- Nothing found.")

    print("\n")

    headers = (
        format_output(text, bold=True)
        for text in ("Timestamp", "BCHARGE", "When")
    )
    data = list()
    log_path = (path.join(p, "kioskwatcher.log*") for p in (
        "/tmp/kiosklogpusher/backup",
        "/usr/local/kioskmonitoringtools"
    ))

    print(format_output("[INFO] UPSBatteryPercentMetric:", "yellow"))

    for d, s, m in logs(log_path, logsize / 15 or 1)[-logsize:]:
        if s >= 50:
            color = "green"
        elif s >= 20:
            color = "yellow"
        else:
            color = "red"

        line = [d, "%s %d%%" % (m, s), parse_datetime(d, humanize=True)]
        data.append([format_output(i, color) for i in line])

    print(table(data, headers=headers) if data else "- Nothing found.")

    print

    print(format_output("[INFO] apcaccess:", "yellow"))

    source = apcaccess()
    count = 3
    while not source and count:
        sleep(count)
        source = apcaccess()
        count -= 1

    if not source:
        return source

    important = ("STATUS", "BCHARGE")
    data = list()

    if "ALARMMSG" in source:
        alarm = source.pop("ALARMMSG")
    else:
        alarm = None

    for k, v in source.items():
        k = format_output(k, "yellow" if k in important else None, True)
        data.append((k, v))

    print(table(data, headers=headers) if data else "- Nothing found.")

    if alarm:
        print("\n")
        print(format_output("[WARN] UPS alarm:", "red", True))
        print(format_output(alarm, bold=True))


def logs(log_path, days_ago):
    from json import loads

    result = list()

    for line in read_logs(log_path, days_ago):
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

        result = filtered

    return result


def apcaccess():

    query = cmd_exec("apcaccess", interactive=False)

    if query:
        result = dict()

        for line in query.split("\n"):
            if line:
                key = line.split(':')[0]
                result[key.strip()] = line.split("%s:" % key)[-1].strip()

        dt_fields = ("STARTTIME", "DATE", "END APC")
        result.update({
            k: parse_datetime(result[k], f_datetime)
            for k in result if k in dt_fields
        })

        alarm_msg = {
            a: " ".join(m.split())
            for a, m in {
                "OVERLOAD":
                    "- Electrical system issue detected. Ask vendor \
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
                    Re-seat UPS batteries and cable connections. Disconnect \
                    UPS from Mains and check if maintains Locker on batteries."
            }.items()
        }

        message = str()
        timeleft = float(result.get("TIMELEFT").split()[0])

        if timeleft <= 10:
            message += " ".join("\
                - UPS batteries are incapable of sustaining the Locker ON \
                during a power outage. KODR will interpret the outage as \
                Network. It's advisable to replace the UPS. If there are \
                recurrent FSTs, investigate \"apcupsd.events\" for repeated \
                power failures.".split())

        elif timeleft >= 300:
            message += " ".join("\
                - Please ask the field engineer to connect the power strip \
                to the UPS port labeled \"MASTER\". It is currently \
                connected to the \"Controlled by MASTER\" port.".split())

        for alarm in (
            set(result.get("STATUS").split()).intersection(alarm_msg.keys())
        ):
            message += "\n" + alarm_msg[alarm]

        if message:
            result["ALARMMSG"] = message.strip()

        return result


def events():

    result = list()

    keywords = (
        "battery",
        "failure",
        "reached",
        "running",
        "shutdown",
        "startup"
    )

    for line in read_logs(["/var/log/apcupsd.events*"]):
        if any(k in line.lower() for k in keywords):
            splitted = line.strip("\x00").split()
            try:
                result.append((
                    parse_datetime(" ".join(splitted[:3]), f_datetime),
                    " ".join(splitted[3:])
                ))
            except Exception as exception:
                logger.debug(exception)

    return sorted(result) if result else result


if __name__ == "__main__":
    main()
