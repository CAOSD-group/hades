import os
from pathlib import Path

# Datos a tener en cuenta
# ------ Comando osm ns-create ------
# --> ns_name: Creo que el nombre de la KNF en si?
# --> nsd_name: Nombre del paquete NS con la KNF
# --> vim_account: Nombre o ID de la VIM donde se desplegará la KNF
# ------ Archivo config ------
# --> k8s-namespace: Namespace donde se incluiran despliegues y servicios
# --> member-vnf-index: Debe apuntar al ns_name
# --> kdu_name: Nombre del despliegue de K8S?
# --> replicaCount: Numero de replicas del pod
# --> service -> nodePort: Numero del puerto en el que se desplegara (Ver si se pueden varios)


class YamlCreator:
  def __init__(self):
    self.deploy_specs = {'kdu_name': 'camera_deploy', 'k8s_namespace': 'daemon', 'node': 'aldres',
     'image': 'aldresdev/example:v3', 'vnf_index': 'openldap',
     'resources': {'request': '64,300', 'limits': '128,500'},
     'env': {'HOST': 'http://192.168.1.21:', 'PORT': '30008'},
     'volumes': 'camera'}
    self.service_ports = [30008, 30009]


  def createConfig(self, specs, ports):
    print('Creando Yaml de configuracion...')
    template = self.getConfigTemplate()
    kdu_name = specs['kdu_name']
    k8s_namespace = specs['k8s_namespace']
    vnf_index = specs['vnf_index']
    name = k8s_namespace+'-'+kdu_name

    image = specs['image']
    image_repository = image.split(':')[0]
    image_tag = image.split(':')[1]

    service_str = self.getServiceString(ports)

    node_str = self.getNodeString(specs['node']) if specs.get('node') else ""
    sched_str = self.getSchedulerString(specs['scheduler']) if specs.get('scheduler') else ""
    res_str = self.getResourceString(specs['resources']) if specs.get('resources') else ""
    env_str = self.getEnvironmentString(specs['env']) if specs.get('env') else ""
    spec_str = self.getVolumeString(specs['volumes']) if specs.get('volumes') else ""

    config_yaml = template.format(k8s_namespace=k8s_namespace, vnf_index=vnf_index, kdu_name=kdu_name, name=name, node=node_str,
      repository=image_repository, tag=image_tag, sched=sched_str, service=service_str, resources=res_str, env=env_str, spec=spec_str)
    #print(specific_yaml)
    origin = os.getcwd()
    # origin = origin[:-12] # Eliminar la ruta sobrante al ejecutar en local
    directory_path = origin + '/api/deployments/' + k8s_namespace
    Path(directory_path).mkdir(parents=True, exist_ok=True)
    file_path = directory_path + '/' + kdu_name + '.yaml'
    yaml_file = open(file_path,"w")
    yaml_file.write(config_yaml)
    yaml_file.close()
    init_path = directory_path + '/' + '__init__.py'
    init_file = open(init_path, "w")
    init_file.write('')
    init_file.close()
    return file_path

  def getConfigTemplate(self):
    template = """k8s-namespace: {k8s_namespace}
additionalParamsForVnf:
- member-vnf-index: {vnf_index}
  additionalParamsForKdu:
  - kdu_name: {kdu_name}
    additionalParams:
      replicaCount: 1
      name: {name}
      {node}
      {sched}
      image:
        repository: {repository}
        pullPolicy: IfNotPresent
        tag: "{tag}"
      {service}
      autoscaling:
        enabled: false
      {resources}
      {env}
      {spec}"""
    return template
  
  def getNodeString(self, node):
    template = """nodeName: {node}"""
    node_str = template.format(node=node)
    return node_str
  
  def getSchedulerString(self, sched):
    template = """scheduler: {sched}"""
    sched_str = template.format(sched=sched)
    return sched_str

  def getServiceString(self, ports):
    service_str = ''
    if len(ports) == 0:
      service_str = ''
    elif len(ports) == 1:
      template = """service:
        type: NodePort
        port: 80
        nodePort: {port}"""
      service_str = template.format(port=ports[0])
    else:
      template = """service:
        type: NodePort
        port: 80
        port2: 81
        nodePort: {port}
        nodePort: {port2}"""
      service_str = template.format(port=ports[0], port2=ports[1])
    return service_str

  def getResourceString(self, resources):
    mem_request = resources['request'].split(',')[0]
    cpu_request = resources['request'].split(',')[1]
    mem_limit = resources['limits'].split(',')[0]
    cpu_limit = resources['limits'].split(',')[1]
    template = """resources:
        requests:
          memory: "{mr}Mi"
          cpu: "{cpur}m"
        limits:
          memory: "{ml}Mi"
          cpu: "{cpul}m" """
    resource_str = template.format(mr=mem_request, cpur=cpu_request, ml=mem_limit, cpul=cpu_limit)
    return resource_str

  def getEnvironmentString(self, env):
    template = """env:\n"""

    for key in env.keys():
      variable_template = """\t\t\t\t{key}: "{value}"\n"""
      variable_str = variable_template.format(key=key, value=env[key])
      template += variable_str
    env_str = template.format()
    return env_str

  def getVolumeString(self, volumes):
    volumes_str = ''
    if volumes == 'camera':
      template = """spec:
        camera: true"""
      volumes_str = template.format()
    return volumes_str

if __name__ == '__main__':
  yaml_creator = YamlCreator()
  yaml_creator.createConfig(yaml_creator.deploy_specs, yaml_creator.service_ports)