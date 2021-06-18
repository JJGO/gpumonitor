def get_styles(gpus, procs):

    styles = {}
    for host in gpus:
        styles[host] = []

        for i, gpu in enumerate(gpus[host]):

            util = gpu['utilization']
            style = {}

            if util <= 10:
                style['util_color'] = "bg-success"
            elif util <= 50:
                style['util_color'] = "bg-warning"
            else:
                style['util_color'] = "bg-danger"

            mem_percent = int(gpu['memory_used'] / gpu['memory_total'] * 100)

            if mem_percent <= 10:
                style['mem_color'] = "bg-success"
            elif mem_percent <= 75:
                style['mem_color'] = "bg-warning"
            else:
                style['mem_color'] = "bg-danger"

            styles[host].append(style)

    return styles
