import requests
import yaml
from django.shortcuts import render
# from api import serializer
from osmclient import client
from osmclient.common.exceptions import ClientException
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.scripts.yaml_creator import YamlCreator

hostname = "192.168.1.21" # OSM machine IP
user = "admin" # OSM user name
password = "admin" # OSM user pass
project = "admin" # OSM project access
kwargs = {}
if user is not None:
    kwargs['user']=user
if password is not None:
    kwargs['password']=password
if project is not None:
   kwargs['project']=project


vim_list = []
k8s_clusters_list = []
#k8s_clusters_metrics = []
k8s_clusters_metrics = {
    "data": [
        {
            "_id": "27a5e889-86c7-4f96-99fa-83764177b758",
            "name": "microk8s-cluster de prueba",
            "description": "My K8S cluster mocky",
            "metrics": [
                {
                    "name": "kubernetes-master",
                    "total_cpu": "8",
                    "cpu_usage": "395m",
                    "cpu_perc": "5",
                    "total_memory": "15964856Ki",
                    "memory_usage": "3980672Ki",
                    "memory_perc": "25",
                    "received_kb": "25kb",
                    "transmit_kb": "49kb",
                    "total_kb": "74kb",
                    "kind": "Worker",
                    "arch": "AMD64",
                    "ip": "https://192.168.130.29:16443"
                }
            ],
            "vim_account": "9926b549-b159-4ad0-8a3a-5b7872551e5d"
        }
    ]
}

deployments = {
    'deployments':
    [
        {
            "name": "Nautic",
            "tasks": [
                {
                    "name": "Visualizer",
                    "ip": "192.168.1.50",
                    "port": 8100
                },
                # {
                #     "name": "Filter Selector",
                #     "ip": "192.168.1.21",
                #     "port": 8092,
                #     "request_port": 8093
                # },
                # {
                #     "name": "Planet Tracker",
                #     "ip": "192.168.1.21",
                #     "port": 8096
                # },
                # {
                #     "name": "Feature Communicator",
                #     "ip": "192.168.1.21",
                #     "port": 8090,
                #     "request_port": 8091
                # },
                # {
                #     "name": "Video Capturer",
                #     "ip": "192.168.1.21",
                #     "port": 0
                # }
            ]
        }
    ]
}


class HelloAPIView(APIView):
    def get(self, request, format=None):
        data = ['data 1', 'data 2', 'data 3']
        return Response({'message': 'Hi example', 'data': data})


class KubeNodes(APIView):
    def get(self, request, format=None):
        return Response({'data': self.getK8sClustersList()})

    def getK8sClustersList(self):
        myclient = client.Client(host=hostname, sol005=True, **kwargs)
        resp = myclient.k8scluster.list()
        return resp


class NSPackages(APIView):
    def get(self, request, format=None):
        return Response({'data': self.getNSPackagesList()})

    def getNSPackagesList(self):
        myclient = client.Client(host=hostname, sol005=True, **kwargs)
        resp = myclient.nsd.list()
        result = []
        for element in resp:
            nsi = {
                '_id': element['_id'],
                'id': element['id'],
                'name': element['name'],
                'vnfd-id': element['vnfd-id'],
                'description': element['description'],
            }
            result.append(nsi)
        return result


class TopClusters(APIView):
    global k8s_clusters_metrics
    def get(self, request, format=None):
        if not k8s_clusters_metrics:
            return Response({'data': self.get_structure()})
        else:
            return Response(k8s_clusters_metrics)
    
    def post(self, request):
        global k8s_clusters_metrics
        print(request.data)
        k8s_clusters_metrics = request.data
        return Response({'message': 'Metrics saved'})
    
    def get_structure(self):
        myclient = client.Client(host=hostname, sol005=True, **kwargs)
        resp = myclient.k8scluster.list()
        result = []
        for element in resp:
            k8scluster = {
                '_id': element['_id'],
                'name': element['credentials']['clusters'][0]['name'],
                'server': element['credentials']['clusters'][0]['cluster']['server'],
                'description': element['description'],
                'vim_account': element['vim_account']
            }
            result.append(k8scluster)
        return result


class KNFInstances(APIView):
    def get(self, request, format=None):
        myclient = client.Client(host=hostname, sol005=True, **kwargs)
        resp = myclient.vnf.list()
        result = []
        for vnf in resp:
            cluster = self.cluster_from_id(vnf['kdur']['k8s-cluster']['id'])
        return Response({'data': resp})

    def cluster_from_id(cluster_id):
        global k8s_clusters_list
        pass


class NSInstances(APIView):
    def get(self, request, format=None):
        myclient = client.Client(host=hostname, sol005=True, **kwargs)
        resp = myclient.ns.list()
        return Response({'data': resp})


