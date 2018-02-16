#!/usr/bin/env python

import re
from urllib import parse as urlparse
import requests
from aws_requests_auth.aws_auth import AWSRequestsAuth
from aws_requests_auth import boto_utils

GITHUB_PROXY_URL = 'https://h7t4pmskpe.execute-api.us-east-1.amazonaws.com/dev/repos/WisdomWolf/gamefly-calcs/issues'

def get_aws_auth(url):
    api_gateway_netloc = urlparse.urlparse(url).netloc
    api_gateway_region = re.match(
        r"[a-z0-9]+\.execute-api\.(.+)\.amazonaws\.com",
        api_gateway_netloc
    ).group(1)

    return AWSRequestsAuth(
        aws_host=api_gateway_netloc,
        aws_region=api_gateway_region,
        aws_service='execute-api',
        **boto_utils.get_credentials()
    )


if __name__ == '__main__':
    list_issues_response = requests.get(
        url=GITHUB_PROXY_URL,
        auth=get_aws_auth(GITHUB_PROXY_URL)
    )
    print(list_issues_response.json())

