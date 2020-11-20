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

    # affected slots verification;

    kiosk = parsed_lockers()

    if len(args.slots) == 1 and str(args.slots[-1]).lower() == "all":
        args.slots = kiosk.keys()

    else:
        args.slots = map(int, args.slots)

    # slot existence verification;

    if all(slot in kiosk.keys() for slot in args.slots):
        pass

    else:
        not_found = set(args.slots) - set(kiosk.keys())
        args.slots = set(args.slots) - not_found

        warn = format_output("[WARN] Slot(s) #%s not found.", "magenta")
        print(warn % ", #".join(map(str, sorted(not_found))))

    # output/operation;

    print(format_output("[INFO] From the local database:", "yellow"))

    data = slot_status(args.slots)
    for line in data:
        color = "green" if line.pop("active") else "red"
        line["status"] = format_output(line["status"], color, bold=True)
        for key in ("updated", "checked"):
            line[key] = parse_datetime(line[key], humanize=True)

    print(table(data, headers={
        k: format_output(k.capitalize(), bold=True)
        for k in data[-1].keys()
    }) if data else "- Nothing found.")

    print

    print(format_output("[INFO] From DPCS service:", "yellow"))

    controller(args.operation, args.slots)


def parsed_lockers():
    return {
        locker.pop("lockerId"): locker
        for locker in lockers()
    }


def controller(operation, slots, interactive=True):

    # operation definition;

    if "sens" in str(operation).lower():
        operation = "-w -s"

    elif "open" in str(operation).lower():
        operation = "-o"

    else:
        raise NotImplementedError

    return cmd_exec(
        "sudo %s %s -d %s" % (
            "/usr/local/dpcs/lockerController.sh",
            operation,
            ' '.join(map(str, slots))
        ),
        interactive=interactive
    ) if slots else None


def slot_status(slots):
    return [
        dict((
            ("#", key),
            ("active", value["businessState"] == "ACTIVE"),
            ("status", value["stateReason"]),
            ("updated", parse_datetime(value["lastBusinessStateChangeTime"])),
            ("open", value["status"]["open"]),
            ("occupied", value["status"]["full"]),
            ("checked", parse_datetime(value["status"]["lastScanDate"])),
        ))
        for key, value in parsed_lockers().items() if key in slots
    ]


def json():
    pass


if __name__ == "__main__":
    main()
