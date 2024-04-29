import argparse
import json
import subprocess

# Usage python3 ./azure-units.py --subscriptions <subscription_1> <subscription_2> <subscription_3> <subscription_4>

parser = argparse.ArgumentParser(prog="SentinelOne CNS Azure Unit Audit")
parser.add_argument("--subscriptions", help="Azure subscription(s) separated by space", nargs='+', default=[], required=True)
args = parser.parse_args()

SUBSCRIPTIONS = args.subscriptions


def call_with_output(command):
    return subprocess.check_output(command, universal_newlines=True, text=True, shell=True, stderr=subprocess.STDOUT)

def check_extenstion(name):
    print("Checking extension: ",name)
    success = False
    try:
        output = call_with_output(f"az extension show -n {name}")
        success = True
    except subprocess.CalledProcessError as e:
        print('[Error] Error checking extension', name)
        print("[Error] [Command]", e.cmd)
        print("[Error] [Command-Output]", e.output)

        output = e.output

    if f"The extension {name} is not installed" in output:
        return False

    return success

def check_azure_subscription(subscription_id):
    try:
        output = call_with_output(f"az account subscription list --output json --only-show-errors")
        for subscription in json.loads(output):
            if subscription_id == subscription["subscriptionId"]:
                return True

    except subprocess.CalledProcessError as e:
        print('[Error] Error checking subscription ', subscription_id)
        print("[Error] [Command]", e.cmd)
        print("[Error] [Command-Output]", e.output)    

    return False

class SentinelOneCNSAzureUnitAudit:
    def __init__(self, subscription):
        self.file_path = f"azure-{subscription}-units.csv" if subscription else 'azure-units.csv'
        self.subscription_flag = f'--subscription "{subscription}"'.format(subscription=subscription) if subscription else ''

        self.total_resource_count = 0
        self.total_workload_count = 0

        extensions= () # example "containerapp",
        for extension in extensions:
            if not check_extenstion(extension):
                raise Exception(f"Extension not installed: {extension}. Install using az extension add -n {extension}")

        if not check_azure_subscription(subscription):
            raise Exception(f"Check azure subscription id/permissions subscription-id: {subscription}")

        with open(self.file_path, 'w') as f:
            f.write("Resource Type, Unit Counted, Workloads\n")

    def add_result(self, k, v, w=""):
        with open(self.file_path, 'a') as f:
            f.write(f'{k}, {v}, {w}\n')

    def count_all(self):
        self.count("Azure Virtual Machine", self.count_vm_instances, workload_multiplier=1)
        self.count("Azure Kubernetes Cluster (AKS)", self.count_kubernetes_clusters, workload_multiplier=1)
        self.count("Azure Container Repository", self.count_container_repository, workload_multiplier=0.1)

        self.add_result("Total Resource", self.total_resource_count, round(self.total_workload_count))
        print("[Info] Results stored at", self.file_path)

    def count(self, svcName, svcCb, workload_multiplier):
        try:
            count = svcCb()
            if count:
                workloads = count * workload_multiplier

                self.total_resource_count += count
                self.total_workload_count += workloads

                self.add_result(svcName, count, workloads)
            print(f"[Info] Fetched {svcName}")
        except subprocess.CalledProcessError as e:
            print('[Error] Error getting ', svcName)
            print("[Error] [Command]", e.cmd)
            print("[Error] [Command-Output]", e.output)
            self.add_result(svcName, "Error: Check Terminal logs")
        except json.decoder.JSONDecodeError as e:
            print("[Error] parsing data from Cloud Provider\n", e)
            self.add_result(svcName, "JSON Error")

    def count_vm_instances(self):
        output = call_with_output(f"az vm list {self.subscription_flag} --output json --only-show-errors")
        j = json.loads(output)
        return len(j)

    def count_kubernetes_clusters(self):
        output = call_with_output(f"az aks list {self.subscription_flag} --output json --only-show-errors")
        j = json.loads(output)
        return len(j)

    def count_container_repository(self):
        output = call_with_output(f"az acr list {self.subscription_flag} --output json --only-show-errors")
        registries = json.loads(output)
        total_repositories = 0

        for registry in registries:
            registryName = registry.get("name")
            output = call_with_output(f"az acr repository list {self.subscription_flag} --name {registryName} --output json")
            repositories = json.loads(output)
            total_repositories += len(repositories)

        return total_repositories

if __name__ == '__main__':
    subscriptions = SUBSCRIPTIONS if len(SUBSCRIPTIONS) > 0 else [None]
    for s in subscriptions:
        try:
            SentinelOneCNSAzureUnitAudit(s).count_all()
        except Exception as e:
            print("[Error]",e)
