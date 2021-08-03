#!/usr/bin/env python3
#! -*- coding:utf8 -*-

import os
import sys
import hashlib
import queue

import time
import requests
import copy
import json
import threading
import random
import operator
import re
from urllib.parse import urljoin

from common.slogging import slog
import common.daemon as daemon

import agent.metrics_rules as metrics_rules
import agent.global_var as gl

# from agent.cpu import CpuWatch
# from agent.net import BandwidthWatch

ALARMQ = queue.Queue(2000)
ALARMQ_HIGH = queue.Queue(2000)

gconfig = {
    'global_sample_rate': 1000,  # sample_rate%。
    'alarm_pack_num': 4,   # upload alarm size one time
    'config_update_time': 5 * 60,  # 5 min
}
# keep all nodeid existing: key is node_id, value is timestamp (ms)
NodeIdMap = {}
mark_down_flag = False

alarm_database_name = 'test_database_name'
alarm_proxy_host = '127.0.0.1:9090'
# top-dw-host = '142.93.126.168:9010'
# host = '161.35.114.185:9010'
mysession = requests.Session()
mypublic_ip_port = '127.0.0.1:800'
my_root_id = ''


def clear_queue():
    global ALARMQ, ALARMQ_HIGH
    while not ALARMQ.empty():
        ALARMQ.get()
    while not ALARMQ_HIGH.empty():
        ALARMQ_HIGH.get()
    slog.info("clear alarmqueue/alarm_high_queue")


def print_queue():
    global ALARMQ, ALARMQ_HIGH
    slog.info("alarmqueue.size = {0}, alarm_queue_high.size = {1}".format(
        ALARMQ.qsize(), ALARMQ_HIGH.qsize()))


def put_alarmq(alarm_payload):
    global ALARMQ
    try:
        ALARMQ.put(alarm_payload, block=True, timeout=2)
        # slog.info("put send_queue:{0} size:{1}, item:{2}".format(
        #     ALARMQ, ALARMQ.qsize(), json.dumps(alarm_payload)))
    except Exception as e:
        slog.warn("queue full, drop alarm_payload")
        return False
    return True

# with high priority and reliable


def put_alarmq_high(alarm_payload):
    global ALARMQ_HIGH
    try:
        ALARMQ_HIGH.put(alarm_payload, block=True, timeout=2)
        slog.info("put alarm_queue_high:{0} size:{1} item:{2}".format(
            ALARMQ_HIGH, ALARMQ_HIGH.qsize(), json.dumps(alarm_payload)))
    except Exception as e:
        slog.warn("queue full, drop alarm_payload")
        return False
    return True


