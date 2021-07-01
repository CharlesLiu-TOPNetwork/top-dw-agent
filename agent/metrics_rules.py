import agent.global_var as gl
import json
import time
import random
import copy
import hashlib
from common.slogging import slog


class CallBackHub():
    def __init__(self):
        self.alarm_type_queue_num = 4
        self.rate_level = 3
        self.rate_num = (2**self.rate_level - 1) << 2

        self.msg_recv_cache = {}
        for num in range(self.alarm_type_queue_num):
            self.msg_recv_cache[num] = {}

        self.msg_recv_last_send_timestamp = {
            0: time.time() * 1000,
            1: time.time() * 1000,
            2: time.time() * 1000,
            3: time.time() * 1000,
        }

        self.msg_send_cache = {}
        for num in range(self.alarm_type_queue_num):
            self.msg_send_cache[num] = {}
        self.msg_send_last_send_timestamp = {
            0: time.time() * 1000,
            1: time.time() * 1000,
            2: time.time() * 1000,
            3: time.time() * 1000,
        }

    def p2pbroadcast_message_send_rule(self, content: str):
        '''
        "category": "p2pnormal",
        "tag": "wroutersend_info",
        "type": "real_time",
        "content": {
            "src_node_id": "f60000ff020003ff.0380000000000000",
            "dst_node_id": "f60000ff020003ff.0380000000000000",
            "hop_num": 0,
            "msg_hash": 1543720011,
            "msg_size": 553,
            "is_root": 0,
            "is_broadcast": 1,
            "timestamp": 1623838240265
        }
        '''
        json_content = json.loads(content)
        m_hash = json_content["msg_hash"]

        if(m_hash & self.rate_num) == self.rate_num:
            # do record
            # uniq_key = '{0}_{1}'.format(header_hash,msg_size)
            uniq_key = '{0}_'.format(m_hash)
            uniq_hash = int(hashlib.sha256(
                uniq_key.encode('utf-8')).hexdigest(), 16) % (10**19)
            index = uniq_hash % self.alarm_type_queue_num
            if uniq_hash not in self.msg_send_cache[index]:
                msg_cache = {}
                msg_cache['src_id'] = json_content["src_node_id"]
                msg_cache['dst_id'] = json_content["dst_node_id"]
                msg_cache['msg_size'] = json_content["msg_size"]
                msg_cache['msg_hash'] = m_hash
                msg_cache['is_root'] = json_content["is_root"]
                msg_cache['is_broadcast'] = json_content["is_broadcast"]
                msg_cache['timestamp'] = json_content["timestamp"]
                self.msg_send_cache[index][uniq_hash] = msg_cache
            else:
                slog("repeated send?")

        time_ = int(time.time()) * 1000

        # send packet of all every 10s or queue full 3000
        for queue_num in range(self.alarm_type_queue_num):
            # slog.info("in? queue_num: {0} {1}".format(queue_num,time_-self.msg_send_last_send_timestamp[queue_num]))
            # if len(self.msg_send_cache[queue_num]):
            if len(self.msg_send_cache[queue_num]) > 3000 or (time_-self.msg_send_last_send_timestamp[queue_num] >= 10 * 1000 and len(self.msg_send_cache[queue_num])):
                # slog.info("in2? queue_num: {0} {1}".format(queue_num,time_-self.msg_send_last_send_timestamp[queue_num]))
                packet_info = {}
                packet_info["msg_type"] = "send"
                packet_info["public_ip"] = gl.get_ip()
                packet_info["content"] = copy.deepcopy(
                    self.msg_send_cache[queue_num])
                self.msg_send_cache[queue_num] = {}
                self.msg_send_last_send_timestamp[queue_num] = time_+(
                    int(random.random()*3000))
                payload = {"alarm_type": "p2p_gossip", "packet": packet_info}
                # print(payload)
                # slog.info("payload {0}".format(payload))
                return True, payload

        return False, {}

    def p2pbroadcast_message_recv_rule(self, content: str):
        # vhostrecv_info
        '''
            "category": "p2pnormal",
            "tag": "vhostrecv_info",
            "type": "real_time",
            "content": {
                "src_node_id": "f60000ff020003ff.0380000000000000",
                "dst_node_id": "e30fffff1dc93c29.bfe00aa671058fe0",
                "hop_num": 3,
                "msg_hash": 1835013513,
                "msg_size": 501,
                "is_root": 1,
                "is_broadcast": 1,
                "is_pulled": 0,
                "packet_size": 773,
                "timestamp": 1623838230771
            }
        '''
        # wrouterrecv_info
        '''
            "category": "p2pnormal",
            "tag": "wrouterrecv_info",
            "type": "real_time",
            "content": {
                "src_node_id": "f60000ff020003ff.0380000000000000",
                "dst_node_id": "3ecfffff96ea335a.6431c5187ffb89b4",
                "hop_num": 3,
                "msg_hash": 1835013513,
                "msg_size": 501,
                "is_root": 1,
                "is_broadcast": 1,
                "packet_size": 773,
                "timestamp": 1623838230771
            }
        '''
        json_content = json.loads(content)
        # if "msg_hash" in json_content.keys():
        m_hash = json_content["msg_hash"]
        m_size = json_content["msg_size"]

        # else:
        #     m_hash = json_content["gossip_header_hash"]
        #     m_size = json_content["gossip_block_size"]

        # slog.info("get recv message info {0} rate {1}".format(header_hash,self.rate_num))
        if(m_hash & self.rate_num) == self.rate_num:
            # slog.info("get recv message info inside {0}".format(header_hash))
            msg_size = m_size
            uniq_key = '{0}_'.format(m_hash)
            uniq_hash = int(hashlib.sha256(
                uniq_key.encode('utf-8')).hexdigest(), 16) % (10**19)
            index = uniq_hash % self.alarm_type_queue_num

            if uniq_hash not in self.msg_recv_cache[index]:
                msg_cache = {}
                msg_cache['vhost_recv'] = 0
                msg_cache['recv_cnt'] = 0
                msg_cache['recv_hash_cnt'] = 0
                msg_cache['is_pulled'] = 0
                msg_cache['packet_size'] = json_content["packet_size"]
                self.msg_recv_cache[index][uniq_hash] = msg_cache
            else:
                msg_cache = self.msg_recv_cache[index][uniq_hash]
                msg_cache['packet_size'] += json_content["packet_size"]

            if "is_pulled" in json_content:
                # vhost_recv_info
                msg_cache['vhost_recv'] += 1
                msg_cache['src_id'] = json_content["src_node_id"]
                msg_cache['dst_id'] = json_content["dst_node_id"]
                msg_cache['timestamp'] = json_content["timestamp"]
                msg_cache['is_pulled'] = json_content["is_pulled"]
                msg_cache['hop_num'] = json_content["hop_num"]
            else:
                # if msg_size != 0:
                msg_cache['recv_cnt'] += 1
                # else:
                #     msg_cache["recv_hash_cnt"] +=1

            time_ = int(time.time())*1000

            for queue_num in range(self.alarm_type_queue_num):
                # slog.info("in? queue_num: {0} {1}".format(queue_num,time_-self.msg_send_last_send_timestamp[queue_num]))
                # if len(self.msg_recv_cache[queue_num]):
                if len(self.msg_recv_cache[queue_num]) > 3000 or (time_-self.msg_recv_last_send_timestamp[queue_num] >= 10*1000 and len(self.msg_recv_cache[queue_num])):
                    # slog.info("in2? queue_num: {0} {1}".format(queue_num,time_-self.msg_send_last_send_timestamp[queue_num]))
                    packet_info = {}
                    packet_info["msg_type"] = "recv"
                    packet_info["public_ip"] = gl.get_ip()
                    packet_info["content"] = copy.deepcopy(
                        self.msg_recv_cache[queue_num])
                    self.msg_recv_cache[queue_num] = {}
                    self.msg_recv_last_send_timestamp[queue_num] = time_+(
                        int(random.random()*3000))
                    payload = {"alarm_type": "p2p_gossip",
                               "packet": packet_info}
                    # print(payload)
                    slog.info("payload {0}".format(payload))
                    return True, payload

        return False, {}

    def vnode_status_rule(self,content:str,databasename:str):
        json_content = json.loads(content)
        packet_info = {}
        
        packet_info["timestamp"] = int(int(time.time())/60)*60
        packet_info["env"] = databasename
        packet_info["public_ip"] = gl.get_ip()
        packet_info["rec"] = json_content["rec"]
        packet_info["zec"] = json_content["zec"]
        packet_info["auditor"] = json_content["auditor"]
        packet_info["validator"] = json_content["validator"]
        packet_info["archive"] = json_content["archive"]
        packet_info["edge"] = json_content["edge"]
        payload = {"alarm_type":"vnode_status","packet":packet_info}

        return True,payload

    def default_metrics_rule(self, content: str):
        # slog.info("default")
        # gl.get_value()
        # print(content)

        # return False,{}

        return True, {}
