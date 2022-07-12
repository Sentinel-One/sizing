# PingSafe Sizing Scripts

### Google Cloud Script

Pre-requisites:
1. python 3+
2. `gcloud` cli
3. gcloud `alpha` component
4. gcloud `bq` cli tool
5. gcloud `gsutil` cli tool

`gcp-units.py`

To run the script
```bash
python3 ./gcp-units.py --project_id project_id
```

Output (in directory from where script is run)
```
gcp-{project_id}-units.csv
```

### AWS Script

Pre-requisites:
1. python 3+
2. `aws` cli

`aws-units.py`

To run the script:
```bash
python3 ./aws-units.py --profiles default profile_2 ... profile_n
```

Output (in directory from where script is run)
```
aws-{profile}-units.csv
aws-{profile2}-units.csv
```