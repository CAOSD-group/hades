import requests
import os
import time
import logging

logging.basicConfig(level=logging.DEBUG)

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning)

HOST_CLIENT = '192.168.1.21'
PORT_CLIENT = int('8000')
PORT_PROMETHEUS = int('30000')


def initialise_data():
    global HOST_CLIENT, PORT_CLIENT
    if os.environ.get('HOST_CLIENT'):
        HOST_CLIENT = os.environ.get('HOST_CLIENT')
    if os.environ.get('PORT_CLIENT'):
        PORT_CLIENT = int(os.environ.get('PORT_CLIENT'))
    if os.environ.get('PORT_PROMETHEUS'):
        PORT_PROMETHEUS = int(os.environ.get('PORT_PROMETHEUS'))


def get_data():
    while True:
        try:
            data = []
            clusters_info = do_clusters_request()
            for cluster in clusters_info:
                cluster_metrics = get_metrics_data(cluster)
                data.append(cluster_metrics)
            return_metrics_data(data)
            time.sleep(10)
        except:
            logging.info('Connection failed, retrying in 5 seconds...')
            time.sleep(5)


def do_clusters_request():
    route = 'http://' + HOST_CLIENT + ':' + str(PORT_CLIENT) + '/api/nodes/'
    request = requests.get(route)
    return request.json()['data']

def get_metrics_data(element):
    metrics = []
    id = element['_id']
    cluster_name = element['name']
    cluster_description = element['description']
    vim_account = element['vim_account']
    location = element['credentials']['clusters'][0]['cluster']['server']
    prometheus_location = reformat_location(location)
    token = 'Bearer ' + element['credentials']['users'][0]['user']['token']

    # ----- CPU and RAM requests ----- #
    nodes_resources_request = requests.get(location + '/apis/metrics.k8s.io/v1beta1/nodes', headers={'Authorization': token}, verify=False)
    nodes_info_request = requests.get(location + '/api/v1/nodes', headers={'Authorization': token}, verify=False)

    nodes_resources = nodes_resources_request.json()
    nodes_info = nodes_info_request.json()
    
    for node in nodes_info['items']:
        name = node['metadata']['name']
        stat = get_stat(name, nodes_resources)
        cpu_perc = calculateCPUPercentage(node['status']['allocatable']['cpu'], stat['usage']['cpu'])
        mem_perc = calculateMemPercentage(node['status']['allocatable']['memory'], stat['usage']['memory'])

        received_kb = do_receive_request(prometheus_location, name)
        transmit_kb = do_transmit_request(prometheus_location, name)
        total_kb = received_kb+transmit_kb

        labels = node['metadata']['labels']
        arch = labels['beta.kubernetes.io/arch']
        kind = get_kind(labels)

        element = {
            'name': name,
            'total_cpu': node['status']['allocatable']['cpu'],
            'cpu_usage': stat['usage']['cpu'],
            'cpu_perc': cpu_perc,
            'total_memory': node['status']['allocatable']['memory'],
            'memory_usage': stat['usage']['memory'],
            'memory_perc': mem_perc,
            'received_kb': str(received_kb)+'kb',
            'transmit_kb': str(transmit_kb)+'kb',
            'total_kb': str(total_kb)+'kb',
            'kind': kind,
            'arch': arch.upper(),
            'ip': location,
        }
        metrics.append(element)

    cluster_metrics = {
        '_id': id,
        'name': cluster_name,
        'description': cluster_description,
        'metrics': metrics,
        'vim_account': vim_account,
        
    }

    return cluster_metrics

def return_metrics_data(metrics_data):
    logging.info(metrics_data)
    route = 'http://' + HOST_CLIENT + ':' + str(PORT_CLIENT) + '/api/top-clusters/'
    request = requests.post(route, json = {'data': metrics_data})

def get_stat(name, resources):
    stat = {
        'usage': {
            'cpu': '',
            'memory': ''
        }
    }

    for stats in resources['items']:
        if name == stats['metadata']['name']:
            stat = {
                'usage': {
                    'cpu': stats['usage']['cpu'],
                    'memory': stats['usage']['memory']
                }
            }
    return stat

def calculateCPUPercentage(set_total, str_usage):
    if str_usage == '':
            return 0

    str_total = next(iter(set_total))

    total = int(str_total) * 1000
    usage = int(str_usage[:-1])
    percentage = round(usage * 100 / total)

    return str(percentage)

def calculateMemPercentage(str_total, str_usage):
    if str_usage == '':
            return 0

    total = int(str_total[:-2])
    usage = int(str_usage[:-2])
    percentage = round(usage * 100 / total)

    return str(percentage)

def get_kind(labels):
    value = 'Master'
    try:
        labels['node-role.kubernetes.io/master']
    except KeyError:
        value = 'Worker'
    return value

def reformat_location(location):
    http_location = location.replace('https', 'http')
    prometheus_chain = http_location.split(':')
    prometheus_location = prometheus_chain[0] + ':' + prometheus_chain[1] + ':' + str(PORT_PROMETHEUS)
    return prometheus_location

def do_receive_request(location, name):
    #route = location + '/api/v1/query?query=sum(rate(node_network_receive_bytes_total[30s]))'
    route = location + '/api/v1/query?query=sum(rate(node_network_receive_bytes_total{instance="' + name + '"}[30s]))'
    request = requests.get(route)
    receive_bytes = float(request.json()['data']['result'][0]['value'][1])
    return round(receive_bytes/1024)

def do_transmit_request(location, name):
    #route = location + '/api/v1/query?query=sum(rate(node_network_transmit_bytes_total[30s]))'
    route = location + '/api/v1/query?query=sum(rate(node_network_transmit_bytes_total{instance="' + name + '"}[30s]))'
    request = requests.get(route)
    transmit_bytes = float(request.json()['data']['result'][0]['value'][1])
    return round(transmit_bytes/1024)

if __name__ == '__main__':
    initialise_data()
    get_data()





# http://192.168.1.21:16443/apis/batch/v1/namespaces/default/jobs
# http://192.168.1.21:16443/api/v1/nodes
# r = requests.post('http://' + HOST_CLIENT + ':' + str(PORT_CLIENT) + '/connection', json=data)
