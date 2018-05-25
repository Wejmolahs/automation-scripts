#!/usr/bin/python2

'''
=== PREREQUISITES ===
Run in Python 2

Install requests library, via macOS terminal:
sudo pip install requests

=== DESCRIPTION ===
This script takes an array of objects (from CSV, headers: PortNumber, PortName, Switch SerialNumber) of switch port #'s and names, and applies them to a given switch in Meraki


=== USAGE ===
python import_ports.py -k <api_key> -o <org_id> -s <search_parameter> [-t <time>] -p <policy>
The -s parameter will be either a local file of MAC addresses (one per line), a currently configured port tag in Dashboard, or the currently configured access policy (number of policy slot) on the Switch > Access policy page. Option -t, if using input list of MACs, to only search for clients that were last seen within t minutes, default is 15. -p specifies the slot # of the new access policy to configure on matching ports.

'''

import getopt
import json
import requests
import sys
import csv
from datetime import datetime

# Prints a line of text that is meant for the user to read
def printusertext(p_message):
	print('# %s' % p_message)

# Prints help text
def printhelp():
	printusertext('This script finds all MS switchports that match the input search parameter,')
	printusertext('searching either by clients from a file listing MAC addresses (one per line),')
	printusertext('a specific tag in Dashboard currently applied to ports, or the specific')
	printusertext('access policy currently configured. It then changes the configuration of the')
	printusertext('port by applying the new access policy specified. Its counterpart script')
	printusertext('find_ports.py can be first used to check, as it does not change any configs.')
	printusertext('')
	printusertext('Usage:')
	printusertext('python update_ports.py -k <api_key> -o <org_id> -f path_to_csv_file')
	printusertext('The -s parameter will be either a local file of MAC addresses (one per line),')
	printusertext('a currently configured port tag in Dashboard, or the currently configured')
	printusertext('access policy (number of policy slot) on the Switch > Access policy page.')
	printusertext('Option -t, if using input list of MACs, to only search for clients')
	printusertext('that were last seen within t minutes, default is 15.')
	printusertext('-p specifies the slot # of the new access policy to configure on matching ports.')

# Internal functions (List networks, get inventory, list switch ports, get port details, update switch ports, etc.)

def list_networks(api_key, org_id):
	url = 'https://dashboard.meraki.com/api/v0/organizations/{}/networks'.format(org_id)
	try:
		response = requests.get(url=url, headers={'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'})
		return json.loads(response.text)
	except requests.exceptions.RequestException as e:
		print('Error calling list_networks: {}'.format(e))

def get_inventory(api_key, org_id):
	url = 'https://dashboard.meraki.com/api/v0/organizations/{}/inventory'.format(org_id)
	try:
		response = requests.get(url=url, headers={'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'})
		#print(response)
		return json.loads(response.text)
	except requests.exceptions.RequestException as e:
		print('Error calling get_inventory: {}'.format(e))

def list_switch_ports(api_key, serial):
	url = 'https://dashboard.meraki.com/api/v0/devices/{}/switchPorts'.format(serial)
	try:
		response = requests.get(url=url, headers={'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'})
		return json.loads(response.text)
	except requests.exceptions.RequestException as e:
		print('Error calling list_switch_ports with serial number {}: {}'.format(serial, e))

def get_port_details(api_key, serial, number):
	url = 'https://dashboard.meraki.com/api/v0/devices/{}/switchPorts/{}'.format(serial, number)
	try:
		response = requests.get(url=url, headers={'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'})
		return json.loads(response.text)
	except requests.exceptions.RequestException as e:
		print('Error calling get_port_details with serial {} and port {}: {}'.format(serial, number, e))

def update_switch_port(api_key, serial, number, data):
	url = 'https://dashboard.meraki.com/api/v0/devices/{}/switchPorts/{}'.format(serial, number)
	#url = 'http://127.0.0.1/{}/{}'.format(serial,number)
	try:
		response = requests.put(url=url, data=data, headers={'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'})
		if debug > 0:
			print('update_switch_port HTTP Status for port %s' % number)
			print(response)
		if debug > 1:
			print('URL:'+url)
			print('Data: '+data)
		return json.loads(response.text)
	except requests.exceptions.RequestException as e:
		print('Error calling update_switch_port with serial {}, port {}, and data {}: {}'.format(serial, number, data, e))

def list_clients(api_key, serial, timestamp=86400): # timestamp in seconds
	url = 'https://dashboard.meraki.com/api/v0/devices/{}/clients?timespan={}'.format(serial, timestamp)
	try:
		response = requests.get(url=url, headers={'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'})
		return json.loads(response.text)
	except requests.exceptions.RequestException as e:
		print ('Error calling list_clients with serial {}: {}'.format(serial, e))


def main(argv):
	# Set default values for command line arguments
	API_KEY = ORG_ID = ARG_SEARCH = ARG_TIME = ARG_POLICY = ARG_FILE = 'null'
	
	#SET DEBUG LEVEL - 1 IS BASIC, 2 IS VERBOSE
	global debug 
	debug = 0
	# Get command line arguments
	try:
		opts, args = getopt.getopt(argv, 'hk:o:f:')
	except getopt.GetoptError:
		printhelp()
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			printhelp()
			sys.exit()
		elif opt == '-k':
			API_KEY = arg
		elif opt == '-o':
			ORG_ID = arg
        elif opt == '-f':
            ARG_FILE = arg
			
	# Check if all parameters are required parameters have been given
	if API_KEY == 'null' or ORG_ID == 'null' or ARG_FILE == 'null':
		 printhelp()
		 sys.exit(2)
		
	# Assign search parameter
	search_file = search_policy = search_tag = None
	try:
	# Check if search parameter is file
		search_file = open(ARG_SEARCH)
	except IOError:
		try:
			# Check if search parameter is number
			search_policy = int(ARG_SEARCH)
		except ValueError:
			search_tag = ARG_SEARCH
	#session = requests.session()
	
######

#Build array of ports per switch from search_file. Starting with 1 before I get ahead of myself. TODO: do more than one switch
#if search_file is not None: TODO: RE-INSERT IF CONDITION
		# Searching on file with list of ports
		if debug > 1:
            print('Building array from %s' % (search_file))

	dataFile = open(ARG_FILE, 'rU') #Must open in universal newline file mode
	getFile = csv.reader(dataFile, delimiter=',') #removed list( )
	portsAndNames = list(getFile)
	
	############
	if debug > 1:
		print(portsAndNames[1])
			


	#FOR each portNumber, Assign #name 
	for i in portsAndNames:
		for j in portsAndNames[1:]:
			portNum = j[0]
			portName = j[1]
			serial = j[2]
			data = '{"name": "%s"}' % portName
			if debug > 1:
				print ('######################### Attempting to apply name to port %s #########################' % portNum)
				print("data variable sent to update_switch_port function ====:   %s   " %data)
			update_switch_port(API_KEY, serial, portNum, data)
				except IOError
					print('error, couldnt update switch port')
					print('Tried to update switch port '+portNum+'on switch'+serial+'to have name'+portName)
			if debug >1:
				print('Updated switch port "'+portNum+'" on switch "'+serial+'" to have name "'+portName+'"')


if __name__ == '__main__':
	startTime = datetime.now()
	print('Starting script at: %s' % startTime)
	print('Arguments entered: %s' % sys.argv[1:])
	main(sys.argv[1:])
	print('Ending script at: %s' % datetime.now())
	print('Total run time: %s' % (datetime.now() - startTime))
	