class Log_Filter:
    def __init__(self, metrics_rule_map: dict):

        # patten:
        self.metrics_log_patten = "\[metrics\](.*)"
        # {"category":"p2p","tag":"electvhost_recv","type":"real_time","content":{"local_gid":"xxxxxxxxxxx","chain_hash":1021694032,"chain_msgid":131076,"packet_size":1136,"chain_msg_size":454,"hop_num":3,"recv_timestamp":1611125860755,"src_node_id":"ff0000010000ffffffffffffffffffff0000000037d716e05aa7c715209a128cd7642986","dest_node_id":"ff0000010000ffffffffffffffffffff0000000037d716e05aa7c715209a128cd7642986","is_root":0,"broadcast":1}}
        self.metrics_real_time = "{\"category\":\"(.*)\",\"tag\":\"(.*)\",\"type\":\"real_time\",\"content\":(.*)}"

        # [metrics]{"category":"vhost","tag":"handle_data_ready_called","type":"flow","content":{"count":6047,"max_flow":11,"min_flow":1,"sum_flow":7249,"avg_flow":1,"tps_flow":297,"tps":"1.65"}}
        # [metrics]{"category":"vhost","tag":"handle_data_ready_called_time","type":"timer","content":{"count":6047,"max_time":150334,"min_time":161,"avg_time":740}}
        # [metrics]{"category":"dataobject","tag":"xreceiptid_pair_t","type":"counter","content":{"count":960,"value":2}}
        self.metrics_format = "{\"category\":\"(.*)\",\"tag\":\"(.*)\",\"type\":\"(.*)\",\"content\":(.*)}"

        # metrics category && rules
        self.metrics_category = {}
        self.metrics_rule_map = metrics_rule_map
        for _category, _tags in self.metrics_rule_map.items():
            self.metrics_category[_category] = []
            for _tag in _tags.keys():
                self.metrics_category[_category].append(_tag)

    def match_line(self, line: str):
        result = re.findall(self.metrics_log_patten, line)
        if result:
            result = re.findall(self.metrics_format, result[0])
            if result:
                category, tag, type, content = result[0]
                # XMETRICS_PACKET_INFO
                if type == "real_time":
                    if category in self.metrics_category and tag in self.metrics_category[category]:
                        rule = self.metrics_rule_map[category][tag]
                        ret, payload = rule(content)
                        # slog.info("{0} {1} {2}".format(
                        #     category, tag, content))
                        # slog.info("{0}: {1}".format(ret,payload))
                        if ret:
                            # print(payload)
                            put_alarmq(payload)
                            return True
                # XMETRICS_PACKET_ALARM
                elif type == "alarm":
                    metrics_info = {
                        'send_timestamp': int(time.time()),
                        'category': category,
                        'tag': tag,
                        'kv_content':json.loads(content)
                    }
                    payload = json.dumps({
                        "alarm_type": "metrics_alarm",
                        "packet": metrics_info
                    })
                    print(payload)
                    put_alarmq_high(payload)
                    return True
                # XMETRICS_COUNTER/TIMER/FLOW
                elif type in ["flow", "timer", "counter", "array_counter"]:
                    # print(category, tag, content)
                    metrics_info = {
                        # 'env': alarm_database_name,
                        # 'public_ip': gl.get_ip(),
                        'send_timestamp': int(int(time.time())/300)*300,
                        'category': category,
                        'tag': tag,
                    }
                    json_content = json.loads(content)
                    for key in json_content:
                        metrics_info[key] = json_content[key]
                    payload = json.dumps({
                        "alarm_type": "metrics_"+type, "packet": metrics_info
                    })
                    # print(payload)
                    put_alarmq(payload)

                    return True
                else:
                    slog.info("unknown metrics check log.{0}".format(line))
                    return False

        return False

    def grep_log(self, line: str):
        global mark_down_flag
        # TODO(smaug) using a better way to handle xtopchain down flag
        mark_down_flag = False

        ret = self.match_line(line)
        return ALARMQ.qsize(), ALARMQ_HIGH.qsize()


