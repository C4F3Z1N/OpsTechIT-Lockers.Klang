#!/usr/bin/env python
# -*- coding: utf-8 -*-


from collections import OrderedDict as dict
from common import (
    cmd_exec,
    format_output,
    # getenv,
    getKioskInfo as _getKioskInfo,
    getKioskLayout as _getKioskLayout,
    logger,
    mac_address,
    table,
)


def main():
    # log_size = int(getenv("LOG_SIZE", 30))
    # print(log_size)

    kiosk_config = _getKioskInfo()["kioskConfig"]

    if "kioskColor" in kiosk_config:
        kiosk_color = kiosk_config["kioskColor"].lower()

    else:
        kiosk_color = {
            "OmniKiosk": "silver",
            "DeliveryKiosk": "yellow"
        }[kiosk_config["kioskType"]]

    info = {
        "generation": generation(),
        "modules": layout(),
        "color": kiosk_color,
    }

    print(format_output("[INFO] Expected layout:", "yellow"))
    print(table((
        (
            format_output(key.capitalize(), bold=True),
            format_output(value, kiosk_color, bold=True)
        )
        for key, value in info.items()
    )))

    print   # simple line break

    print(format_output("[INFO] Ping results:", "yellow"))

    if info["generation"] <= 2:
        print("- Serial boards are unreachable by ping.")
        return

    boards = dict(zip(
        ip_dials('S', 250) + ip_dials(info["modules"]),
        ["SVB"] + list(info["modules"]),
    ))

    data = boards.keys()
    for key, value in multi_ping(data).items():
        result = {
            "type": format_output(boards[key], kiosk_color, bold=True),
            "ip": key,
        }
        color = "red"

        if value:
            color = "green" if not value["loss"] else color
            result["mac"] = mac_address(key)
            result["sent/recv"] = format_output("%d/%d" % (
                value["transmitted"],
                value["received"],
            ), color, bold=True)
        else:
            result["mac"] = format_output("?????", color, bold=True)
            result["sent/recv"] = format_output("0/0", color, bold=True)

        data[data.index(key)] = {
            format_output(r.upper(), bold=True): result[r]
            for r in result
        }

    print(table(data, headers="keys"))


def ping(host, size=10, interval=.2, interactive=False):

    def parse_output(output):
        stats = {
            "transmitted": None,
            "received": None,
            "loss": None,
        }

        line = filter(
            lambda line: all(s in line for s in stats.keys()),
            output.split("\n")
        )[-1].split(',')

        for key in stats.keys():
            # 12.5% packet loss
            value = filter(lambda x: key in x, line)[-1]
            # 12.5%
            value = value.split()[0]
            # 12.5
            value = float(value.strip('%')) if '%' in value else int(value)
            # "loss": 12.5
            stats[key] = value

        return stats

    result = cmd_exec(
        "ping -c %d -i %f %s" % (size, interval, host),
        interactive=interactive
    )

    return parse_output(result) if not interactive and result else result


def generation():

    options = {
        "ZHILAI_GEN_4": 4,
        "ZHILAI_GEN_3": 3,
        "ZHILAI_GEN_2_5": 2.5,
        "ZHILAI_GEN_2": 2,
    }

    query = _getKioskLayout()["generation"]

    try:
        return float(options[query])

    except Exception as e:
        logger.debug([type(e), e.message, e])

        for key, value in sorted(options.items(), reverse=True):
            if key in query:
                return float(value)


def layout():

    query = _getKioskLayout()

    try:
        return query["kioskLayoutArrangement"]

    except Exception as e:
        logger.debug([type(e), e.message, e])

        kiosk = {
            key: value for key, value in query.items()
            if key in ("columns", "starterColumnPosition")
        }

        layout = [
            len(column["rows"])
            for column in sorted(
                kiosk["columns"],
                key=lambda c: c["position"]
            )
        ]

        if generation() == 2:
            for k, v in enumerate(layout):
                if v == 1:
                    layout[k] = 'F'
                elif v <= 3:
                    layout[k] = 'Q'
                else:
                    layout[k] = 'A'

            layout[kiosk["starterColumnPosition"] - 1] = 'S'

        elif generation() <= 2.5:
            result = list()

            for k in range(0, len(layout), 2):
                slots = sum(layout[k:k + 2])

                if slots == 1:
                    component = 'F'
                elif slots <= 3:
                    component = 'Q'
                else:
                    component = 'A'

                result.append(component)

            starter = kiosk["starterColumnPosition"]
            result[(starter / 2 + starter % 2) - 1] = 'S'
            layout = result

        else:
            raise NotImplementedError

        return str().join(layout)


def ip_dials(layout, starter_ip=10):

    def sided_range(odd, n):
        s = starter_ip + int(not odd)
        n = 2 * n + s
        r = filter(lambda x: x % 2 == odd, range(s, n))
        return r[::-1] if odd else r

    # reversed_ip = "1.1.861.291"
    reversed_ip = cmd_exec("hostname -I", interactive=False).split()[-1][::-1]

    # base = "192.168.1."
    base = reversed_ip[reversed_ip.index('.'):][::-1]

    left, right = map(len, layout.split('S'))

    left = sided_range(True, left)
    right = sided_range(False, right)

    return [base + str(d) for d in left + [starter_ip] + right]


def multi_ping(hosts, size=10, interval=.2, interactive=False):

    from multiprocessing import Pool, cpu_count

    pool = Pool(cpu_count())

    execution = {
        h: pool.apply_async(ping, args=(h, size, interval, interactive))
        for h in hosts
    }

    pool.close()
    pool.join()

    return {
        key: value.get()
        for key, value in execution.items()
    }


if __name__ == "__main__":
    main()
