GPU Monitor
===========

Resource monitor for Nvidia GPUs.
Collects data through Nvidia's Python bindings (see [here](https://pypi.org/project/pynvml/)) and makes it more interpreatable by including userids, runtime and total allocated memory.  
Data is aggregated using a web server that also computes aggregate statistics. 
Entirely built on Python using the builtin RPC library for communication between nodes. 


## Configuration

In order for the scripts to run a `config.yml` needs to be created with a structure as shown below. Ports can be changed and the hosts need to all be reachable from the defined web server. Host entries can be either IP or URLs both will work.  

```
# Config for GPU monitor
web_port: 8042
rpc_port: 8043
rpc_timeout: 2
hosts:
  - host1
  - host2
```


## Installation

Since the RPC server needs to be installed in every server an Ansible playbook is provided for ease of installation. 
It will copy the relevant files, create an user and `python3.6` environment to run the scripts and install systemd services for both the RPC servers and the webserver(s). 

To install you first need to create a `hosts` file under `ansible-install` that has this structure replacing the user and server ips where appropriate (urls can also be used instead). 

```
[webserver]
server ansible_host=SERVER_IP ansible_user=USER ansible_remote_tmp=/tmp/.ansible/tmp

[rpcservers]
host1 ansible_host=HOST1_IP ansible_user=USER ansible_remote_tmp=/tmp/.ansible/tmp
host2 ansible_host=HOST2_IP ansible_user=USER ansible_remote_tmp=/tmp/.ansible/tmp
```

Then the software can be installed by executing the following command. Note that sudo permissions are required on all remote machines 

```
ansible-playbook -i ./hosts main.yml --ask-become-pass
```

### Reverse proxy

By default the web server will be listening on the `web_port` defined in the `config.yml`. To use https and port 443 a reverse proxy can be used

#### NGINX

For NGINX the following block will work

```
    location /gpus/ {
        auth_basic off;
        proxy_pass http://localhost:8042/;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $http_host;
        proxy_http_version 1.1;
        proxy_redirect off;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
```

### Caddy

To use caddy include a block like this in the `Caddyfile`

```
location example.com {
    redir /gpus/ /gpus
    reverse_proxy /gpus localhost:8042
}
```
