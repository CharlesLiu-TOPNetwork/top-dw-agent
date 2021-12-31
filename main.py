#!/usr/bin/env python3
#! -*- coding:utf8 -*-

import sys
if sys.version_info.major != 3:
    print("Python2 not supported, Please use python3 run again.")
    sys.exit(1)

import argparse
import setproctitle

import common.slogging as slogging

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.description='TOP-Argus Agent，拉取远程配置，报警采集并上报'
    parser.add_argument('-a', '--alarm', help='alarm proxy host, agent pull config and push alarm to this proxy host, eg: 127.0.0.1:9090', default='127.0.0.1:9090')
    parser.add_argument('-f', '--file', help="log file for agent to watch, eg: ./xtop.log", default='/chain/log/xtop.log')
    parser.add_argument('-d', '--database', help="set this environment name, which decide to store in which database", default='test_database_name')
    parser.add_argument('-p', '--port', help="set this port of monitor comunication, which will be added to public_ip:public_port", default='9000')
    parser.add_argument('--split', action='store_true',  help='agent will auto split database by add date-suffix, default false')
    parser.add_argument('--local', action='store_true',  help='agent will use local ip (used when depoly in local net) default false')
    parser.add_argument('--nodaemon', action='store_true', help='start as no-daemon mode')
    args = parser.parse_args()

    # set process title
    proc_title = 'topargus-agent: '
    for i in range(len(sys.argv)):
        proc_title = '{0} {1}'.format(proc_title, sys.argv[i])
    setproctitle.setproctitle(proc_title)

    from agent import argus_agent
    slogging.start_log_monitor()
    r = argus_agent.run(args)
    sys.exit(r)
