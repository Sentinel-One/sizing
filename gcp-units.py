import subprocess
import json
import argparse

# Usage python3 ./gcp-units.py --project_id <project_id>

parser = argparse.ArgumentParser(prog="PingSafe GCP Unit Audit")
parser.add_argument("--project_id", help="GCP Project ID", required=True)
args = parser.parse_args()

PROJECT_ID = args.project_id


def gcloud_set_project(project_id):
    output = subprocess.check_output(
        f"gcloud config set project {project_id}",
        text=True, shell=True, stderr=subprocess.STDOUT
    )
    print(output)
    if f"WARNING: You do not appear to have access to project [{project_id}] or it does not exist." in output:
        return False
    return True


def gcloud_components_check():
    output = subprocess.check_output(
        "gcloud --version",
        text=True, shell=True
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
            print("missing component:", component)
            print("required gcloud components:", "alpha", "bq", "gsutil")
            return False
    return True


def gcloud_list_services():
    output = subprocess.check_output(
        "gcloud services list --format json",
        text=True, shell=True
    )
    services = json.loads(output)
    for service in services:
        yield {
            'name': service['config']['name'],
            'enabled': service['state'] == 'ENABLED'
        }


class PingSafeGCPUnitAudit:
    def __init__(self, project_id):
        self.existing_permissions = {}
        self.project_id = project_id
        self.file_path = f"gcp-{project_id}-units.csv"
        self.total_resource_count = 0

        if not gcloud_set_project(project_id):
            raise Exception("check gcp project id/permissions")
        print("successfully set gcloud project id:", project_id)

        if not gcloud_components_check():
            raise Exception("check installed components")
        print("found all required cli components")

        for service in gcloud_list_services():
            if service['enabled']:
                self.existing_permissions[service['name']] = True
        print("fetched all existing permissions on account")

        with open(self.file_path, 'w') as f:
            # Write Header
            f.write("Resource Type, Unit Counted\n")

    def is_api_enabled(self, apis):
        for api in apis:
            if not self.existing_permissions.get(api, False):
                print(f"service-api {api} is disabled")
                return False
        return True

    def add_result(self, k, v):
        with open(self.file_path, 'a') as f:
            f.write(f'{k}, {v}\n')

    def count_all(self):
        self.add_result("Load Balancers", self.count_load_balancers())
        self.add_result("Compute Instances", self.count_compute_instances())
        self.add_result("Disks", self.count_disks())
        self.add_result("VPC Networks", self.count_vpc_networks())
        self.add_result("Firewalls", self.count_firewalls())
        self.add_result("Managed DNS Zones", self.count_managed_dns_zones())

        # All iam users also includes service accounts
        all_iam_users = self.count_all_iam_users()
        all_service_account_users = self.count_all_service_account_users()
        self.total_resource_count -= all_service_account_users
        self.add_result("IAM Users", all_iam_users - all_service_account_users)
        self.add_result("Service Account Users", all_service_account_users)

        self.add_result("Kubernetes Clusters", self.count_kubernetes_clusters())
        self.add_result("Alert Policies", self.count_alert_policies())
        self.add_result("Log Sinks", self.count_log_sinks())
        self.add_result("SQL Instances", self.count_sql_instances())
        self.add_result("Storage Buckets", self.count_storage_buckets())

        self.add_result("Pub Sub Topics", self.count_pub_sub_topics())
        self.add_result("Spanner Instances", self.count_spanner_instances())
        self.add_result("Cloud Functions", self.count_cloud_functions())

        big_query_datasets, big_query_tables = self.count_big_query_datasets_tables()
        self.add_result("Big Query Datasets", big_query_datasets)
        self.add_result("Big Query Tables", big_query_tables)

        self.add_result('TOTAL', self.total_resource_count)
        print("results stored at", self.file_path)

    def count_load_balancers(self):
        print('getting data for count_load_balancers')
        if not self.is_api_enabled(["compute.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud compute forwarding-rules list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_compute_instances(self):
        print('getting data for count_compute_instances')
        if not self.is_api_enabled(["compute.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud compute instances list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_disks(self):
        print('getting data for count_disks')
        if not self.is_api_enabled(["compute.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud compute disks list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_vpc_networks(self):
        print('getting data for count_vpc_networks')
        if not self.is_api_enabled(["compute.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud compute networks list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_firewalls(self):
        print('getting data for count_firewalls')
        if not self.is_api_enabled(["compute.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud compute firewall-rules list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_managed_dns_zones(self):
        print('getting data for count_managed_dns_zones')
        if not self.is_api_enabled(["dns.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud dns managed-zones list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_all_iam_users(self):
        print('getting data for count_all_iam_users')
        if not self.is_api_enabled(["iam.googleapis.com", "orgpolicy.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            f"gcloud projects get-iam-policy {self.project_id} --flatten=\"bindings[].members\" --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_all_service_account_users(self):
        print('getting data for count_all_service_account_users')
        if not self.is_api_enabled(["iam.googleapis.com", "orgpolicy.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud iam service-accounts list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_kubernetes_clusters(self):
        print('getting data for count_kubernetes_clusters')
        if not self.is_api_enabled(["container.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud container clusters list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_alert_policies(self):
        print('getting data for count_alert_policies')
        if not self.is_api_enabled(["monitoring.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud alpha monitoring policies list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_log_sinks(self):
        print('getting data for count_log_sinks')
        if not self.is_api_enabled(["logging.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud logging sinks list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_sql_instances(self):
        print('getting data for count_sql_instances')
        if not self.is_api_enabled(["sqladmin.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud sql instances list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_storage_buckets(self):
        print('getting data for count_storage_buckets')
        if not self.is_api_enabled(["storage.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            f"gsutil ls -p {self.project_id}",
            text=True, shell=True
        )
        j = list(filter(lambda x: len(x.strip()) > 0, output.split('\n')))
        self.total_resource_count += len(j)
        return len(j)

    def count_pub_sub_topics(self):
        print('getting data for count_pub_sub_topics')
        if not self.is_api_enabled(["pubsub.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud pubsub topics list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_spanner_instances(self):
        print('getting data for count_spanner_instances')
        if not self.is_api_enabled(["spanner.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            "gcloud spanner instances list --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_cloud_functions(self):
        print('getting data for count_cloud_functions')
        if not self.is_api_enabled(["cloudfunctions.googleapis.com"]):
            return 0
        output = subprocess.check_output(
            f"gcloud functions list --regions={','.join(GCP_CF_LOCATIONS)} --format json",
            text=True, shell=True
        )
        j = json.loads(output)
        self.total_resource_count += len(j)
        return len(j)

    def count_big_query_datasets_tables(self):
        print('getting data for count_big_query_datasets_tables')
        if not self.is_api_enabled(["bigquery.googleapis.com"]):
            return 0, 0
        dataset_count, table_count = 0, 0
        output = subprocess.check_output(
            f"bq ls --project_id {self.project_id} --format json",
            text=True, shell=True
        )
        if len(output) == 0:
            output = "[]"
        datasets = json.loads(output)
        dataset_count = len(datasets)
        for dataset in datasets:
            output = subprocess.check_output(
                f"bq ls --project_id {self.project_id} --max_results 10000 --format json {dataset['id']}",
                text=True, shell=True
            )
            if len(output) == 0:
                output = "[]"
            tables = json.loads(output)
            table_count += len(tables)
        self.total_resource_count += dataset_count + table_count
        return dataset_count, table_count


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

PingSafeGCPUnitAudit(PROJECT_ID).count_all()