class IdList(APIView):
    def get(self, request, format=None):
        result = []
        myclient = client.Client(host=hostname, sol005=True, **kwargs)

        vims = myclient.vim.list()
        for element in vims:
            vim = {
                'name': element['name'],
                '_id': element['_id'],
                'kind': 'vim'
            }
            result.append(vim)

        k8s_clusters = myclient.k8scluster.list()
        for element in k8s_clusters:
            cluster = {
                'name': element['name'],
                '_id': element['_id'],
                'kind': 'k8s-cluster'
            }
            result.append(cluster)

        return Response({'data': result})


class Location(APIView):
    def get(self, request, format=None):
        return Response({'data': deployments})

    def post(self, request):
        self.insertData(request.data)
        response = self.searchTask(request.data)
        return Response({'data': response})
    
    def insertData(self, data):
        deployment = self.getDeploymentIfExists(data['deployment'])
        if deployment:
            self.modifyDeployment(data, deployment)
        else:
            self.insertDeployment(data)

    def searchTask(self, data):
        # data = {'deployment': 'Nauticon', 'name': 'Aruco', 'ip': SERVER_HOST, 'port': SERVER_PORT, 'task_requested': 'Filter Selector'}
        result = False
        deployment = self.getDeploymentIfExists(data['deployment'])
        if deployment:
            result = self.getTaskIfExists(data['task_requested'], deployment)
        return result
    
    def getDeploymentIfExists(self, deployment_name):
        result = False
        if deployments:
            for deployment in deployments['deployments']:
                if deployment_name == deployment['name']:
                    result = deployment
                    break      
        return result

    def insertDeployment(self, data):
        new_deployment = {
            'name': data['deployment'],
            'tasks': [
                {
                    'name': data['name'],
                    'ip': data['ip'],
                    'port': int(data['port'])
                }
            ]
        }
        deployments['deployments'].append(new_deployment)

    def modifyDeployment(self, data, deployment):
        task = self.getTaskIfExists(data['name'], deployment)
        if (task):
            self.modifyTask(data, deployment, task)
        else:
            self.insertTask(data, deployment)

    def getTaskIfExists(self, task_name, deployment):
        result = False
        print(task_name)
        if deployment:
            for task in deployment['tasks']:
                if task_name == task['name']:
                    result = task
                    break
        return result

    def insertTask(self, data, deployment):
        # data_planet = {'deployment': DEPLOYMENT, 'name': TASK, 'ip': SERVER_HOST, 'port': FRAME_PORT, 'request_port': REQUEST_PORT, 'task_requested': PL_NAME}
        new_task = self.createNewTask(data)
        deployment_index = self.getDeploymentIndex(deployment['name'])
        deployments['deployments'][deployment_index]['tasks'].append(new_task)

    def createNewTask(self, data):
        task = {}
        if(data.get('request_port')):
            task = {
                'name': data['name'],
                'ip': data['ip'],
                'port': int(data['port']),
                'request_port': int(data['request_port'])
            }
        else:
            task = {
                'name': data['name'],
                'ip': data['ip'],
                'port': int(data['port'])
            }
        return task

    def modifyTask(self, data, deployment, task):
        deployment_index = self.getDeploymentIndex(deployment['name'])
        task_index = self.getTaskIndex(deployment_index, task['name'])
        deployments['deployments'][deployment_index]['tasks'][task_index]['ip'] = data['ip']
        deployments['deployments'][deployment_index]['tasks'][task_index]['port'] = int(data['port'])
        if(data.get('request_port')):
            deployments['deployments'][deployment_index]['tasks'][task_index]['request_port'] = int(data['request_port'])

    def getDeploymentIndex(self, deployment_selected):
        count = 0
        for deployment in deployments['deployments']:
            if deployment['name'] == deployment_selected:
                break
            else:
                count+=1
        return count

    def getTaskIndex(self, deployment_index, task_selected):
        count = 0
        for task in deployments['deployments'][deployment_index]['tasks']:
            if task['name'] == task_selected:
                break
            else:
                count+=1
        return count


class Manager(APIView):
    def post(self, request):
        print('La data')
        print(request.data)
        response = self.manageRequest(request.data)
        # response = 'Done'
        return Response({'data': response})
    
    def manageRequest(self, data):
        print('Antes de encontrar la tarea')
        # data = {'deployment': 'Nautic', 'task': 'Planet Tracker', 'action': 'open/stop'}
        task = self.getTaskIfExists(data)
        if task:
            print('Tenemos la tarea')
            print(task)
            response = self.sendActionToLocation(data, task)
            return response
        else:
            response = 'Location not found'
            return response 

    def getTaskIfExists(self, data):
        result = False
        deployment = self.getDeploymentIfExists(data['deployment'])
        if deployment:
            for task in deployment['tasks']:
                if task['name'] == 'Feature Communicator':
                    result = task
                    break
        return result

    def getDeploymentIfExists(self, deployment_name):
        result = False
        if deployments:
            for deployment in deployments['deployments']:
                if deployment_name == deployment['name']:
                    result = deployment
                    break
        return result

    def sendActionToLocation(self, data, task):
        result = 'Done'
        data_request = {'name': data['task']}
        requests.post('http://' + task['ip'] + ':' + str(task['request_port']) + '/' + data['action'] + '/', json=data_request)
        return result


