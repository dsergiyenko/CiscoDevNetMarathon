# -*- coding: utf-8 -*-

import re
import datetime
import os
import yaml
from netmiko import (NetMikoAuthenticationException, NetMikoTimeoutException, ConnectHandler)
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

BACKUP_FOLDER_PATH = './backup_folder/'

def backup_config(ConnectHandler_obj, hostname):
    command_output = ConnectHandler_obj.send_command('show run')
    if not os.path.exists(BACKUP_FOLDER_PATH):
        os.makedirs(BACKUP_FOLDER_PATH)
    with open(BACKUP_FOLDER_PATH + hostname + '_' + datetime.now().strftime("%Y_%m_%d-%H_%M_%S")  + '.txt', 'w') as f:
        f.write(command_output)

def get_cdp_status(ConnectHandler_obj):
    command_output = ConnectHandler_obj.send_command('show cdp neighbors')
    if 'CDP is not enabled' in command_output:
        return 'CDP is OFF|'
    else:
        result = re.findall(r'(\S+) +(\S+ \d+/\d+).+ (\S+ \d+/\d+)', command_output, re.MULTILINE)
        return 'CDP is ON,'+str(len(result)) +' peers|'

def get_software_version(ConnectHandler_obj):
    command_output = ConnectHandler_obj.send_command('show version')
    result = re.findall(r'Cisco .*\((\S+)\), Version|Cisco (\S+).*processor', command_output, re.MULTILINE)
    if 'NPE' in result[0][0]:
        return result[1][1] +'|'+ result[0][0]+'|NPE|'
    else:
        return result[1][1] +'|'+ result[0][0]+'|PE|'


def configure_ntp(ConnectHandler_obj):
    command_output = ConnectHandler_obj.send_command('show ntp status')
    if 'Clock is synchronized, stratum 9, reference is 192.168.10.4' in command_output:
        return 'Clock in Sync'
    else:
        command_output = ConnectHandler_obj.send_command('ping 192.168.10.4')
        if '!' in command_output:
            command_output = ConnectHandler_obj.send_config_set(['clock timezone GMT 0', 'ntp server 192.168.10.4', 'end', 'wr'])
            command_output = ConnectHandler_obj.send_command('show ntp status')
            if 'Clock is synchronized, stratum' in command_output:
                return 'Clock in Sync'
            elif 'Clock is unsynchronized' in command_output:
                return 'Clock not in Sync'

def connect_ssh(ne_data):
    result=''
    try:
        with ConnectHandler(**ne_data) as net_connect:
            net_connect.enable()
            hostname = net_connect.find_prompt()[:-1]
            result += hostname+'|'
            print('Connection to device: '+hostname )
            backup_config(net_connect, hostname)
            result += get_software_version(net_connect)
            result += get_cdp_status(net_connect)
            result += configure_ntp(net_connect)
            net_connect.disconnect()
    except (NetMikoTimeoutException, NetMikoAuthenticationException) as e:
        print(e)
    return result


def threads_conn(function, ne_data, limit=10):
    with ThreadPoolExecutor(max_workers=limit) as executor:
        f_result = executor.map(function, ne_data)
    return list(f_result)


if __name__ == '__main__':
    with open("routers.yaml") as devices_file:
        ne_data = yaml.safe_load(devices_file)
        all_done = threads_conn(connect_ssh, ne_data)
print(*all_done, sep='\n')













