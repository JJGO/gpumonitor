import http.client
import json
import logging
import socket
import time
import xmlrpc.client

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


class TimeoutTransport(xmlrpc.client.Transport):
    timeout = 2.0

    def set_timeout(self, timeout):
        self.timeout = timeout

    def make_connection(self, host):
        return http.client.HTTPConnection(host, timeout=self.timeout)


def format_memory(MBs):
    if MBs/1024 < 1:
        return f"{MBs} MB"
    return f"{MBs/1024:.2f} GB"


class GPUStats:

    def __init__(self, hosts, port, timeout):
        self.hosts = hosts
        self.port = port
        self.gpus = defaultdict(dict)
        self.procs = defaultdict(dict)
        self.state = {h: "Never" for h in self.hosts}
        self.last_contact = defaultdict(int)
        self.timeout = timeout

    def _fetch_host(self, host):
        logging.info(f"Contacting {host}")
        t = TimeoutTransport()
        t.set_timeout(self.timeout)
        try:
            url = f"http://{host}:{self.port}/"
            with xmlrpc.client.ServerProxy(url, transport=t) as proxy:
                response = json.loads(proxy.gpu_stats())
                self.gpus[host] = response['gpus']
                self.procs[host] = response['procs']
                self.state[host] = 'Up'
                self.last_contact[host] = time.time()
                logging.info(f"Updated {host}")
        except ConnectionRefusedError:
            self.state[host] = 'Down' if self.state[host] != 'Never' else 'Never'
            logging.info(f"Connection Refused for {host}. Last contact {self.last_contact[host]}")
        except socket.timeout:
            self.state[host] = 'Timeout' if self.state[host] != 'Never' else 'Never'
            logging.info(f"Timeout for {host}. Last contact {self.last_contact[host]}")

    def fetch_stats(self):
        for host in self.hosts:
            self._fetch_host(host)
        return self.gpus, self.procs

    def parallel_fetch_stats(self):
        with ThreadPoolExecutor() as executor:
            for host in self.hosts:
                executor.submit(self._fetch_host, host)
            executor.shutdown(wait=True)
        return self.gpus, self.procs

    def gpu_summaries(self):
        dfs = {}
        for host in self.hosts:
            data = []
            for g, procs_gpu in enumerate(self.procs[host]):
                for p in procs_gpu:
                    data.append([g, p['userid'], format_memory(p['used_memory']), p['time'], p['pid']])
            dfs[host] = pd.DataFrame(data=data, columns=('GPU', 'User', 'Memory', 'Time', 'PID'))
        return dfs

    def user_summary(self):
        data = []
        for host in self.hosts:
            for i, procs_gpu in enumerate(self.procs[host]):
                for p in procs_gpu:
                    data.append([p['userid'], f"{host}", f"{i}", p['pid'], p['used_memory'], p['time']])
        df = pd.DataFrame(data=data, columns=['userid', 'host', 'gpu', 'pid', 'memory', 'walltime'])
        summary = []
        for userid, sdf in df.groupby('userid'):
            used_gpus = {}
            for host, gpu in zip(sdf['host'].values, sdf['gpu'].values):
                if host not in used_gpus:
                    used_gpus[host] = set()
                used_gpus[host].add(gpu)
            used_gpus = "  ".join([f"{host}-"+",".join(sorted(gpus)) for host, gpus in used_gpus.items()])
            summary.append([userid,
                            sdf['memory'].sum(),
                            len(sdf),
                            used_gpus
                            ])
        sum_df = pd.DataFrame(summary, columns=['user', 'memory', 'n_procs', 'gpus'])
        sum_df = sum_df.sort_values(by=['memory', 'n_procs'], ascending=False)
        sum_df['memory'] = sum_df['memory'].apply(format_memory)
        return sum_df
