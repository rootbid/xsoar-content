"""Cisco Umbrella Reporting v2 Integration for Cortex XSOAR (aka Demisto)
"""

import demistomock as demisto
from CommonServerPython import *  # noqa # pylint: disable=unused-wildcard-import
from CommonServerUserPython import *  # noqa

import requests
import traceback
from typing import Dict
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()  # pylint: disable=no-member


''' CONSTANTS '''

DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'  # ISO8601 format with UTC, default in XSOAR

''' CLIENT CLASS '''


class Client(BaseClient):
    """Client class to interact with the service API

    This Client implements API calls, and does not contain any XSOAR logic.
    Should only do requests and return data.
    It inherits from BaseClient defined in CommonServer Python.
    Most calls use _http_request() that handles proxy, SSL verification, etc.
    For this  implementation, no special attributes defined
    """
    def __init__(self, base_url, verify, headers, proxy, org_id):
        super().__init__(base_url=base_url, verify=verify, headers=headers, proxy=proxy, ok_codes=(200))
        self.org_id = org_id

    def get_summary(self, start: str = '', end: str = '') -> Dict[str, str]:
        """Returns a summary of top identities, destinations, URLs, categories, threats, threat types, events
        and IPs being observed in your environment within a specific timeframe.
        """
        suffix = f'/organizations/{self.org_id}/summary?from={start}&to={end}'
        response = self._http_request(
            method='GET',
            url_suffix=suffix,
            resp_type='json',
            ok_codes=(200,))
        response_data = response.get('data', {})
        return response_data

    def list_top_threats(self, start: str = '', end: str = '') -> List[Dict]:
        """Returns a List of top threats within timeframe based on both DNS and
        Proxy data.
        """
        suffix = f'/organizations/{self.org_id}/top-threats?from={start}&to={end}'
        response = self._http_request(method='GET', url_suffix=suffix, resp_type='json', ok_codes=(200,))
        response_data = response.get('data', {})
        return response_data


def test_module(client: Client) -> str:
    """Tests API connectivity and authentication'

    Returning 'ok' indicates that the integration works like it is supposed to.
    Connection to the service is successful.
    Raises exceptions if something goes wrong.

    :type client: ``Client``
    :param Client: client to use

    :return: 'ok' if test passed, anything else will fail the test.
    :rtype: ``str``
    """

    try:
        client.get_summary(start='-2days', end='now')
        message = 'ok'
    except DemistoException as e:
        if 'Forbidden' in str(e) or 'Authorization' in str(e):
            message = 'Authorization Error: make sure API Key is correctly set'
        else:
            raise e
    return message


def get_summary_command(client: Client, args: dict) -> CommandResults:
    """
    :param client: Cisco Umbrella Client for the api request.
    :param args: args from the user for the command.
    """
    start = args.get('from', '')
    end = args.get('to', '')
    response = client.get_summary(start=start, end=end)
    return CommandResults(
        outputs_prefix='UmbrellaReporting.Summary',
        outputs_key_field='object',
        outputs=response
    )


def list_top_threats_command(client: Client, args: dict) -> CommandResults:
    """
    :param client: Cisco Umbrella Client for the api request.
    :param args: args from the user for the command.
    """
    start = args.get('from', '')
    end = args.get('to', '')
    response = client.list_top_threats(start=start, end=end)
    markdown = tableToMarkdown('Top Threats', response, headers=['threat', 'threattype', 'count'])
    return CommandResults(
        readable_output=markdown,
        outputs_prefix='UmbrellaReporting.TopThreats',
        outputs_key_field=['threat', 'threattype'],
        outputs=response
    )


class UmbrellaAuthAPI:
    def __init__(self, url, ident, secret):
        self.url = url
        self.ident = ident
        self.secret = secret
        self.token = None

    def get_access_token(self):
        auth = HTTPBasicAuth(self.ident, self.secret)
        oauth_client = BackendApplicationClient(client_id=self.ident)
        oauth = OAuth2Session(client=oauth_client)
        self.token = oauth.fetch_token(token_url=self.url, auth=auth)
        return self.token


''' MAIN FUNCTION '''


def main() -> None:
    params = demisto.params()
    token_url = params.get('token_url')
    org_id = params.get('orgId')
    api_key = params.get('apiKey')
    api_secret = params.get('apiSecret')
    base_url = params['url']
    verify_certificate = not params.get('insecure', False)
    proxy = params.get('proxy', False)

    command = demisto.command()
    demisto.debug(f'Command being called is {command}')

    commands = {
        'umbrella-get-summary': get_summary_command,
        'umbrella-list-top-threats': list_top_threats_command,
    }

    try:

        product_auth = UmbrellaAuthAPI(token_url, api_key, api_secret)
        access_token = product_auth.get_access_token()["access_token"]
        headers: Dict = {
            "Authorization": f"Bearer {access_token}"
        }

        client = Client(
            base_url=base_url,
            verify=verify_certificate,
            headers=headers,
            proxy=proxy,
            org_id=org_id)

        if command == 'test-module':
            # This is the call made when pressing the integration Test button.
            result = test_module(client)
            return_results(result)

        elif command in commands:
            return_results(commands[command](client, demisto.args()))

        else:
            raise NotImplementedError(f'Command "{command}" is not implemented.')

    # Log exceptions and return errors
    except Exception as e:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute {command} command.\nError:\n{str(e)}')


''' ENTRY POINT '''


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
