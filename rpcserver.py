import datetime
import logging
import json
import time
import socket
from xmlrpc.server import SimpleXMLRPCServer

import psutil
import yaml
from pynvml.smi import nvidia_smi

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

pid_cache = {}

nv = nvidia_smi()
host = socket.gethostname()
count = nv.DeviceQuery()['count']


def get_user_time(pid):
    if pid not in pid_cache:
        process = psutil.Process(pid)
        userid = process.username()
        create_time = process.create_time()
        pid_cache[pid] = (userid, create_time)
    return pid_cache[pid]


def gpu_stats():
    query = nv.DeviceQuery()
    gpus = []
    procs = []
    now = time.time()

    for i in range(count):
        gpu = query['gpu'][i]
        gpus.append({
            "memory_total": gpu['fb_memory_usage']['total'],
            "memory_used": gpu['fb_memory_usage']['used'],
            "memory_free": gpu['fb_memory_usage']['free'],
            "utilization": gpu['utilization']['gpu_util'],
            "temperature": gpu['temperature']['gpu_temp'],
            "model": gpu['product_name']
        })
        ps = gpu['processes'] if gpu['processes'] is not None else []

        for p in ps:
            uid, create_time = get_user_time(p['pid'])
            p['userid'] = uid
            p['time'] = str(datetime.timedelta(seconds=int(now-create_time)))
        procs.append(ps)

    logging.info('Querying devices')

    return json.dumps({'gpus': gpus, 'procs': procs})


if __name__ == '__main__':
    with open('config.yml', 'r') as f:
        config = yaml.safe_load(f)
        port = config['rpc_port']
    server = SimpleXMLRPCServer(("0.0.0.0", port))
    logging.info(f"Listening on port {port}...")
    server.register_function(gpu_stats, "gpu_stats")
    server.serve_forever()
