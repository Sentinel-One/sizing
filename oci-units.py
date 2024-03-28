import subprocess
import json
import argparse

# Usage python3 ./oci-units.py --profiles profile_1 profile_2 profile_3 --compartments compartment_1 compartment_2 --args "--auth security_token"
parser = argparse.ArgumentParser(prog="PingSafe OCI Unit Audit")

parser.add_argument("--profiles", help="OCI profile(s) separated by space", nargs='+', default=[], required=False)
parser.add_argument("--compartments", help="Compartments to run script for", nargs='+', default=[], required=False)
parser.add_argument("--args", help="OCI CLI aditional args", nargs='+', default=[], required=False)

args = parser.parse_args()

ADITIONAL_ARGS = " ".join(args.args)
PROFILES = args.profiles
COMPARTMENTS = args.compartments

class PingSafeOCIUnitAudit:
    def __init__(self, profile):
        self.file_path = "oci-{profile}-units.csv".format(profile=profile) if profile else 'oci-units.csv'
        self.profile_flag = "--profile {profile}".format(profile=profile) if profile else ''

        self.total_resource_count = 0
        with open(self.file_path, 'w') as f:
            f.write("Resource Type, Unit Counted\n")

    def add_result(self, k, v):
        with open(self.file_path, 'a') as f:
            f.write('{k}, {v}\n'.format(k=k,v=v))

    def count_all(self):
        compute_instance_count = 0
        kubernetes_cluster_count = 0

        compartments = self.get_compartments()

        for compartmentId, compartmentName in compartments.items():
            print("Fetching resources of compartment", compartmentName)
            compute_instance_count += self.count_compute_instance(compartmentId)
            kubernetes_cluster_count += self.count_kubernetes_cluster(compartmentId)

        self.add_result("Oracle Compute Instance", compute_instance_count)
        self.add_result("Oracle Kubernetes Cluster", kubernetes_cluster_count)
        self.add_result('TOTAL', self.total_resource_count)
        print("results stored at", self.file_path)

    def get_compartments(self):
        print("Fetching Compartments")
        output = subprocess.check_output(
            f"oci iam compartment list --all --include-root --compartment-id-in-subtree true --access-level ACCESSIBLE --lifecycle-state ACTIVE --output json {ADITIONAL_ARGS}",
                text=True, shell=True
            )
        j = json.loads(output)
        compartments = {}

        for i in j.get('data'):
            compartments[i.get("id")] = i.get("name")

        # when COMPARTMENTS are passed manually, returning only mentioned comartmentIds with name
        if len(COMPARTMENTS) != 0:
            return {key: val for key, val in compartments.items() if key in COMPARTMENTS}

        return compartments

    def count_compute_instance(self, compartmentId):
      print("Fetching count_compute_instance")
      output = subprocess.check_output(
          f"oci compute instance list --all --output json --compartment-id {compartmentId} {self.profile_flag} {ADITIONAL_ARGS}",
          text=True, shell=True
      )
      if output == None or output == "":
          return 0
      j = json.loads(output)
      self.total_resource_count += len(j.get('data'))
      return len(j.get('data'))

    def count_kubernetes_cluster(self, compartmentId):
      print("Fetching count_kubernetes_cluster")
      output = subprocess.check_output(
          f"oci ce cluster list --all --output json --compartment-id {compartmentId} {self.profile_flag} {ADITIONAL_ARGS}",
          text=True, shell=True
      )
      if output == None or output == "":
          return 0
      j = json.loads(output)
      self.total_resource_count += len(j.get('data'))
      return len(j.get('data'))

if __name__ == '__main__':
    profiles = PROFILES if len(PROFILES) > 0 else [None]
    for p in profiles:
        PingSafeOCIUnitAudit(p).count_all()
