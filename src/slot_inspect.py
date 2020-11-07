#!/usr/bin/env python
# -*- coding: utf-8 -*-

from common import (
    cmd_exec,
    format_output,
    lockers,
    parse_datetime,
    table,
)


def main():
    from argparse import ArgumentParser

    args = ArgumentParser(description="Interact with slot(s).")

    args.add_argument(
        "operation",
        help="Either \"open\" (-o) or \"sensor\" (-s).",
        metavar="operation")

    args.add_argument(
        "slots",
        help="1 2 3... all",
        metavar="slots",
        nargs="*")

    args = args.parse_args()

    controller(args.operation, args.slots)


def controller(operation, slots):

    kiosk = {
        locker["lockerConfig"]["lockerId"]: locker
        for locker in lockers()
    }

    print(kiosk)

    if not operation or "sens" in str(operation).lower():
        operation = "-s"

    elif "open" in str(operation).lower():
        operation = "-o"

    else:
        raise NotImplementedError

    if len(slots) == 1 and str(slots[0]).lower() == "all":
        slots = kiosk.keys()

    else:
        slots = map(int, slots)

    if all(slot in kiosk.keys() for slot in slots):
        pass

    elif any(slot in kiosk.keys() for slot in slots):
        not_found = set(slots) - set(kiosk.keys())
        slots = list(set(slots) - not_found)

        warn = format_output("[WARN] Slots #%s weren't found.", "yellow")
        print(warn % ", #".join(map(str, not_found)))

    else:
        raise NotImplementedError

    print(format_output("[INFO] From the local database:", "yellow"))
    slot_print(slots)

    print

    print(format_output("[INFO] From DPCS service:", "yellow"))

    return cmd_exec(
        "sudo %s %s -d %s" % (
            "/usr/local/dpcs/lockerController.sh",
            operation,
            " ".join(map(str, slots))))


def slot_print(slots, full=True):

    header = ["#", "Status", "Updated"]

    if full:
        header += ["Open", "Occupied", "Scanned"]

    kiosk = lockers()
    data = list()

    for i in slots:

        if kiosk[i]["businessState"] == "ACTIVE":
            color = "green"

        else:
            color = "red"

        d = [
            i,
            format_output(kiosk[i]["stateReason"], color, True),
            parse_datetime(
                kiosk[i]["lastBusinessStateChangeTime"],
                humanize=True
            )
        ]

        if full:
            d += [
                kiosk[i]["status"]["open"],
                not kiosk[i]["status"]["empty"],
                parse_datetime(
                    kiosk[i]["status"]["lastScanDate"],
                    humanize=True
                )
            ]

        data.append(d)

    header = [format_output(h, bold=True) for h in header]

    print(table(data, headers=header))


def json():
    pass


if __name__ == "__main__":
    main()
