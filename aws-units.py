import subprocess
import json
import argparse

# Usage python3 ./aws-units.py --profiles <profile_1> <profile_2> <profile_3> <profile_4>

parser = argparse.ArgumentParser(prog="PingSafe AWS Unit Audit")
parser.add_argument("--profiles", help="AWS profile(s) separated by space", nargs='+', default=[], required=True)
parser.add_argument("--regions", help="Regions to run script for", nargs='+', default=[], required=False)
args = parser.parse_args()

PROFILES = args.profiles
REGIONS = args.regions


def aws_describe_regions(profile='default'):
    output = subprocess.check_output(
        f"aws --profile {profile} ec2 describe-regions --filters \"Name=opt-in-status,Values=opted-in,opt-in-not-required\" --output json",
        text=True, shell=True, stderr=subprocess.STDOUT
    )
    if f"The config profile ({profile}) could not be found" in output:
        raise Exception(f"found invalid aws profile {profile}")
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


class PingSafeAWSUnitAudit:
    def __init__(self, profile):
        self.profile = profile
        self.file_path = f"aws-{profile}-units.csv"
        self.total_resource_count = 0
        self.regions = aws_describe_regions(profile)

        with open(self.file_path, 'w') as f:
            # Write Header
            f.write("Resource Type, Unit Counted\n")

    def add_result(self, k, v):
        with open(self.file_path, 'a') as f:
            f.write(f'{k}, {v}\n')

    def count_all(self):
        agv1_rest_api_count = 0
        cloudfront_distribution_count = 0
        elastic_ips_count = 0
        ec2_instances_count = 0
        ecr_repositories_count = 0
        lb_v1_count = 0
        lb_v2_count = 0
        rdb_db_instance_count = 0
        s3_bucket_count = 0
        agv2_api_count = 0
        redshift_cluster_count = 0
        eks_cluster_count = 0
        eb_env_count = 0

        # Region Agnostic
        s3_bucket_count += self.count_s3_buckets()
        cloudfront_distribution_count += self.count_cloudfront_distributions()
        redshift_cluster_count += self.count_redshift_clusters()
        elastic_ips_count += self.count_elastic_ips()

        # Region Specific
        for region in self.regions:
            agv1_rest_api_count += self.count_rest_api(region)
            ec2_instances_count += self.count_ec2_instances(region)
            ecr_repositories_count += self.count_ecr_repositories(region)
            lb_v1_count += self.count_load_balancers_v1(region)
            lb_v2_count += self.count_load_balancers_v2(region)
            rdb_db_instance_count += self.count_rds_db_instances(region)
            agv2_api_count += self.count_apis_v2(region)
            eks_cluster_count += self.count_eks_clusters(region)
            eb_env_count += self.count_elastic_beanstalk_environments(region)

        self.add_result("ApiGateway V1 Rest APIs", agv1_rest_api_count)
        self.add_result("CloudFront Distributions", cloudfront_distribution_count)
        self.add_result("Elastic IPs", elastic_ips_count)
        self.add_result("EC2 Instances", ec2_instances_count)
        self.add_result("ECR Repositories", ecr_repositories_count)
        self.add_result("LoadBalancer V1 Instances", lb_v1_count)
        self.add_result("LoadBalancer V2 Instances", lb_v2_count)
        self.add_result("RDB DB instances", rdb_db_instance_count)
        self.add_result("S3 Buckets", s3_bucket_count)
        self.add_result("ApiGateway V2 APIs", agv2_api_count)
        self.add_result("Redshift Clusters", redshift_cluster_count)
        self.add_result("EKS Clusters", eks_cluster_count)
        self.add_result("ElasticBeanstalk Environments", eb_env_count)

        self.add_result('TOTAL', self.total_resource_count)
        print("results stored at", self.file_path)

    def count_rest_api(self, region):
        print('getting data for count_rest_api', region)
        output = subprocess.check_output(
            f"aws --region {region} --profile {self.profile} apigateway get-rest-apis --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        c = len(j.get("items", []))
        self.total_resource_count += c
        return c

    # Region agnostic
    def count_cloudfront_distributions(self):
        print('getting data for count_cloudfront_distributions')
        output = subprocess.check_output(
            f"aws --profile {self.profile} cloudfront list-distributions --query \"DistributionList.Items[].Id\" --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        c = len(j)
        self.total_resource_count += c
        return c

    # Region agnostic
    def count_elastic_ips(self):
        print('getting data for count_elastic_ips')
        output = subprocess.check_output(
            f"aws --profile {self.profile} ec2 describe-addresses --query \"Addresses[].PublicIp\" --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        c = len(j)
        self.total_resource_count += c
        return c

    def count_ec2_instances(self, region):
        print('getting data for count_ec2_instances', region)
        output = subprocess.check_output(
            f"aws --region {region} --profile {self.profile} --query \"Reservations[].Instances\" ec2 describe-instances --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        c = len(j)
        self.total_resource_count += c
        return c

    def count_ecr_repositories(self, region):
        print('getting data for count_ecr_repositories', region)
        output = subprocess.check_output(
            f"aws --region {region} --profile {self.profile} ecr describe-repositories --query \"repositories[].repositoryArn\" --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        c = len(j)
        self.total_resource_count += c
        return c

    # Region agnostic
    def count_load_balancers_v1(self, region):
        print('getting data for count_load_balancers_v1', region)
        output = subprocess.check_output(
            f"aws --region {region} --profile {self.profile} elb describe-load-balancers --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        c = len(j.get("LoadBalancerDescriptions", []))
        self.total_resource_count += c
        return c

    # Region agnostic
    def count_load_balancers_v2(self, region):
        print('getting data for count_load_balancers_v2', region)
        output = subprocess.check_output(
            f"aws --region {region} --profile {self.profile} elbv2 describe-load-balancers --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        c = len(j.get("LoadBalancers", []))
        self.total_resource_count += c
        return c

    def count_rds_db_instances(self, region):
        print('getting data for count_rds_db_instances', region)
        output = subprocess.check_output(
            f"aws --region {region} --profile {self.profile} rds describe-db-instances --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        if j is None or len(j) == 0:
            return 0
        c = len(j.get("DBInstances", []))
        self.total_resource_count += c
        return c

    # s3 api is region agnostic
    def count_s3_buckets(self):
        print('getting data for count_s3_buckets')
        output = subprocess.check_output(
            f"aws --profile {self.profile} s3api list-buckets --query \"Buckets[].Name\" --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        c = len(j)
        if j is None or len(j) == 0:
            return 0
        self.total_resource_count += c
        return c

    def count_apis_v2(self, region):
        print('getting data for count_apis_v2', region)
        output = subprocess.check_output(
            f"aws --region {region} --profile {self.profile} apigatewayv2 get-apis --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        c = len(j.get("Items", []))
        if j is None or len(j) == 0:
            return 0
        self.total_resource_count += c
        return c

    # Region agnostic
    def count_redshift_clusters(self):
        print('getting data for count_redshift_clusters')
        output = subprocess.check_output(
            f"aws --profile {self.profile} redshift describe-clusters --query \"Clusters[].ClusterIdentifier\" --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        c = len(j)
        if j is None or len(j) == 0:
            return 0
        self.total_resource_count += c
        return c

    def count_eks_clusters(self, region):
        print('getting data for count_eks_clusters', region)
        output = subprocess.check_output(
            f"aws --region {region} --profile {self.profile} eks list-clusters --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        c = len(j.get("clusters", []))
        if j is None or len(j) == 0:
            return 0
        self.total_resource_count += c
        return c

    def count_elastic_beanstalk_environments(self, region):
        print('getting data for count_elastic_beanstalk_environments', region)
        output = subprocess.check_output(
            f"aws --region {region} --profile {self.profile} elasticbeanstalk describe-environments --query \"Environments[].EnvironmentId\" --output json --no-paginate",
            text=True, shell=True
        )
        j = json.loads(output)
        c = len(j)
        if j is None or len(j) == 0:
            return 0
        self.total_resource_count += c
        return c


if __name__ == '__main__':
    for p in PROFILES:
        PingSafeAWSUnitAudit(p).count_all()
