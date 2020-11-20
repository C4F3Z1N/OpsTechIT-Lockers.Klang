#!/usr/bin/env python
# -*- coding: utf-8 -*-


from common import (
    logger,
    argv,
    cmd_exec,
    exit,
    format_output,
    getenv,
    parse_datetime,
    path,
    read_logs,
    reservations,
    str_cleanup,
    table,
    timedelta,
)
from boards import generation
from collections import OrderedDict as dict
from hashlib import sha256


EMPTY = "???"   # printable char;


def main():
    logsize = int(getenv("LOG_SIZE", 50))

    if not len(argv[1:]):
        exit("Too many arguments: %s" % argv[1:])

    elif len(argv[1:]) == 1:
        filtering = argv[1:][0]

    else:
        filtering = None

    if filtering:
        print(format_output(
            "[INFO] %s detection methods:" % filtering.capitalize(),
            "yellow"
        ))

        data = list()
        for key, value in detect(filtering).items():
            color = "green" if value else "red"
            data.append([
                key,
                format_output(bool(value), color)
            ])

        print(table(data, headers=(
            format_output(key.capitalize(), bold=True)
            for key in ("command", "reachable")
        )) if data else "- Nothing found.")

        print

    if logsize > 15:

        log_path = (path.join(p, "azbox_ui.log*") for p in (
            "/tmp/kiosklogpusher/backup",
            "/kiosk/local/*/logs",
        ))

        print(format_output("[INFO] Latest interaction logs:", "yellow"))

        data = logs(log_path, logsize / 15, filtering)[-logsize:]
        for line in data:
            colors = {
                "SUCCESS": "green",
                "FAILURE": "red",
            }

            line["when"] = parse_datetime(line["timestamp"], humanize=True)

            if line["result"] in colors:
                line["result"] = format_output(
                    line["result"],
                    colors[line["result"]],
                    bold=True
                )

        print(table(data, headers={
            k: format_output(k.capitalize(), bold=True)
            for k in data[-1].keys()
        }) if data else "- Nothing found.")


def logs(log_path, days_ago, method=None):

    data = list()
    for line in sorted(read_logs(log_path, days_ago)):
        if "Validat" in line and "directedID" not in line:
            current = dict((
                ("timestamp", parse_datetime(line.split("INFO")[0].strip())),
                ("actor", EMPTY),
                ("method", EMPTY),
                ("code", EMPTY),
                ("result", EMPTY),
                ("reservation", EMPTY),
            ))
            message = line.split("[anonymous]")[-1].split()
            unwanted_char = '[]",'

            if any(r in message for r in ("SUCCESS", "FAILURE")):
                current["code"] = str_cleanup(unwanted_char, message[-1])
                current["actor"] = message[3]
                current["result"] = message[1]

            elif "METHOD" in message:
                current["code"] = str_cleanup(unwanted_char, message[3])
                current["actor"] = message[1]
                current["method"] = str_cleanup(unwanted_char, message[-1])

            else:
                logger.debug([current["timestamp"], message])

            current["reservation"] = find_reservation(current["code"]) or EMPTY

            # result:
            if data[-1:] and (len(data[-1]) == len(current)):
                previous = data[-1]
                validation = (
                    (
                        current["timestamp"] - previous["timestamp"]
                        <= timedelta(seconds=3)
                    ),
                    current["reservation"] == previous["reservation"],
                    current["actor"] == previous["actor"],
                    previous["result"] == EMPTY,
                    current["method"] == EMPTY,
                )

                if all(validation):
                    current["method"] = previous["method"]
                    current["code"] = ", ".join(sorted(set([
                        current["code"],
                        previous["code"],
                    ])))
                    data[-1] = current
                    continue

            data.append(current)

    filtering = {
        "scanner": ("BARCODE", EMPTY),
        "screen": ("KEYBOARD", "KEYPAD", EMPTY),
    }

    return filter(
        lambda l: l["method"] in filtering[method],
        data
    ) if method else data


def find_reservation(code):
    filtered = str().join(filter(str.isdigit, code))

    for r in reservations():
        if any(i in code for i in ('_', "CR")):
            if "externalReferenceIds" in r:
                for attr in r["externalReferenceIds"]:
                    if attr["value"] in code:
                        return r["reservationId"]

        elif len(filtered) == 6:
            hashed = sha256(r["credentials"]["pinSalt"] + filtered)
            if hashed.hexdigest() == r["credentials"]["pinSaltedHash"]:
                return r["reservationId"]

        elif "shipmentIds" in r:
            if code in r["shipmentIds"]:
                return r["reservationId"]


def detect(method):
    data = {
        "dmesg": str(cmd_exec("dmesg -T", interactive=False)).split("\n"),
        "lsusb": str(cmd_exec("lsusb", interactive=False)).split("\n"),
    }
    result = dict()

    if method == "scanner":
        result["dmesg"] = filter(
            lambda l: "honey" in l.lower(),
            data["dmesg"]
        )

        if generation() > 2:
            result["ls"] = path.islink("/dev/tty.barcodeScanner")

    elif method == "screen":
        keywords = ("egal", "elo")
        for key in data.keys():
            result[key] = filter(
                lambda l: any(k in l.lower() for k in keywords),
                data[key]
            )

    else:
        logger.debug(method)
        raise ValueError

    return result


if __name__ == "__main__":
    main()