class log_monitor:
    def __init__(self):
        self.callbackhub = metrics_rules.CallBackHub()
        metrics_rule_map = {
            # # p2pperf -> rrs gossip only:
            # "p2pperf":{
            #     "vhostrecv_info": self.callbackhub.p2pbroadcast_message_recv_rule,
            #     "wrouterrecv_info": self.callbackhub.p2pbroadcast_message_recv_rule,
            #     "wroutersend_info": self.callbackhub.p2pbroadcast_message_send_rule
            # },
            # "p2pnormal": {
            #     "vhostrecv_info": self.callbackhub.p2pbroadcast_message_recv_rule,
            #     "wrouterrecv_info": self.callbackhub.p2pbroadcast_message_recv_rule,
            #     "wroutersend_info": self.callbackhub.p2pbroadcast_message_send_rule
            # },
            "p2p":{
                "kad_info": self.callbackhub.p2pkadinfo_rule,
            },
            "p2pbroadcast":{
                "wroutersend_info": self.callbackhub.p2pbroadcast_message_send_rule,
                "vhostrecv_info": self.callbackhub.p2pbroadcast_message_recv_rule,
            },
            "vnode":{
                "status": self.callbackhub.vnode_status_rule,
            },
            "xsync":{
                "interval": self.callbackhub.sync_interval_rule,
            },
            "txpool":{
                "state": self.callbackhub.txpool_state_rule,
                "receipt_delay": self.callbackhub.txpool_receipt_delay_rule,
                "cache": self.callbackhub.txpool_cache_rule,
            },
        }
        self.log_filter = Log_Filter(metrics_rule_map)

    def run_watch(self, filename='./xtop.log'):
        global ALARMQ, ALARMQ_HIGH
        clear_queue()
        offset = 0
        while True:
            time.sleep(1)
            offset = self.watchlog(filename, offset)
            slog.info("grep_log finish, alarmqueue.size = {0} alarmq_high.size = {1}, offset = {2}".format(
                ALARMQ.qsize(), ALARMQ_HIGH.qsize(), offset))

    def watchlog(self, filename, offset=0):
        try:
            #log_handle = open(filename, 'r',encoding="utf-8", errors='replace')
            log_handle = open(filename, 'r', encoding="utf-8", errors='ignore')
        except Exception as e:
            slog.warn("open file exception: {0}".format(e))
            return offset

        wait_num = 0
        # log_handle.seek(0, 2)   # go to end
        log_handle.seek(offset, 0)   # go to offset from head
        cur_pos = log_handle.tell()
        while True:
            cur_pos = log_handle.tell()
            try:
                line = log_handle.readline()
            except Exception as e:
                slog.warn(
                    "readline exception:{0}, cur_pos:{1}, time:{2}".format(e, cur_pos, int(time.time())))
                continue
            if not line:
                wait_num += 1
                log_handle.seek(cur_pos)  # go to cur_pos from head
                time.sleep(1)
                # slog.info("sleep 1 s, cur_pos: {0}".format(cur_pos))
                # print_queue()
                if wait_num > 4:
                    slog.debug("file: {0} done watch, size: {1}".format(
                        filename, cur_pos))
                    break
            else:
                send_size, recv_size = self.log_filter.grep_log(line)
                wait_num = 0

        # judge new file "$filename" created
        if not os.path.exists(filename):
            return cur_pos
        try:
            new_log_handle = open(filename, 'r', encoding="utf-8", errors='ignore')
        except Exception as e:
            return cur_pos

        new_log_handle.seek(0, 2)   # go to end
        new_size = new_log_handle.tell()

        if new_size > cur_pos:
            return cur_pos
        if new_size == cur_pos:
            slog.info('logfile:{0} maybe stopped'.format(filename))
            return cur_pos

        # new file "$filename" created
        slog.info("new file: {0} created".format(filename))
        return 0


def do_alarm(alarm_list):
    global alarm_proxy_host
    url = 'http://' + alarm_proxy_host
    url = urljoin(url, '/api/alarm/')
    my_headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
    }
    my_data = {
        'token': 'testtoken',
        'public_ip': gl.get_ip(),
        'env': alarm_database_name,
        'data': [json.loads(_l) for _l in alarm_list],
    }
    my_data = json.dumps(my_data, separators=(',', ':'))
    # print("do_alarm: {0}".format(my_data))
    # print("[after]{0}".format(json.loads(my_data)))
    try:
        res = mysession.post(url, headers=my_headers, data=my_data, timeout=5)
        if res.status_code == 200:
            if res.json().get('status') == 0:
                # slog.info("send alarm ok, response: {0}".format(res.text))
                return True
            else:
                slog.warn("send alarm fail, response: {0}".format(res.text))
        else:
            slog.warn('send alarm fail: {0}'.format(res.text))
    except Exception as e:
        slog.warn("exception: {0}".format(e))

    return False


