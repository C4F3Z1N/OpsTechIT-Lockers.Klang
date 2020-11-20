#!/usr/bin/env python
# -*- coding: utf-8 -*-

from contextlib import contextmanager
from datetime import date, timedelta
from glob import glob
from itertools import chain
from os import chdir, getcwd, getenv, path
from requests import Session, Timeout
from requests.packages.urllib3 import disable_warnings
from sys import argv, exit
import logging as _logger
import signal


# _logger.basicConfig(level=_logger.DEBUG)
_logger.getLogger().setLevel(getenv("DEBUG_LEVEL", 0))
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


def format_output(text, color=None, bold=False):

    gray = 2
    colors = {
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "magenta": 35,
        "cyan": 36,
        "gray": gray,
        "silver": gray,
        "beige": gray,
        "ink": gray,
        "black": gray,
    }

    for c in colors.keys():
        if c in str(color).lower():
            color = c

    if color not in colors:
        return "\033[%dm%s\033[0m" % (bold, text)

    else:
        return "\033[%d;%dm%s\033[0m" % (bold, colors[color], text)


def fetch(url, headers=None, warnings=False, verify=False):

    if not warnings:
        disable_warnings()

    with Session() as s:

        if headers:
            s.headers.update(headers)

        s.verify = verify

        return s.get(url)


def ignore_warnings(f):
    from functools import wraps
    from warnings import catch_warnings, simplefilter

    @wraps(f)
    def inner(*args, **kwargs):
        with catch_warnings(record=True):
            simplefilter("ignore")
            response = f(*args, **kwargs)
        return response
    return inner


@ignore_warnings
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
    for n in str(cmd_exec("arp -a %s" % ip, interactive=False)).split():
        if len(n.split(':')) == 6:
            return n.upper()


def table(*args, **kwargs):
    from tabulate import tabulate

    if not kwargs.get("tablefmt"):
        kwargs["tablefmt"] = "plain"

    return tabulate(*args, **kwargs)


def read_logs(log_path, days_ago=None):

    if isinstance(log_path, str):
        raise TypeError("'str' is not accepted.")
    else:
        iter(log_path)

    expanded = list(chain.from_iterable(map(glob, log_path)))

    if days_ago:
        days_ago *= -1 if days_ago > 0 else 1
        log_path = set()
        for d in map(str, date_range(days_ago)):
            log_path.update([path for path in expanded if d in path])
    else:
        log_path = expanded

    result = set()
    for path in log_path:
        with open_logfile(path) as file:
            result.update(file.readlines())

    return sorted(result)


# def read_logs(log_path, days_ago=None):
#     return chain.from_iterable(_read_logs(log_path, days_ago))


@contextmanager
def open_logfile(path, function=None):

    if not function:
        if path.split('.')[-1].lower() == "gz":
            from gzip import open as gzip_open
            function = gzip_open

        else:
            function = open

    try:
        with function(path) as logfile:
            yield logfile

    finally:
        pass


def str_cleanup(r_iter, r_string):

    result = r_string

    for i in r_iter:
        result = str().join(filter(bool, result.split(i)))

    return str(result)


def api_request(call):

    if "Kiosk" in call.__name__:
        path = call.__name__
    else:
        path = "v1/%s/" % call.__name__

    def wrapper():
        return fetch("http://localhost:7777/%s" % path).json()
    return wrapper


@api_request
def getKioskInfo():
    pass


@api_request
def getKioskLayout():
    pass


@api_request
def lockers():
    pass


@api_request
def reservations():
    pass


@contextmanager
def timeout(time):

    def raise_timeout(signum, frame):
        raise Timeout

    # Register a function to raise a TimeoutError on the signal.
    signal.signal(signal.SIGALRM, raise_timeout)
    # Schedule the signal to be sent after ``time``.
    signal.alarm(time)

    try:
        yield

    except Timeout as exception:
        logger.debug([type(exception), exception.message, exception])
        pass

    finally:
        # Unregister the signal so it won't be triggered
        # if the timeout is not reached.
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


def tmp():
    logger.debug(argv)
    exit()
    pass
