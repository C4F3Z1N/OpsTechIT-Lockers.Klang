#!/usr/bin/env python
# -*- coding: utf-8 -*-

from common import (
    cmd_exec,
    format_output,
    lockers,
    parse_datetime,
    table,
)
from collections import OrderedDict as dict


def main():
    from argparse import ArgumentParser

    args = ArgumentParser(description="Interact with slot(s).")

    args.add_argument(
        "operation",
        help="Either \"open\" (-o) or \"sensor\" (-s).",
        metavar="operation")

    args.add_argument(
        "slots",
        help="Either \"1 2 3... n\" or \"all\"",
        metavar="slots",
        nargs="*")

    args = args.parse_args()

    controller(args.operation, args.slots)


def parsed_lockers():
    return {
        int(locker["lockerConfig"]["lockerId"]): locker
        for locker in lockers()
    }


def controller(operation, slots):

    kiosk = parsed_lockers()

    # operation definition;

    if not operation or "sens" in str(operation).lower():
        operation = "-w -s"

    elif "open" in str(operation).lower():
        operation = "-o"

    else:
        raise NotImplementedError

    # affected slots verification;

    if len(slots) == 1 and str(slots[0]).lower() == "all":
        slots = kiosk.keys()

    else:
        slots = map(int, slots)

    # slot existence verification;

    if all(slot in kiosk.keys() for slot in slots):
        pass

    elif any(slot in kiosk.keys() for slot in slots):
        not_found = set(slots) - set(kiosk.keys())
        slots = set(slots) - not_found

        warn = format_output("[WARN] Slot(s) #%s not found.", "magenta")
        print(warn % ", #".join(map(str, not_found)))

    else:
        raise NotImplementedError

    # output/operation;

    data = list()
    for line in slot_status(slots):
        line_color = "green" if line.pop("active") else "red"
        line["status"] = format_output(line["status"], line_color, bold=True)
        for i in ("updated", "checked"):
            line[i] = parse_datetime(line[i], humanize=True)

        data.append(dict((
            (format_output(key.capitalize(), bold=True), value)
            for key, value in line.items()
        )))

    print(format_output("[INFO] From the local database:", "yellow"))
    print(table(data, headers="keys") if data else "- Nothing found.")

    print

    print(format_output("[INFO] From DPCS service:", "yellow"))
    return cmd_exec(
        "sudo %s %s -d %s" % (
            "/usr/local/dpcs/lockerController.sh",
            operation,
            ' '.join(map(str, slots))
        ),
        interactive=True
    )


def slot_status(slots):

    result = list()

    for key, value in filter(
        lambda (key, value): key in slots,
        parsed_lockers().items()
    ):
        result.append(dict((
            ("#", key),
            ("active", value["businessState"] == "ACTIVE"),
            ("status", value["stateReason"]),
            ("updated", parse_datetime(value["lastBusinessStateChangeTime"])),
            ("open", value["status"]["open"]),
            ("occupied", value["status"]["full"]),
            ("checked", parse_datetime(value["status"]["lastScanDate"])),
        )))

    return result


def json():
    pass


if __name__ == "__main__":
    main()
