import subprocess
import json
import argparse
# Usage python3 ./azure-units.py --subscriptions <subscription_1> <subscription_2> <subscription_3> <subscription_4>

parser = argparse.ArgumentParser(prog="PingSafe Azure Unit Audit")
parser.add_argument("--subscriptions", help="Azure subscription(s) separated by space", nargs='+', default=[], required=False)
args = parser.parse_args()

SUBSCRIPTIONS = args.subscriptions


def call_with_output(command):
    success = False
    retries = 3
    while(retries > 0 and not success ):
        try:
            output = subprocess.check_output(command, text=True, shell=True)
            success = True
            break
        except subprocess.CalledProcessError as e:
            output = e.output
        retries = retries - 1
        print(f"retries {retries}/3")
    return(success, output)

def check_extenstion(name):
    print("Checking extension: ",name)
    success = False
    try:
        success, output = call_with_output(f"az extension show -n {name}")
        success = True 
    except subprocess.CalledProcessError as e:
        output = e.output
    if f"The extension {name} is not installed" in output:
        return False
    return success

def azure_show_subscription(subscription):
    success, output = call_with_output(f"az account subscription show --subscription-id {subscription} --output json")
    if f"SubscriptionNotFound" in output:
        return False
    return success

class PingSafeAzureUnitAudit:
    def __init__(self, subscription):
        self.file_path = f"azure-{subscription}-units.csv" if subscription else 'azure-units.csv'
        self.subscription_flag = f'--subscription "{subscription}"'
        self.total_resource_count = 0
        
        extensions= ("containerapp",)
        for extension in extensions:
            if not check_extenstion(extension):
                raise Exception(f"Extension not installed: {extension}. Install using az extension add -n {extension}")
            
        if not azure_show_subscription(subscription):
            raise Exception(f"check azure subscription id/permissions subscription-id: {subscription}")
        
        with open(self.file_path, 'w') as f:
            f.write("Resource Type, Unit Counted\n")

    def add_result(self, k, v):
        with open(self.file_path, 'a') as f:
            f.write(f'{k}, {v}\n')

    def count_all(self):
        self.add_result("App Services", self.count_app_services())
        accounts = self.list_storage_accounts()
        count_storage_blob_container = 0
        count_storage_file_share = 0
        count_storage_queue = 0
        count_storage_table = 0
        for account in accounts:
            key = self.get_storage_account_keys(account)
            count_storage_blob_container += self.count_storage_blob_container(account, key)
            count_storage_file_share += self.count_storage_file_share(account, key)
            count_storage_queue += self.count_storage_queue(account, key)
            count_storage_table += self.count_storage_table(account, key)

        self.add_result("Storage Account", self.count_storage_accounts(accounts))
        self.add_result("Storage Blob Container", count_storage_blob_container)
        self.add_result("Storage File Share", count_storage_file_share)
        self.add_result("Storage Queue", count_storage_queue)
        self.add_result("Storage Table", count_storage_table)

        self.add_result("Virtual Machine", self.count_vm_instances())
        self.add_result("Compute Disks", self.count_disks())
        self.add_result("Compute Virtual Machine Scale Sets", self.count_vm_instance_scale_sets())
        self.add_result("Virtual Networks", self.count_vpc_networks())
        self.add_result("Network Security Group", self.count_network_security_group())
        self.add_result("Network Watcher", self.count_network_watcher())
        self.add_result("Application Gateway", self.count_app_gateway())
        self.add_result("Network Load Balancer", self.count_load_balancers())
        self.add_result("SQL Servers", self.count_sql_server())
        self.add_result("Databases for PostgreSql Server", self.count_postgres_server())
        self.add_result("Databases for MySql Server", self.count_mysql_server())
        self.add_result("Cache for Redis", self.count_redis())
        self.add_result("CDN Profile", self.count_cdn_profile())
        self.add_result("Key Vault", self.count_key_vault())
        self.add_result("Container Registry", self.count_container_registry())
        self.add_result("Container Instance", self.count_container_instance())
        self.add_result("Container Apps", self.count_containerapp())
        self.add_result("Kubernetes Cluster", self.count_kubernetes_clusters())
        self.add_result("CosmosDB Account", self.count_cosmosdb())
        self.add_result("Total Resource", self.total_resource_count)
        print("results stored at", self.file_path)

    def count_storage_blob_container(self, account, key):
        print(f"getting storage account ({account}) data for count_storage_blob_container")
        success, output = call_with_output(f"az storage container list --account-key {key} --account-name {account} {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_storage_file_share(self, account, key):
        print(f"getting storage account ({account}) data for count_storage_file_share")
        success, output = call_with_output(f"az storage share list --account-key {key} --account-name {account} {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_storage_queue(self, account, key):
        print(f"getting storage account ({account}) data for count_storage_queue")
        success, output = call_with_output(f"az storage queue list --account-key {key} --account-name {account} {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_storage_table(self, account, key):
        print(f"getting storage account ({account}) data for count_storage_table")
        success, output = call_with_output(f"az storage table list --account-key {key} --account-name {account} {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_app_services(self):
        print('getting data for count_app_services')
        success, output = call_with_output(f"az appservice ase list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def list_storage_accounts(self):
        success, output = call_with_output(f"az storage account list {self.subscription_flag}  --query '[].name' --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        return json.loads(output)
    
    def get_storage_account_keys(self, account):
        success, output = call_with_output(f"az storage account keys list --account-name {account} {self.subscription_flag}  --query '[0].value' --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        return json.loads(output)
    
    def count_storage_accounts(self, storage_accounts_list):
        print('getting data for count_storage_accounts')
        self.total_resource_count += len(storage_accounts_list)
        return len(storage_accounts_list)

    def count_vm_instances(self):
        print('getting data for count_vm_instances')
        success, output = call_with_output(f"az vm list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_vm_instance_scale_sets(self):
        print('getting data for count_vm_instance_scale_sets')
        success, output = call_with_output(f"az vmss list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_disks(self):
        print('getting data for count_disks')
        success, output = call_with_output(f"az disk list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)


    def count_vpc_networks(self):
        print('getting data for count_vpc_networks')
        success, output = call_with_output(f"az network vnet list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_sql_server(self):
        print('getting data for count_sql_server')
        success, output = call_with_output(f"az sql server list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
        
    def count_postgres_server(self):
        print('getting data for count_postgres_server')
        success, output = call_with_output(f"az postgres server list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_redis(self):
        print('getting data for count_redis')
        success, output = call_with_output(f"az redis list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_mysql_server(self):
        print('getting data for count_mysql_server')
        success, output = call_with_output(f"az mysql server list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_network_watcher(self):
        print('getting data for count_network_watcher')
        success, output = call_with_output(f"az network watcher list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_network_security_group(self):
        print('getting data for count_network_security_group')
        success, output = call_with_output(f"az network nsg list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_key_vault(self):
        print('getting data for count_key_vault')
        success, output = call_with_output(f"az keyvault list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_kubernetes_clusters(self):
        print('getting data for count_kubernetes_clusters')
        success, output = call_with_output(f"az aks list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_cdn_profile(self):
        print('getting data for count_cdn_profile')
        success, output = call_with_output(f"az cdn profile list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_container_registry(self):
        print('getting data for count_container_registry')
        success, output = call_with_output(f"az acr list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_container_instance(self):
        print('getting data for count_container_instance')
        success, output = call_with_output(f"az container list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_containerapp(self):
        print('getting data for count_containerapp')
        success, output = call_with_output(f"az containerapp list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_cosmosdb(self):
        print('getting data for count_cosmosdb')
        success, output = call_with_output(f"az cosmosdb list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_network_watcher(self):
        print('getting data for count_network_watcher')
        success, output = call_with_output(f"az network watcher list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_container(self):
        print('getting data for count_container')
        success, output = call_with_output(f"az container list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_app_gateway(self):
        print('getting data for count_app_gateway')
        success, output = call_with_output(f"az network application-gateway list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)
    
    def count_load_balancers(self):
        print('getting data for count_load_balancers')
        success, output = call_with_output(f"az network lb list {self.subscription_flag} --output json")
        if not success:
            print("Failed with error: ",output)
            return 0
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

if __name__ == '__main__':
    subscriptions = SUBSCRIPTIONS if len(SUBSCRIPTIONS) > 0 else [None]
    for s in subscriptions:
        PingSafeAzureUnitAudit(s).count_all()
