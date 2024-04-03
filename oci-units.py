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
            f.write("Resource Type, Unit Counted, Error Compartments\n")

    def add_result(self, k, v, e=''):
        with open(self.file_path, 'a') as f:
            f.write('{k}, {v} {e}\n'.format(k=k,v=v, e=e))

    def count_all(self):
        self.compartments = self.get_compartments()
        self.count("Oracle Compute Instance", self.count_compute_instance)
        self.count("Oracle Kubernetes Cluster", self.count_kubernetes_cluster)

        self.add_result('TOTAL', self.total_resource_count)
        print("[Info] Results stored at", self.file_path)

    def count(self, svcName, svcCb):
        count = 0
        error = ''
        for compartmentId, compartmentName in self.compartments.items():
            try:
                count += svcCb(compartmentId)
            except subprocess.CalledProcessError as e:
                print('[Error] Error getting ', svcName)
                print("[Error] [Command]", e.cmd)
                print("[Error] [Command-Output]", e.output)
                error += f"{compartmentId}, "
            except json.decoder.JSONDecodeError as e:
                print("[Error] parsing data from Cloud Provider\n", e)
                error += f"{compartmentId} (JSON), "
            print(f'[Info] Fetched {compartmentName} - {svcName}')
        self.add_result(svcName, count, error)

    def get_compartments(self):
        print("[Info] Fetching Compartments")
        try:
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
        except subprocess.CalledProcessError as e:
            print('[Error] Error getting Compartments', )
            print("[Error] [Command]", e.cmd)
            print("[Error] [Command-Output]", e.output)
            return {}

    def count_compute_instance(self, compartmentId):
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
