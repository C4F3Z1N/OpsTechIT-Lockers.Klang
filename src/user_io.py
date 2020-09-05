#!/usr/bin/env python
# -*- coding: utf-8 -*-


from common import (
    # logger,
    # format_output,
    getenv,
    parse_datetime,
    path,
    read_logs,
    str_cleanup,
    table
)
# from pprint import pprint


def main():

    logsize = int(getenv("LOG_SIZE", 50))

    log_path = (path.join(p, "azbox_ui.log*") for p in (
        "/tmp/kiosklogpusher/backup",
        "/kiosk/local/*/logs"
    ))

    # headers = (format_output(text, bold=True) for text in (
    #     "Date/time", "Message"
    # ))
    data = logs(log_path, logsize / 15 or 1)[-logsize:]

    # print(table(data, headers=headers))
    print(table(data))


def logs(log_path, days_ago):

    data = list()

    for line in read_logs(log_path, days_ago):
        if "Validat" in line:
            timestamp = line.split("INFO")[0].strip()
            message = line.split("[anonymous]")[-1].strip()
            data.append((
                parse_datetime(timestamp),
                message
            ))

    validation = list()
    method = list()
    # tmp = list()
    unwanted_char = '[]",'

    for line in data:
        if ("SUCCESS" in line[-1]) or ("FAILURE" in line[-1]):
            splitted = line[-1].split()
            validation.append([
                line[0],
                # bool(splitted[1] == "SUCCESS"),    # "SUCCESS" or "FAILURE";
                str_cleanup(unwanted_char, splitted[-1]),    # Code;
                splitted[1],    # "SUCCESS" or "FAILURE";
            ])
        elif "INPUT METHOD" in line[-1]:
            splitted = line[-1].split()
            method.append([
                line[0],
                str_cleanup(unwanted_char, splitted[3]),    # Code;
                splitted[1],    # Customer or Carrier;
                str_cleanup(unwanted_char, splitted[-1]),   # Method;
            ])

    # pprint(validation)
    # pprint(method)

    return sorted(method + validation) if method else None

    # return sorted(validation) if validation else None

    # return sorted(data) if data else None


if __name__ == "__main__":
    main()
    # 40027812
