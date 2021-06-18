import datetime
import logging
import time

import yaml
from flask import Flask, render_template, request

from util.stats import GPUStats
from util.templating import get_styles


logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
app = Flask(__name__)


@app.route('/')
@app.route('/index')
@app.route('/gpus')
def index():
    logging.info(f"Petition from {request.environ.get('HTTP_X_FORWARDED_FOR')}")
    # Fetch latest stats
    gpus, procs = gpustats.parallel_fetch_stats()
    # Get template bars
    styles = get_styles(gpus, procs)
    # Get gpu tables
    gpu_tables = {h: df.to_html(index=False, classes='table', border=0)
                  for h, df in gpustats.gpu_summaries().items()}
    # User summary table
    user_table = gpustats.user_summary().to_html(index=False, classes='table', border=0)

    # Compute state and last heard
    now = time.time()
    times = {h: str(datetime.timedelta(seconds=int(now-gpustats.last_contact[h])))
             for h in gpustats.hosts}
    # times = {h : datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
              # for h, t in gpustats.last_contact.items()}
    try:
        refresh = int(request.args['refresh'])
    except:
        refresh = 0

    return render_template('index.j2',
                           gpus=gpus,
                           procs=procs,
                           styles=styles,
                           gpu_tables=gpu_tables,
                           user_table=user_table,
                           state=gpustats.state,
                           times=times,
                           refresh=refresh)


if __name__ == '__main__':
    with open('config.yml', 'r') as f:
        config = yaml.safe_load(f)

    gpustats = GPUStats(config['hosts'],
                        config['rpc_port'],
                        config['rpc_timeout'])

    app.run(host="localhost",
            port=config['web_port'])
