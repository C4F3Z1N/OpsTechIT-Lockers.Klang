#!/usr/bin/env python
# -*- coding: utf-8 -*-

#HELP	Checks the expected layout and pings each component (PCBs/SVB).

from json import load as json_load
from os import environ
from re import findall as re_findall

ENV = environ.copy()

def run_cmd(command, silent = True, shell = False):

	from subprocess import CalledProcessError, check_output

	if type(command) is str and not shell:
		command = command.split()

	try:
		output = check_output(command, shell = shell)
		result = True

	except CalledProcessError as exception:
		output = exception.output
		result = False

	return result if silent else output

def ping(host, size = 4, silent = True):

	size = 1 if size < 1 else int(size)

	return run_cmd("ping -c %d %s" % (size, host), silent = silent)

def multi_ping(hosts, size = None, silent = True):

	from multiprocessing import Pool

	pool = Pool(len(hosts))

	result = [[h, pool.apply_async(ping, args = (h, size, silent))] for h in hosts]

	pool.close()
	pool.join()

	return [[ip, pool.get()] for ip, pool in result]

def get_layout(loaded_json):

	if "kioskLayoutArrangement" in loaded_json:
		return loaded_json["kioskLayoutArrangement"]

	else:
		layout = [None] * len(loaded_json["columns"])

		for column in loaded_json["columns"]:
			layout[column["position"] - 1] = len(column["rows"])

		result = list()

		for i in range(0, len(layout), 2):

			slots = layout[i] + layout[i + 1]

			if slots == 1: component_type = 'F'
			elif slots == 3: component_type = 'Q'
			else: component_type = 'A'

			result.append(component_type)

		starter = loaded_json["starterColumnPosition"]
		result[(starter / 2 + starter % 2) - 1] = 'S'

		return ''.join(result)

def get_dials(layout):

	left, right = layout.split('S')

	left = range(11, 11 + 2 * len(left), 2)[::-1]
	right = range(12, 12 + 2 * len(right), 2)

	return left + [10] + right

def get_ips(dials):

	command = "ip -4 addr show eth1"

	base = run_cmd(command, silent = False)

	base = base.split("inet ")[1].split("/")[0].split('.')[:-1]

	return ['.'.join(map(str, base + [i])) for i in dials]

def get_macaddr(host):

	command = "arp -a %s" % host

	result = run_cmd(command, silent = False)

	return result.split("at")[1].split()[0].upper()

def format_text(text, color = None, bold = False):

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

	if not color:
		return "\033[%dm%s\033[0m" % (bold, text)

	else:
		return "\033[%d;%dm%s\033[0m" % (bold, colors[color.lower()], text)

def process_ping(keywords, output):

	result = dict()

	for k in keywords:
		for o in output:
			if k in o:
				result[k] = re_findall(r'\d+', o)
				if len(result[k]) > 1: raise ValueError
				else: result[k] = int(result[k][-1])

	return result

if __name__ == "__main__":

	size = (int(ENV["LOG_SIZE"]) / 3) if "LOG_SIZE" in ENV else 10

	try:
		with open("/var/tmp/kioskConfig.json", 'r') as json_file:
			kiosk_color = "silver" if json_load(json_file)["kioskType"] == "OmniKiosk" else "yellow"

		with open("/kiosk/data/dpcs/kioskPhysicalLayout.json", 'r') as json_file:
			physicallayout_json = json_load(json_file)

		layout = get_layout(physicallayout_json)
		dials = get_dials(layout)

	except IOError as exception:
		layout = "Unknown"
		dials = range(10, 51)
		kiosk_color = "red"
		print "\"%s\" not found. IP range set from %d to %d.\n" % (exception.filename, dials[0], dials[-1])

	print format_text("EXPECTED LAYOUT:", bold = True) + '\n- ' + format_text(layout, kiosk_color, bold = True)

	print format_text("\nTYPE\t\tIP\t\tMAC\t\tRECV/SENT (PACKETS)", bold = True)

	try:
		for ip, result in multi_ping(get_ips([250] + dials), size, silent = False):

			mac = get_macaddr(ip)
			component = int(ip.split('.')[-1])
			result = process_ping(["transmitted", "received", "loss"], result.split("statistics")[-1].split(','))

			if component in dials and layout != "Unknown":
				component = format_text(layout[dials.index(component)], kiosk_color, bold = True)

			elif component == 250: component = "SVB"
			else: component = "???"

			if not result["loss"]: result_color = "green"
			elif result["loss"] >= 25: result_color = "red"
			else: result_color = "yellow"

			result = format_text("%d/%d" % (result["received"], result["transmitted"]), result_color, bold = True)

			print "%s\t%s\t%s\t%s" % (component, ip, mac if len(mac) == 17 else "\t???\t", result)

	except KeyboardInterrupt:
		pass
