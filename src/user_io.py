#!/usr/bin/env python
# -*- coding: utf-8 -*-


from common import (
    # logger,
    argv,
    exit,
    format_output,
    getenv,
    parse_datetime,
    path,
    read_logs,
    str_cleanup,
    table,
    timedelta,
)


def main():

    logsize = int(getenv("LOG_SIZE", 50))

    log_path = (path.join(p, "azbox_ui.log*") for p in (
        "/tmp/kiosklogpusher/backup",
        "/kiosk/local/*/logs",
    ))

    if len(argv[1:]) > 1:
        exit("Too many arguments: %s" % argv[1:])

    elif len(argv[1:]) == 1:
        filtering = argv[1:][0]

    else:
        filtering = None

    data = logs(log_path, logsize / 15 or 1, filtering)[-logsize:]
    headers = {
        k: format_output(k.capitalize(), bold=True)
        for k in data[-1].keys()
    }

    print(table(data, headers=headers) if data else "- Nothing found.")


def logs(log_path, days_ago, method=None):

    data = list()

    for line in read_logs(log_path, days_ago):
        if "Validat" in line and "directedID" not in line:
            message = line.split("[anonymous]")[-1].strip()
            message = str_cleanup(
                (w for w in message.split() if "Validat" in w),
                message
            )
            empty = '~'
            unwanted_char = '[]",'
            current = {
                "timestamp": parse_datetime(line.split("INFO")[0].strip()),
                "code": empty,
                "actor": empty,
                "method": empty,
                "result": empty,
            }

            if any(r in message for r in ("SUCCESS", "FAILURE")):
                message = message.split()

                current["code"] = str_cleanup(unwanted_char, message[-1])
                current["actor"] = message[2]
                current["result"] = message[0]

            elif "INPUT METHOD" in message:
                current["code"] = str_cleanup(
                    unwanted_char,
                    message.split(',')[0].split()[-1]
                )
                current["method"] = str_cleanup(
                    unwanted_char,
                    message.split("INPUT METHOD")[-1]
                ).strip()
                current["actor"] = message.split()[0]

            # result:
            if data[-1:] and (len(data[-1]) == len(current)):
                previous = data[-1]
                validation = [
                    (
                        current["timestamp"] - previous["timestamp"]
                        <= timedelta(seconds=3)
                    ),
                    current["actor"] == previous["actor"],
                    previous["result"] == empty,
                    current["method"] == empty,
                ]

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
        "scanner": "BARCODE",
        "screen": ("KEYPAD", "KEYBOARD"),
    }

    if method in filtering.keys():
        result = filter(lambda d: d["method"] in filtering[method], data)

    else:
        result = data

    return sorted(result, key=lambda d: d["timestamp"])


if __name__ == "__main__":
    main()
