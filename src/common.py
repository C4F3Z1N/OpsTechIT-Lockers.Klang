#!/usr/bin/env python
# -*- coding: utf-8 -*-

from contextlib import contextmanager
from datetime import date, timedelta
from glob import glob
from os import chdir, getenv, getcwd, path
from requests import Session
from requests.packages.urllib3 import disable_warnings
import logging as _logger


_logger.basicConfig(level=_logger.DEBUG)
logger = _logger


def cmd_exec(command, interactive=True, shell=False):
    from subprocess import call, CalledProcessError, check_output

    if isinstance(command, str):
        command = command.split()

    if filter(path.dirname, command):
        i = command.index(filter(path.dirname, command)[0])

        if path.dirname(command[i]) != ".":
            with cd(path.dirname(command[i])):
                command[i] = path.join(".", path.basename(command[i]))
                return cmd_exec(command, interactive, shell)

    if interactive:
        return call(command, shell=shell) == 0

    else:
        result = False

        try:
            result = check_output(command, shell=shell)

        except CalledProcessError as exception:
            logger.debug(exception.output)

        return result


# https://stackoverflow.com/a/24176022
@contextmanager
def cd(newdir):

    prevdir = getcwd()
    chdir(path.expanduser(newdir))

    try:
        yield

    finally:
        chdir(prevdir)


def json_load(path):
    from json import load

    with open(path, "r") as file:
        return load(file)


def lockers():

    return {
        locker["lockerConfig"]["lockerId"]: locker
        for locker in json_load("/kiosk/data/dpcs/lockers.json")
    }


def format_output(text, color=None, bold=False):

    colors = {
        "silver": 2,
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "magenta": 35,
        "cyan": 36,
        "gray": 90
    }

    if color not in colors:
        return "\033[%dm%s\033[0m" % (bold, text)

    else:
        return "\033[%d;%dm%s\033[0m" % (bold, colors[color.lower()], text)


def fetch(url, headers=None, warnings=False, verify=False):

    if not warnings:
        disable_warnings()

    with Session() as s:

        if headers:
            s.headers.update(headers)

        s.verify = verify

        return s.get(url)


def parse_datetime(raw, template=None, humanize=False):
    from arrow import get

    if template:
        result = get(raw, template)

    else:
        result = get(raw)

    return result.humanize() if humanize else result.to("local").datetime


def date_range(num, start=date.today()):

    if num < 0:
        custom_range = [-n for n in range(num * -1 + 1)]
    else:
        custom_range = range(num + 1)

    return [start + timedelta(days=n) for n in custom_range]


def mac_address(ip):

    for n in str(cmd_exec("ip neigh", False)).split("\n"):
        if ip in n:
            return str(n.split()[-2]).upper()


def table(content, headers=()):
    from tabulate import tabulate

    return tabulate(content, headers=headers, tablefmt="plain")


def read_logs(log_path, days_ago=None):
    from gzip import open as gz_open

    if isinstance(log_path, str):
        raise TypeError("'str' is not accepted.")
    else:
        iter(log_path)

    expanded = set()
    for g in map(glob, log_path):
        expanded.update(g)

    if days_ago:
        days_ago *= -1 if days_ago > 0 else 1
        log_path = set()
        for d in map(str, date_range(days_ago)):
            log_path.update([path for path in expanded if d in path])
    else:
        log_path = expanded

    result = set()
    for i in log_path:
        file_open = gz_open if i.split('.')[-1].lower() == "gz" else open
        result.update(file_open(i).readlines())

    return sorted(result) if result else None


def tmp():
    getenv("USER")
    pass
