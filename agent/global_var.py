#!/usr/bin/env python3
#! -*- coding:utf8 -*-

import socket

def _init():
    global global_config
    global_config = {
        'global_sample_rate': 1000,  # sample_rate%。
        'alarm_pack_num': 2,  # upload alarm size one time
        'config_update_time': 5 * 60,  # 5 min
        'grep_broadcast': {
            'start':
            'true',
            'sample_rate':
            1000,  # 20%
            'alarm_type':
            'packet',
            # xnetwork_id:3Bytes zone_id:1Byte cluster_id:1Byte group_id:1Byte  = hex:12 size
            'network_focus_on': [
                'ff0000010000', 'ff0000020000', 'ff00000f0101', 'ff00000e0101',
                'ff00000001'
            ],  # src or dest: rec;zec;edg;arc;aud/val
            'network_ignore': [],  # src or dest
        },
        'grep_point2point': {
            'start':
            'true',
            'sample_rate':
            1000,  # 1%
            'alarm_type':
            'packet',
            'network_focus_on': [
                'ff0000010000', 'ff0000020000', 'ff00000f0101', 'ff00000e0101',
                'ff00000001'
            ],  # src or dest: rec;zec;edg;arc;aud/val
            'network_ignore': [],  # src or dest
        },
        'grep_networksize': {
            'start': 'true',
            'sample_rate': 1000,  # 5%
            'alarm_type': 'networksize',
        },
        'system_cron': {
            'start': 'true',
            'alarm_type': 'system',
        }
    }

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '0.0.0.0'
    finally:
        s.close()
    return IP

my_ip = get_local_ip()


def set_public_ip(local_ip):
    global my_ip
    my_ip = local_ip

def get_ip():
    global my_ip
    return my_ip

def set_value(name, value):
    global_config[name] = value


def get_value(name, defValue=None):
    try:
        return global_config[name]
    except KeyError:
        return defValue
