import agent.global_var as gl
import json
import time
import random
import copy
import hashlib
import re
from common.slogging import slog
from common.config import dw_config

service_type_pattern = " .*\[network (.*)\]-\[zone (.*)\]-\[cluster (.*)\]-\[group (.*)\]-\[height (.*)\]"
def anaylse_service_type(type_info_str: str) -> str:
    result = re.findall(service_type_pattern, type_info_str)
    if not result:
        return False,0
    network_id, zone_id, cluster_id, group_id, height = result[0]
    network_id = int(network_id)
    zone_id = int(zone_id)
    cluster_id = int(cluster_id)
    group_id = int(group_id)
    height = int(height)
    if zone_id == 1 and cluster_id == 0 and group_id == 0:
        return "rec", height
    if zone_id == 2 and cluster_id == 0 and group_id == 0:
        return "zec", height
    if zone_id == 0 and cluster_id == 1:
        if group_id < 64:
            return "adv"+str(group_id), height
        else:
            return "con"+str(group_id), height
    if zone_id == 14 and cluster_id == 1 and group_id == 1:
        return "archive", height
    if zone_id == 15 and cluster_id == 1 and group_id == 1:
        return "edge", height
    return "unknown", height

class CallBackHub():
    def __init__(self):
        # xsync
        self.xsync_interval = 300
        self.xsync_cache = {
            "fast":{},
            "full":{},
        }

        # txpool
        self.txpool_interval = 300
    
    def p2ptest_send_record(self, content: str):
        '''
        {
            "category": "p2ptest",
            "tag": "send_record",
            "type": "real_time",
            "content": {
                "src_node_id": "2e4ffffff7e74b68.0698b35e1a699d2d",
                "dst_node_id": "5d6fffff66b167f2.fe8c9257b19dbc2e",
                "dst_ip_port": "192.168.50.139:9126",
                "hop_num": 2,
                "msg_hash": 2498826743,
                "msg_size": 0,
                "is_root": 1,
                "is_broadcast": 1,
                "timestamp": 1638785164577
            }
        }
        '''

        json_content = json.loads(content)
        rate_num = 2**dw_config['p2p_sample_rate_level']-1
        if(int(json_content["msg_hash"]) & rate_num) != rate_num:
            return False,{}
        packet_info = {}
        packet_info["src_node_id"] = json_content["src_node_id"]
        packet_info["dst_node_id"] = json_content["dst_node_id"]
        packet_info["dst_ip_port"] = json_content["dst_ip_port"]
        packet_info["hop_num"] = json_content["hop_num"]
        packet_info["msg_hash"] = json_content["msg_hash"]
        packet_info["msg_size"] = json_content["msg_size"]
        packet_info["is_root"] = json_content["is_root"]
        packet_info["is_broadcast"] = json_content["is_broadcast"]
        packet_info["timestamp"] = json_content["timestamp"]

        payload = {"alarm_type": "p2ptest_sendrecord", "packet": packet_info}

        return True, json.dumps(payload)

    def p2ptest_send_info(self, content: str):
        '''
        {
            "category": "p2ptest",
            "tag": "send_broadcast_info",
            "type": "real_time",
            "content": {
                "src_node_id": "23afffffa02048c9.0fe027cb6e6cbabe",
                "dst_node_id": "c9cfffffc2b35dff.bdf5ed38df1613e0",
                "hop_num": 0,
                "msg_hash": 2523515927,
                "msg_size": 0,
                "is_root": 1,
                "is_broadcast": 1,
                "timestamp": 1638785153596
            }
        }
        '''
        json_content = json.loads(content)
        rate_num = 2**dw_config['p2p_sample_rate_level']-1
        if(int(json_content["msg_hash"]) & rate_num) != rate_num:
            return False,{}
        packet_info = {}
        packet_info["src_node_id"] = json_content["src_node_id"]
        packet_info["dst_node_id"] = json_content["dst_node_id"]
        packet_info["hop_num"] = json_content["hop_num"]
        packet_info["msg_hash"] = json_content["msg_hash"]
        packet_info["msg_size"] = json_content["msg_size"]
        packet_info["is_root"] = json_content["is_root"]
        packet_info["is_broadcast"] = json_content["is_broadcast"]
        packet_info["timestamp"] = json_content["timestamp"]

        payload = {"alarm_type": "p2ptest_send_info", "packet": packet_info}

        return True, json.dumps(payload)

    def p2ptest_recv_info(self, content: str):
        '''
        {
            "category": "p2ptest",
            "tag": "vhostrecv_info",
            "type": "real_time",
            "content": {
                "src_node_id": "2e4ffffff7e74b68.0698b35e1a699d2d",
                "dst_node_id": "5dcfffff30c8f53c.24452e92cefe04e7",
                "hop_num": 1,
                "msg_hash": 2303518191,
                "msg_size": 0,
                "is_root": 1,
                "is_broadcast": 1,
                "packet_size": 280,
                "timestamp": 1638785164584
            }
        }
        '''
        json_content = json.loads(content)
        rate_num = 2**dw_config['p2p_sample_rate_level']-1
        if(int(json_content["msg_hash"]) & rate_num) != rate_num:
            return False,{}
        packet_info = {}
        packet_info["src_node_id"] = json_content["src_node_id"]
        packet_info["dst_node_id"] = json_content["dst_node_id"]
        packet_info["hop_num"] = json_content["hop_num"]
        packet_info["msg_hash"] = json_content["msg_hash"]
        packet_info["msg_size"] = json_content["msg_size"]
        packet_info["is_root"] = json_content["is_root"]
        packet_info["is_broadcast"] = json_content["is_broadcast"]
        packet_info["packet_size"] = json_content["packet_size"]
        packet_info["timestamp"] = json_content["timestamp"]

        payload = {"alarm_type": "p2ptest_recv_info", "packet": packet_info}

        return True, json.dumps(payload)


    def p2pkadinfo_rule(self, content: str):
        '''
        "content": {
            "local_nodeid": "f600000000040801.01c0000000000022",
            "service_type": " [network 0]-[zone 0]-[cluster 1]-[group 2]-[height 34]",
            "node_size": 7,
            "unknown_node_size": 0,
            "public_ip": "104.248.6.197",
            "public_port": 9000
        }
        "content": {
            "local_nodeid": "aa2fffff64b1bb93.971274084dd90fa8",
            "service_type": " [network 1048575]-[zone 50]-[cluster 44]-[group 110]-[height 1642408]",
            "neighbours": 41,
            "public_ip": "104.248.6.197",
            "public_port": 9000
        }
        '''
        json_content = json.loads(content)
        packet_info = {}
        if "neighbours" in json_content:
            # root
            packet_info["service_type"] = "root"
            packet_info["neighbours"] = json_content["neighbours"]
            packet_info["local_nodeid"] = json_content["local_nodeid"]
        else:
            # election:
            service_type,height = anaylse_service_type(json_content["service_type"])
            # print(content,service_type,height)
            # slog.info("{0}{1}{2}".format(content,service_type,height))
            if service_type == "unknown":
                return False,""
            packet_info["service_type"] = service_type
            packet_info["height"] = height
            packet_info["node_size"] = json_content["node_size"]
            packet_info["unknown_node_size"] = json_content["unknown_node_size"]
            packet_info["local_nodeid"] = json_content["local_nodeid"]
        packet_info["update_time"] = int(time.time())
        
        payload = {"alarm_type": "kadinfo", "packet": packet_info}
        return True, json.dumps(payload)

    def p2pbroadcast_message_send_rule(self, content: str):
        '''
        "content": {
            "src_node_id": "f60000ff020003ff.0200000000000000",
            "dst_node_id": "f60000ff020003ff.0200000000000000",
            "hop_num": 0,
            "msg_hash": 4279548633,
            "msg_size": 554,
            "is_root": 0,
            "is_broadcast": 1,
            "timestamp": 1625811480400
        }
        '''
        json_content = json.loads(content)
        m_hash = json_content["msg_hash"]
        rate_num = 2**dw_config['p2p_sample_rate_level']-1
        if(m_hash & rate_num) == rate_num:
            packet_info = {}
            packet_info["type"] = "send"
            packet_info["src_node_id"] = json_content["src_node_id"]
            packet_info["dst_node_id"] = json_content["dst_node_id"]
            packet_info["hop_num"] = json_content["hop_num"]
            packet_info["msg_hash"] = json_content["msg_hash"]
            packet_info["msg_size"] = json_content["msg_size"]
            packet_info["is_root"] = json_content["is_root"]
            packet_info["is_broadcast"] = json_content["is_broadcast"]
            packet_info["timestamp"] = json_content["timestamp"]
            
            payload = {"alarm_type":"p2pbroadcast","packet":packet_info}

            return True,json.dumps(payload)
        return False,""

    def p2pbroadcast_message_recv_rule(self, content: str):
        '''
        "content": {
            "src_node_id": "f60000ff020003ff.0200000000000000",
            "dst_node_id": "f60000ff020003ff.0200000000000000",
            "hop_num": 2,
            "msg_hash": 4279548633,
            "msg_size": 554,
            "is_root": 0,
            "is_broadcast": 1,
            "is_pulled": 0,
            "packet_size": 736,
            "timestamp": 1625811480401
        }
        '''
        json_content = json.loads(content)
        m_hash = json_content["msg_hash"]

        rate_num = 2**dw_config['p2p_sample_rate_level']-1
        if(m_hash & rate_num) == rate_num:
            packet_info = {}
            packet_info["type"] = "recv"
            packet_info["src_node_id"] = json_content["src_node_id"]
            packet_info["dst_node_id"] = json_content["dst_node_id"]
            packet_info["hop_num"] = json_content["hop_num"]
            packet_info["msg_hash"] = json_content["msg_hash"]
            packet_info["msg_size"] = json_content["msg_size"]
            packet_info["is_root"] = json_content["is_root"]
            packet_info["is_broadcast"] = json_content["is_broadcast"]
            packet_info["packet_size"] = json_content["packet_size"]
            packet_info["timestamp"] = json_content["timestamp"]
            
            payload = {"alarm_type":"p2pbroadcast","packet":packet_info}

            return True,json.dumps(payload)
        return False,""

    def vnode_status_rule(self,content:str):
        json_content = json.loads(content)
        packet_info = {}
        
        packet_info["timestamp"] = int(int(time.time())/60)*60
        # packet_info["env"] = databasename
        # packet_info["public_ip"] = gl.get_ip()
        packet_info["rec"] = json_content["rec"]
        packet_info["zec"] = json_content["zec"]
        packet_info["auditor"] = json_content["auditor"]
        packet_info["validator"] = json_content["validator"]
        packet_info["archive"] = json_content["archive"]
        packet_info["edge"] = json_content["edge"]
        packet_info["fullnode"] = json_content["fullnode"] if "fullnode" in json_content else 0
        payload = {"alarm_type":"vnode_status","packet":packet_info}

        return True,json.dumps(payload)

    def sync_interval_rule(self,content:str):
        json_content = json.loads(content)
        sync_mod = json_content["mode"]
        table_address = json_content["table_address"]
        if sync_mod != "full" or sync_mod != "fast":
            return False, {}
        if not sync_mod or not table_address:
            return False, {}
        '''
        {
            "mode": "full",
            "table_address": "Ta00013T7BKn5pP8Zi3K5z2Z5BQuSXTf5u37Se79x@0",
            "self_min": 0,
            "self_max": 16,
            "peer_min": 0,
            "peer_max": 16
        }
        '''
        if table_address not in self.xsync_cache[sync_mod]:
            self.xsync_cache[sync_mod][table_address] = {
                "send_timestamp" : int(int(time.time())/self.xsync_interval)*self.xsync_interval,
                "self_min":0,
                "self_max":0,
                "peer_min":0,
                "peer_max":0,
            }

        self.xsync_cache[sync_mod][table_address]["self_min"] = json_content["self_min"]
        self.xsync_cache[sync_mod][table_address]["self_max"] = json_content["self_max"]
        self.xsync_cache[sync_mod][table_address]["peer_min"] = json_content["peer_min"]
        self.xsync_cache[sync_mod][table_address]["peer_max"] = json_content["peer_max"]

        if int(time.time()) - self.xsync_cache[sync_mod][table_address]["send_timestamp"] < self.xsync_interval : 
            # print(int(time.time()), sync_mod, table_address, self.xsync_cache[sync_mod][table_address])
            return False,""
        else:
            packet_info = {}
            # packet_info["env"] = databasename
            # packet_info["public_ip"] = gl.get_ip()
            packet_info["sync_mod"] = sync_mod
            packet_info["table_address"] = table_address
            packet_info["send_timestamp"] = self.xsync_cache[sync_mod][table_address]["send_timestamp"]
            packet_info["self_min"] = self.xsync_cache[sync_mod][table_address]["self_min"]
            packet_info["self_max"] = self.xsync_cache[sync_mod][table_address]["self_max"]
            packet_info["peer_min"] = self.xsync_cache[sync_mod][table_address]["peer_min"]
            packet_info["peer_max"] = self.xsync_cache[sync_mod][table_address]["peer_max"]

            payload = {"alarm_type":"xsync_interval","packet":packet_info}
            self.xsync_cache[sync_mod][table_address]["send_timestamp"] = int(int(time.time())/self.xsync_interval)*self.xsync_interval
            return True,json.dumps(payload)

    def txpool_state_rule(self,content:str):
        '''
        "content": {
            "table_num": 0,
            "unconfirm": 0,
            "received_recv": 0,
            "received_confirm": 0,
            "pulled_recv": 0,
            "pulled_confirm": 0
        }
        '''
        json_content = json.loads(content)
        json_content["send_timestamp"] = int(int(time.time())/self.txpool_interval)*self.txpool_interval
        payload = {"alarm_type":"txpool_state","packet":json_content}
        return True,json.dumps(payload)

    def txpool_receipt_delay_rule(self,content:str):
        '''
        "content": {
            "1clk": 0,
            "2clk": 0,
            "3clk": 0,
            "4clk": 0,
            "5clk": 0,
            "6clk": 0,
            "7to12clk": 0,
            "13to30clk": 0,
            "ex30clk": 0
        }
        '''
        json_content = json.loads(content)
        json_content["send_timestamp"] = int(int(time.time())/self.txpool_interval)*self.txpool_interval
        payload = {"alarm_type":"txpool_receipt","packet":json_content}
        return True,json.dumps(payload)

    def txpool_cache_rule(self,content:str):
        '''
        "content": {
            "send_cur": 0,
            "recv_cur": 0,
            "confirm_cur": 0,
            "unconfirm_cur": 0,
            "push_send_fail": 0,
            "push_receipt_fail": 0,
            "duplicate": 0,
            "repeat": 0
        }
        '''
        json_content = json.loads(content)
        json_content["send_timestamp"] = int(int(time.time())/self.txpool_interval)*self.txpool_interval
        payload = {"alarm_type":"txpool_cache","packet":json_content}
        return True,json.dumps(payload)
    
    def relayer_gas_rule(self,content:str):
        '''
        {
            "category": "TOP-relayer",
            "tag": "gas",
            "type": "realtime",
            "content": {
                "count": 58,
                "value": 8000,
                "detail": "0xadaa9182fd481c6ed4c4b5cc91881067a36af1c357613f0b48bd0f94e495926c"
            }
        }
        '''
        json_content = json.loads(content)
        json_content["send_timestamp"] = int(time.time())
        # packet_info = {}
        # packet_info["count"] = json_content["count"]
        # packet_info["amount"] = json_content["amount"]
        # packet_info["detail"] = json_content["detail"]
        # packet_info["send_timestamp"] = int(time.time())
        payload = {"alarm_type":"relayer_gas","packet":json_content}
        return True,json.dumps(payload)

    def default_metrics_rule(self, content: str):
        # slog.info("default")
        # gl.get_value()
        # print(content)

        # return False,{}

        return True, {}
