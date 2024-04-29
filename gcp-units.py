import argparse
import json
import subprocess

# Usage python3 ./gcp-units.py --projects <project_id_1> <project_id_2> <project_id_3>

parser = argparse.ArgumentParser(prog="SentinelOne CNS GCP Unit Audit")
parser.add_argument("--projects", help="GCP Project ID(s) separated by space", nargs='+', default=[],required=True)
args = parser.parse_args()

PROJECTS = args.projects

def gcloud_set_project(project_id):
    output = subprocess.check_output(
        f"gcloud config set project {project_id}",
        text=True, shell=True, stderr=subprocess.STDOUT
    )
    print(f"[Info]: {output}")
    if f"WARNING: You do not appear to have access to project [{project_id}] or it does not exist." in output:
        return False
    return True

def gcloud_components_check():
    try:
        output = subprocess.check_output(
            "gcloud --version",
            text=True, shell=True, stderr=subprocess.STDOUT
        )
        installed_components = [x.split(" ")[0] for x in list(filter(lambda x: len(x.strip()) > 0, output.split("\n")))]
        requirements = {
            "alpha": False,
            "bq": False,
            "gsutil": False
        }
        for component in installed_components:
            if requirements.get(component, None) is not None:
                requirements[component] = True
        for component in requirements:
            if not requirements[component]:
                print("[Error] missing component:", component)
                print("[Error] required gcloud components:", "alpha", "bq", "gsutil")
                return False
        return True
    except:
        return False

def gcloud_list_services():
    output = subprocess.check_output(
        "gcloud services list --format json",
        text=True, shell=True, stderr=subprocess.STDOUT
    )
    services = json.loads(output)
    for service in services:
        yield {
            'name': service['config']['name'],
            'enabled': service['state'] == 'ENABLED'
        }

class SentinelOneCNSGCPUnitAudit:
    def __init__(self, project_id):
        self.existing_permissions = {}
        self.project_id = project_id
        self.file_path = f"gcp-{project_id}-units.csv"
        self.total_resource_count = 0

        if not gcloud_set_project(project_id):
            raise Exception("Check gcp project id/permissions")
        print("[Info] successfully set gcloud project id:", project_id)

        if not gcloud_components_check():
            raise Exception("Check installed components")
        print("[Info] found all required cli components")

        for service in gcloud_list_services():
            if service['enabled']:
                self.existing_permissions[service['name']] = True
        print("[Info] fetched all existing permissions on account")

        with open(self.file_path, 'w') as f:
            # Write Header
            f.write("Resource Type, Unit Counted\n")

    def is_api_enabled(self, apis):
        for api in apis:
            if not self.existing_permissions.get(api, False):
                print(f"[Info] service-api {api} is disabled")
                return False
        return True

    def add_result(self, k, v):
        with open(self.file_path, 'a') as f:
            f.write(f'{k}, {v}\n')

    def count_all(self):
        self.count("GCP Compute Instance", self.count_compute_instances)
        self.count("GCP Kubernetes Cluster (GKE)", self.count_kubernetes_clusters)
        self.count("GCP Cloud Function", self.count_cloud_functions)
        self.count("GCP Cloud Run", self.count_cloud_run)
        self.count("GCP Artifact Repository (only docker repositories)", self.count_artifact_repository_docker)
        self.count("GCP Container Repository", self.count_container_repository)

        self.add_result('TOTAL', self.total_resource_count)
        print("[Info] results stored at", self.file_path)

    def count(self, svcName, svcCb):
        try:
            count = svcCb()
            if count:
                self.add_result(svcName, count)
            print('[Info] Fetched ', svcName)
        except subprocess.CalledProcessError as e:
            print('[Error] Error getting ', svcName)
            print("[Error] [Command]", e.cmd)
            # print("[Error] [Command-Output]", e.output)
            self.add_result(svcName, "Error")
        except json.decoder.JSONDecodeError as e:
            print("[Error] parsing data from Cloud Provider\n", e)
            self.add_result(svcName, "Error")

    def count_compute_instances(self):
        if not self.is_api_enabled(["compute.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud compute instances list --format json",
            text=True, shell=True, 
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_kubernetes_clusters(self):
        if not self.is_api_enabled(["container.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud container clusters list --format json",
            text=True, shell=True, 
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_cloud_functions(self):
        if not self.is_api_enabled(["cloudfunctions.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            f"gcloud functions list --regions={','.join(GCP_CF_LOCATIONS)} --format json",
            text=True, shell=True, 
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_cloud_run(self):
        if not self.is_api_enabled(["run.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            f"gcloud run services list --format json",
            text=True, shell=True, 
        )
        j = json.loads(output)

        self.total_resource_count += len(j)
        return len(j)

    def count_artifact_repository_docker(self):
        if not self.is_api_enabled(["artifactregistry.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            f"gcloud artifacts repositories list --filter=\"format=docker\" --format json",
            universal_newlines=True, text=True, shell=True,
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_container_repository(self):
        if not self.is_api_enabled(["storage-api.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            f"gcloud container images list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

GCP_CF_LOCATIONS = [
    'us-west1',
    'us-central1',
    'us-east1',
    'us-east4',
    'europe-west1',
    'europe-west2',
    'asia-east1',
    'asia-east2',
    'asia-northeast1',
    'asia-northeast2',
    'us-west2',
    'us-west3',
    'us-west4',
    'northamerica-northeast1',
    'southamerica-east1',
    'europe-west3',
    'europe-west6',
    'europe-central2',
    'australia-southeast1',
    'asia-south1',
    'asia-southeast1',
    'asia-southeast2',
    'asia-northeast3'
]

if __name__ == '__main__':
    projects = PROJECTS if len(PROJECTS) > 0 else [None]
    for projectId in projects:
        try:
            SentinelOneCNSGCPUnitAudit(projectId).count_all()
        except Exception as e:
            print("[Error]", e)