def do_alarm_tz(alarm_list: list):
    # global alarm_proxy_host
    # url = 'http://' + alarm_proxy_host
    # url = urljoin(url, '/api/alarm/')

    url = 'https://dt-apigateway-log.dt-pn1.com/report/log/async/'
    # 
    my_headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
    }
    # print("alarm_list: {0}".format(alarm_list))
    msg_data = {
        "data": [json.loads(_l) for _l in alarm_list],
        "public_ip":gl.get_ip(),
        "env":alarm_database_name,
    }
    msg_data = json.dumps(msg_data, separators=(',', ':'))
    print("msg_data : {0}".format(msg_data))
    # print("msg_data:len : {0}".format(len(msg_data)))
    data_sha = ""
    if len(msg_data) <= 128:
        data_sha = hashlib.sha256(msg_data.encode('utf-8')).hexdigest()
    else:
        new_str = msg_data[0:64]+msg_data[-64:]
        # print("new_str: {0}".format(new_str))
        data_sha = hashlib.sha256(new_str.encode('utf-8')).hexdigest()

    # print("sign: {0}".format(data_sha))

    post_data = {
        "topic": "tz_chain",
        "msg": msg_data,
        "sign": data_sha
    }
    post_data = json.dumps(post_data)

    print("do_alarm: {0}".format(post_data))
    # return
    try:
        res = mysession.post(url, headers=my_headers,
                             data=post_data, timeout=5)
        if res.status_code == 200:
            if res.json().get('status') == 0 or res.json().get('status') == 200:
                slog.info("send alarm ok, response: {0}".format(res.text))
                return True
            else:
                slog.warn("send alarm fail, response: {0}".format(res.text))
        else:
            slog.warn('send alarm fail: {0}'.format(res.text))
    except Exception as e:
        slog.warn("exception: {0}".format(e))

    return False


def consumer_alarm():
    global ALARMQ, ALARMQ_HIGH, gconfig
    alarm_pack_num = gconfig.get('alarm_pack_num')
    th_name = threading.current_thread().name
    alarm_list = []
    while True:
        try:
            # slog.info("consumer thread:{0} send_queue:{1} size:{2}".format(
            #     th_name, ALARMQ, ALARMQ.qsize()))
            while not ALARMQ.empty():
                alarm_payload = ALARMQ.get()
                alarm_list.append(alarm_payload)

                if len(alarm_list) >= alarm_pack_num:
                    # slog.info("alarm do_alarm")
                    do_alarm(alarm_list)
                    # do_alarm_tz(alarm_list)
                    alarm_list.clear()

            time.sleep(1)
        except Exception as e:
            pass


def consumer_alarm_high():
    global ALARMQ, ALARMQ_HIGH, gconfig
    th_name = threading.current_thread().name
    alarm_pack_num = gconfig.get('alarm_pack_num')
    alarm_pack_num = 1
    alarm_list = []
    while True:
        try:
            # slog.info("consumer thread:{0} recv_queue:{1} size:{2}".format(
            #     th_name, ALARMQ_HIGH, ALARMQ_HIGH.qsize()))
            while not ALARMQ_HIGH.empty():
                alarm_payload = ALARMQ_HIGH.get()
                alarm_list.append(alarm_payload)

                if len(alarm_list) >= alarm_pack_num:
                    # slog.info("alarm_high do_alarm")
                    if not do_alarm(alarm_list):
                        slog.warn("alarm_high send failed, put in queue again")
                        for item in alarm_list:
                            put_alarmq_high(item)
                    alarm_list.clear()

            time.sleep(1)
        except Exception as e:
            pass


def run(args):
    global gconfig, alarm_database_name, alarm_proxy_host, mypublic_ip_port
    if args.alarm.find(':') == -1:
        slog.error('alarm proxy host invalid')
        return 1

    alarm_database_name = args.database.replace('.','_')
    alarm_proxy_host = args.alarm
    alarm_filename = args.file

    start_print = 'agent start... database:{0} host:{1} file:{2}\n'.format(
        alarm_database_name, alarm_proxy_host, alarm_filename)
    slog.info(start_print)
    print(start_print)

    if args.nodaemon:
        slog.warn("start as no-daemon mode")
    else:
        slog.warn("start as daemon mode")
        try:
            daemon.daemon_init()
        except RuntimeError as e:
            print(e, file=sys.stderr)
            raise SystemExit(1)

    log_m = log_monitor()

    watchlog_th = threading.Thread(
        target=log_m.run_watch, args=(alarm_filename, ))
    watchlog_th.daemon = True
    watchlog_th.start()
    slog.info("start watchlog thread")

    con_send_th = threading.Thread(target=consumer_alarm)
    con_send_th.daemon = True
    con_send_th.start()
    slog.info("start consumer_alarm thread")

    con_alarm_high_th = threading.Thread(target = consumer_alarm_high)
    con_alarm_high_th.daemon = True
    con_alarm_high_th.start()
    slog.info("start consumer_alarm_high thread")

    while True:
        time.sleep(1000)

    return 0
