import boto3
from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError
import os
import json
import datetime
import hashlib
import pathlib
import subprocess
import git


def branch_to_net(branch):
    if branch != DEPLOY_VERSION:
        return "betanet"
    elif branch == "beta":
        return "guildnet"
    elif branch == "stable":
        return "testnet"


branch=os.getenv('GITHUB_REF')
net=branch_to_net(branch)
commit=os.getenv('GITHUB_SHA')
if commit == "HEAD":
    commit=subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip()

def upload_s3(local_file, bucket, s3_file):
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

    try:
        s3.upload_file(local_file, bucket, s3_file)
        print("Upload Successful")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False

def upload_config(net, config):
    json.dump(config, open('/tmp/near/config.json', 'w'), indent=2)
    with open(f'/tmp/near/boot_nodes', 'w') as f:
        f.write(config['network']['boot_nodes'])
    upload_s3('boot_nodes', net, 'boot_nodes')
    upload_s3('node0/config.json', net, 'config.json')


def update_deploy(net, commit, branch=None):
    print(f"Deploying {branch}:{commit} to {net}")
    deploy_timestamp = datetime.datetime.strftime(datetime.datetime.utcnow(),
                                                  '%Y%m%d_%H%M%S')
    with open(f'/tmp/near/commit', 'w') as f:
        f.write(commit)
    with open('/tmp/near/latest_deploy_at', 'w') as f:
        f.write(deploy_timestamp)

    upload_s3('commit', net, 'latest_deploy')
    upload_s3('latest_deploy_at', net, 'latest_deploy_at')

    if branch:
        with open('/tmp/near/latest_release', 'w') as f:
            f.write(branch)
        upload_s3('latest_release', net, 'latest_release')


def upload_genesis(net, genesis):
    tmpdir = pathlib.Path('/tmp/near')

    def md5sum(src: str, dst: str) -> None:
        chsum = hashlib.md5((tmpdir / src).read_bytes()).hexdigest()
        (tmpdir / dst).write_text(chsum)

    with open(tmpdir / 'genesis.json', 'w') as f:
        json.dump(genesis, f, indent=2)
    with open(tmpdir / 'protocol_version', 'w') as f:
        f.write(str(genesis['protocol_version']))
    md5sum('genesis.json', 'genesis_md5sum')
    with open(tmpdir / 'genesis_time', 'w') as f:
        f.write(genesis['genesis_time'])
    if net != 'mainnet':
        subprocess.check_call(('xz', '-k9', tmpdir / 'genesis.json'))
        md5sum('genesis.json.xz', 'genesis_xz_md5sum')
        upload_s3('genesis.json', net, 'genesis.json')
        upload_s3('genesis.json.xz', net, 'genesis.json.xz')
        upload_s3('genesis_xz_md5sum', net, 'genesis.json.xz')
    else:
        print(
            'Please update neard/res/mainnet/mainnet_genesis.json with /tmp/near/genesis.json and merge it to stable'
        )
        input('Press enter once you’re done')

    s3 = boto3.resource('s3')

    upload_s3('genesis_md5sum', net, 'genesis_md5sum')
    upload_s3('protocol_version', net, 'protocol_version')
    upload_s3('genesis_time', net, 'genesis_time')
    #upload_config(net,)
    #upload_genesis(net,)
    #update_deploy(net,)
