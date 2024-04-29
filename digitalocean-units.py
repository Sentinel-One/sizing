import argparse
import json
import subprocess

# Usage python3 ./digitalocean-units.py --contexts <context_1> <context_2> <context_3> <context_4>

parser = argparse.ArgumentParser(prog="SentinelOne CNS Digital Ocean Unit Audit")
parser.add_argument("--contexts", help="Digital Ocean CLI Contexts separated by space", nargs='+', default=[], required=False)
args = parser.parse_args()

CONTEXTS = args.contexts

class SentinelOneCNSDigitalOceanUnitAudit:
    def __init__(self, context):
        self.file_path = "digitalocean-{context}-units.csv".format(context=context) if context else 'digitalocean-units.csv'
        self.context_flag = "--context {context}".format(context=context) if context else ''
        self.total_resource_count = 0
        self.total_workload_count = 0

        with open(self.file_path, 'w') as f:
            f.write("Resource Type, Unit Counted, Workloads\n")

    def add_result(self, k, v, w=""):
        with open(self.file_path, 'a') as f:
            f.write('{k}, {v}, {w}\n'.format(k=k,v=v,w=w))

    def count_all(self):
        self.count("Digital Ocean Droplets", self.count_droplets, workload_multiplier=1)
        self.add_result('TOTAL', self.total_resource_count, round(self.total_workload_count))
        print("[Info] results stored at", self.file_path)
        
    def count(self, svcName, svcCb, workload_multiplier):
        try:
            count = svcCb()
            if count:
                workloads = count * workload_multiplier
                self.total_resource_count += count
                self.total_workload_count += workloads

                self.add_result(svcName, count, workloads)
            print('[Info] Fetched ', svcName)
        except subprocess.CalledProcessError as e:
            print('[Error] Error getting ', svcName)
            print("[Error] [Command]", e.cmd)
            print("[Error] [Command-Output]", e.output)
            self.add_result(svcName, "Error")
        except json.decoder.JSONDecodeError as e:
            print("[Error] parsing data from Cloud Provider\n", e)
            self.add_result(svcName, "JSON Error")

    def count_droplets(self):
      output = subprocess.check_output(
          f"doctl compute droplet list --output json {self.context_flag}",
          text=True, shell=True
      )
      j = json.loads(output)
      return len(j)

if __name__ == '__main__':
    contexts = CONTEXTS if len(CONTEXTS) > 0 else [None]
    for context in contexts:
        SentinelOneCNSDigitalOceanUnitAudit(context).count_all()
