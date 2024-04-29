import argparse
import json
import subprocess

# Usage python3 ./aws-units.py --profiles <profile_1> <profile_2> <profile_3> <profile_4>

parser = argparse.ArgumentParser(prog="SentinelOne CNS AWS Unit Audit")
parser.add_argument("--profiles", help="AWS profile(s) separated by space", nargs='+', default=[], required=False)
parser.add_argument("--regions", help="Regions to run script for", nargs='+', default=[], required=False)
args = parser.parse_args()

PROFILES = args.profiles
REGIONS = args.regions


def aws_describe_regions(profile):
    profile_flag = "--profile {profile}".format(profile=profile) if profile else ''
    try:
        output = subprocess.check_output(
            "aws {profile_flag} ec2 describe-regions --filters \"Name=opt-in-status,Values=opted-in,opt-in-not-required\" --output json".format(
                profile_flag=profile_flag),
            universal_newlines=True, shell=True, stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        print('[Error] Error getting regions')
        print("[Error] [Command]", e.cmd)
        print("[Error] [Command-Output]", e.output)
        return []

    if "The config profile ({profile}) could not be found".format(profile=profile) in output:
        raise Exception("found invalid aws profile {profile}".format(profile=profile))
    j = json.loads(output)
    all_regions_active = [region_object['RegionName'] for region_object in j['Regions']]
    if len(REGIONS) == 0:
        return all_regions_active

    # if only some regions to be whitelisted
    print('found whitelisted regions', REGIONS)
    regions_to_run = []
    for region in all_regions_active:
        if region in REGIONS:
            regions_to_run.append(region)
    print("valid whitelisted regions", regions_to_run)
    return regions_to_run


class SentinelOneCNSAWSUnitAudit:
    def __init__(self, profile):
        self.file_path = "aws-{profile}-units.csv".format(profile=profile) if profile else 'aws-units.csv'
        self.profile_flag = "--profile {profile}".format(profile=profile) if profile else ''
        self.total_resource_count = 0
        self.regions = aws_describe_regions(profile)

        with open(self.file_path, 'w') as f:
            # Write Header
            f.write("Resource Type, Unit Counted, Error Regions\n")

    def build_aws_cli_command(self, service, api, paginate=True, region=None, query=None):
        region_flag = paginate_flag = query_flag = ""
        if region:
            region_flag = "--region {region}".format(region=region)
        if query:
            query_flag = "--query {query}".format(query=query)
        if not paginate:
            paginate_flag = "--no-paginate"
        cmd = "aws {region_flag} {profile_flag} --output json {service} {api} {query_flag} {paginate_flag}".format(
            region_flag=region_flag, profile_flag=self.profile_flag, service=service, api=api,
            paginate_flag=paginate_flag, query_flag=query_flag
        )
        return cmd

    def add_result(self, k, v, e=""):
        with open(self.file_path, 'a') as f:
            f.write('{k}, {v}, {e}\n'.format(k=k, v=v, e=e))

    def count_all(self):
        self.count("AWS EC2 Instance", self.count_ec2_instances)
        self.count("AWS Container Repository", self.count_ecr_repositories)
        self.count("AWS Kubernetes Cluster (EKS)", self.count_eks_clusters)
        self.count("AWS ECS Cluster", self.count_ecs_clusters)
        self.count("AWS Lambda Function", self.count_lambda_functions)

        self.add_result('TOTAL', self.total_resource_count)
        print("[Info] Results stored at", self.file_path)

    def count(self, svcName, svcCb):
        count = 0
        error = ''
        for region in self.regions:
            try:
                count += svcCb(region)
            except subprocess.CalledProcessError as e:
                print('[Error] Error getting ', svcName, region)
                print("[Error] [Command]", e.cmd)
                print("[Error] [Command-Output]", e.output)
                error += f"{region}, "
            except json.decoder.JSONDecodeError as e:
                print("[Error] parsing data from Cloud Provider\n \n", e)
                error += f"{region} (JSON), "
            print(f'[info] Fetched {svcName} - {region}')
        if count or error != '':
            self.total_resource_count += count
            self.add_result(svcName, count, error)

    def count_ec2_instances(self, region):
        output = subprocess.check_output(
            # "aws --region {region} {profile_flag} --query \"Reservations[].Instances\" ec2 describe-instances --output json --no-paginate".format(region=region, profile_flag=self.profile_flag),
            self.build_aws_cli_command(
                service="ec2",
                api="describe-instances",
                paginate=False,
                query="\"Reservations[].Instances\"",
                region=region),
            universal_newlines=True, shell=True, stderr=subprocess.STDOUT
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        return len(j)

    def count_ecr_repositories(self, region):
        output = subprocess.check_output(
            # "aws --region {region} {profile_flag} ecr describe-repositories --query \"repositories[].repositoryArn\" --output json --no-paginate".format(region=region,profile_flag=self.profile_flag)
            self.build_aws_cli_command(
                service="ecr",
                api="describe-repositories",
                query="\"repositories[].repositoryArn\"",
                paginate=False,
                region=region),
            universal_newlines=True, shell=True, stderr=subprocess.STDOUT
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        return len(j)

    def count_eks_clusters(self, region):
        output = subprocess.check_output(
            # f"aws --region {region} {self.profile_flag} eks list-clusters --output json --no-paginate",
            self.build_aws_cli_command(
                service="eks",
                api="list-clusters",
                paginate=False,
                region=region),
            universal_newlines=True, shell=True, stderr=subprocess.STDOUT
        )
        j = json.loads(output)
        c = len(j.get("clusters", []))
        if j is None or len(j) == 0:
            return 0
        return c

    def count_lambda_functions(self, region):
        output = subprocess.check_output(
            # f"aws --region {region} {self.profile_flag} lambda list-functions --query 'Functions[*].FunctionName' --output json --no-paginate",
            self.build_aws_cli_command(
                service="lambda",
                api="list-functions",
                paginate=False,
                query="\"Functions[*].FunctionName\"",
                region=region),
            universal_newlines=True, shell=True, stderr=subprocess.STDOUT
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        return len(j)

    def count_ecs_clusters(self, region):
        output = subprocess.check_output(
            # f"aws --region {region} {self.profile_flag} ecs list-clusters --query 'clusterArns' --output json --no-paginate",
            self.build_aws_cli_command(
                service="ecs",
                api="list-clusters",
                paginate=False,
                query="\"clusterArns\"",
                region=region),
            universal_newlines=True, shell=True, stderr=subprocess.STDOUT
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        return len(j)


if __name__ == '__main__':
    profiles = PROFILES if len(PROFILES) > 0 else [None]
    for p in profiles:
        SentinelOneCNSAWSUnitAudit(p).count_all()