class Deployment(APIView):
    def post(self, request):
        data = request.data
        response = 'Initialising deployment...'
        if not k8s_clusters_metrics:
            response = 'No metrics of the system, cannot initialise deployments.'
        else:
            busy_ports = self.getBusyPorts()
            # tasks_specs es una lista de objetos JSON, cada uno con dos parametros: deploy_specs y service_ports
            tasks_specs = self.calculateOptimalDeployment(data, k8s_clusters_metrics)
            yaml_creator = YamlCreator()
            for spec in tasks_specs:
                yaml_creator.createConfig(spec['deploy_specs'], spec['service_ports'])
            response = busy_ports
        return Response({'data': response})

    def getBusyPorts(self):
        busy_ports = []
        if deployments:
            for deployment in deployments['deployments']:
                ports = self.getBusyPortsFromDeployment(deployment)
                if ports:
                    for port in ports:
                        busy_ports.append(port)
        return busy_ports

    def getBusyPortsFromDeployment(self, deployment):
        ports = []
        for task in deployment['tasks']:
            if task['port'] != 0:
                ports.append(task['port'])
            if task.get('request_port'):
                ports.append(task['request_port'])
        return ports

    def calculateOptimalDeployment(self, data, metrics):
        # Angel Algorithm
        specs_list = [
            {
                'deploy_specs': {
                    'kdu_name': 'video_capturer', 'k8s_namespace': 'nautic', 'node': 'kubernetes-master',
                    'image': 'aldresdev/example:v3', 'vnf_index': 'openldap',
                    'resources': {'request': '64,300', 'limits': '128,500'},
                    'env': {
                        'CENTRAL_HOST': '127.0.0.1', 'CENTRAL_PORT': '8000', 'DEPLOYMENT': 'nautic', 'SERVER_HOST': '150.214.108.92'
                    },
                    'volumes': 'camera'
                },
                'service_ports': []
            },
            {
                'deploy_specs': {
                    'kdu_name': 'feature_communicator', 'k8s_namespace': 'nautic', 'node': 'kubernetes-master',
                    'image': 'aldresdev/example:v3', 'vnf_index': 'openldap',
                    'resources': {'request': '64,300', 'limits': '128,500'},
                    'env': {
                        'CENTRAL_HOST': '127.0.0.1', 'CENTRAL_PORT': '8000', 'DEPLOYMENT': 'nautic', 'SERVER_HOST': '150.214.108.92',
                        'FRAME_PORT': 8090, 'REQUEST_PORT': 8091, 'PLANET_FEATURE': 'included'
                    }
                },
                'service_ports': [8090, 8091]
            },
            {
                'deploy_specs': {
                    'kdu_name': 'planet_tracker', 'k8s_namespace': 'nautic', 'node': 'kubernetes-master',
                    'image': 'aldresdev/example:v3', 'vnf_index': 'openldap',
                    'resources': {'request': '64,300', 'limits': '128,500'},
                    'env': {
                        'CENTRAL_HOST': '127.0.0.1', 'CENTRAL_PORT': '8000', 'DEPLOYMENT': 'nautic', 'SERVER_HOST': '150.214.108.92',
                        'FRAME_PORT': 8090, 'CAMERA_WIDTH': 320, 'CAMERA_HEIGHT': 240
                    }
                },
                'service_ports': [8096]
            },
            {
                'deploy_specs': {
                    'kdu_name': 'filter_selector', 'k8s_namespace': 'nautic', 'node': 'kubernetes-master',
                    'image': 'aldresdev/example:v3', 'vnf_index': 'openldap',
                    'resources': {'request': '64,300', 'limits': '128,500'},
                    'env': {
                        'CENTRAL_HOST': '127.0.0.1', 'CENTRAL_PORT': '8000', 'DEPLOYMENT': 'nautic', 'SERVER_HOST': '150.214.108.92',
                        'FRAME_PORT': 8092, 'REQUEST_PORT': 8093
                    }
                },
                'service_ports': [8092, 8093]
            },
            {
                'deploy_specs': {
                    'kdu_name': 'visualizer', 'k8s_namespace': 'nautic', 'node': 'kubernetes-master',
                    'image': 'aldresdev/example:v3', 'vnf_index': 'openldap',
                    'resources': {'request': '64,300', 'limits': '128,500'},
                    'env': {
                        'CENTRAL_HOST': '127.0.0.1', 'CENTRAL_PORT': '8000', 'DEPLOYMENT': 'nautic', 'SERVER_HOST': '150.214.108.92',
                        'FRAME_PORT': 8100
                    }
                },
                'service_ports': [8092, 8093]
            }
        ]

        return specs_list

