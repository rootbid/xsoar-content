import json
import io
import requests_mock
from freezegun import freeze_time
import demistomock as demisto


URL = 'https://example.my.idaptive.app/'
DEMISTO_PARAMS = {
    'url': URL,
    'credentials': {
        'identifier': 'admin@example.com.11',
        'password': '123456',
    },
    'from': '3 days',
    'app_id': 'test_app',
    'limit': 100,
}


def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())


@freeze_time('2022-05-12T00:00:00Z')
def test_fetch_events_few_events(mocker):
    """
    Given
        - 3 events was created in CyberArk side in the last 3 days.
    When
        - fetch-events is running (with limit set to 100).
    Then
        - Verify that all 3 events were created in XSIAM.
        - Verify last_run was set as expected.
    """

    params = mocker.patch.object(demisto, 'params', return_value=DEMISTO_PARAMS)
    mocker.patch.object(demisto, 'args', return_value={})
    last_run = mocker.patch.object(demisto, 'getLastRun', return_value={})
    results = mocker.patch.object(demisto, 'results')
    mocker.patch('CyberArkEventCollector.send_events_to_xsiam')

    with requests_mock.Mocker() as m:
        m.get(f'{URL}oauth2/token/test_app', json={'access_token': '123456abc'})
        m.get(f'{URL}RedRock/Query', json=util_load_json('test_data/events.json'))

        from CyberArkEventCollector import main
        main('CyberArk-get-events', params.return_value)

    events = results.call_args[0][0]['Contents']
    assert last_run.return_value.get('from') == '2022-05-15T13:35:26.645000'
    assert len(last_run.return_value.get('ids')) == len(events) == 3


@freeze_time('2022-05-12T00:00:00Z')
def test_fetch_events_no_events(mocker):
    """
    Given
        - 3 events was created in CyberArk side in the last 3 days.
    When
        - fetch-events is running (with limit set to 100).
    Then
        - Make sure no events was created in XSIAM.
        - Make sure last_run was set as expected.
    """

    params = mocker.patch.object(demisto, 'params', return_value=DEMISTO_PARAMS)
    mocker.patch.object(demisto, 'args', return_value={})
    last_run = mocker.patch.object(demisto, 'getLastRun', return_value={})
    results = mocker.patch.object(demisto, 'results')
    mocker.patch('CyberArkEventCollector.send_events_to_xsiam')

    with requests_mock.Mocker() as m:
        m.get(f'{URL}oauth2/token/test_app', json={'access_token': '123456abc'})
        m.get(f'{URL}RedRock/Query', json={'Result': {}})

        from CyberArkEventCollector import main
        main('CyberArk-get-events', params.return_value)

    events = results.call_args[0][0]['Contents']
    assert last_run.return_value.get('from') == last_run.return_value.get('ids') == events is None


@freeze_time('2022-05-12T00:00:00Z')
def test_fetch_events_limit_set_to_one(mocker):
    """
    Given
        - 3 events was created in CyberArk side in the last 3 days.
    When
        - fetch-events is running (with limit set to 1).
    Then
        - Verify that only 1 event were created in XSIAM.
        - Verify last_run was set as expected.
    """

    params = mocker.patch.object(demisto, 'params', return_value=DEMISTO_PARAMS)
    params['limit'] = 1
    mocker.patch.object(demisto, 'args', return_value={})
    last_run = mocker.patch.object(demisto, 'getLastRun', return_value={})
    results = mocker.patch.object(demisto, 'results')
    mocker.patch('CyberArkEventCollector.send_events_to_xsiam')

    with requests_mock.Mocker() as m:
        m.get(f'{URL}oauth2/token/test_app', json={'access_token': '123456abc'})
        m.get(f'{URL}RedRock/Query', json=util_load_json('test_data/events.json'))

        from CyberArkEventCollector import main
        main('CyberArk-get-events', params.return_value)

    events = results.call_args[0][0]['Contents']
    assert last_run.return_value.get('from') == '2022-05-15T13:35:03.570000'
    assert len(last_run.return_value.get('ids')) == len(events) == 1
