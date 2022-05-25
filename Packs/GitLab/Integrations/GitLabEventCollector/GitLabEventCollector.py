from CommonServerPython import *  # noqa # pylint: disable=unused-wildcard-import
from SiemApiModule import *  # noqa # pylint: disable=unused-wildcard-import


class Client(IntegrationEventsClient):

    def __init__(self, request: IntegrationHTTPRequest, options: IntegrationOptions, last_run: str):  # pragma: no cover
        super().__init__(request=request, options=options)
        self.last_run = last_run
        self.page = 1
        self.event_type = ''

    def set_request_filter(self, after: Any):  # pragma: no cover
        self.page += 1

    def prepare_request(self):
        self.request.url = f'{self.request.url.split("?")[0]}?created_after={self.last_run}&per_page=100&page={self.page}'


class GetEvents(IntegrationGetEvents):
    @staticmethod
    def get_last_run(events: list) -> dict:
        groups = [event for event in events if event['entity_type'] == 'Group']
        groups.sort(key=lambda k: k.get('id'))
        projects = [event for event in events if event['entity_type'] == 'Project']
        projects.sort(key=lambda k: k.get('id'))

        return {'groups': groups[-1]['created_at'], 'projects': projects[-1]['created_at']}

    def _iter_events(self):  # pragma: no cover
        self.client.prepare_request()
        response = self.call()
        events: list = response.json()
        events.sort(key=lambda k: k.get('created_at'))
        if not events:
            return []

        while True:
            yield events

            last = events[-1]
            self.client.set_request_filter(last['created_at'])
            self.client.prepare_request()
            response = self.call()
            events = response.json()
            events.sort(key=lambda k: k.get('created_at'))
            if not events:
                break


def main() -> None:  # pragma: no cover
    demisto_params = demisto.params()
    url = urljoin(demisto_params['url'], '/api/v4/')
    events_collection_management = {
        'groups_ids': argToList(demisto_params.get('group_ids', '')),
        'projects_ids': argToList(demisto_params.get('project_ids', '')),
        'event_types': ['groups', 'projects']
    }

    headers = {'PRIVATE-TOKEN': demisto_params.get('api_key', {}).get('credentials', {}).get('password')}
    request_object = {
        'method': Method.GET,
        'url': url,
        'headers': headers,
    }
    last_run = demisto.getLastRun()
    if ('groups', 'projects') not in last_run:
        last_run = dateparser.parse(demisto_params['after'].strip()).isoformat()
        last_run = {
            'groups': last_run,
            'projects': last_run,
        }
    else:
        last_run = last_run

    options = IntegrationOptions.parse_obj(demisto_params)

    request = IntegrationHTTPRequest(**request_object)

    client = Client(request, options, last_run)

    get_events = GetEvents(client, options)

    command = demisto.command()
    try:
        events = []
        for event_type in events_collection_management['event_types']:
            for obj_id in events_collection_management[f'{event_type}_ids']:
                call_url_suffix = f'{event_type}/{obj_id}/audit_events'
                get_events.client.request.url = url + call_url_suffix
                get_events.client.page = 1
                get_events.client.event_type = event_type
                events.extend(get_events.run())
        if command == 'test-module':
            return_results('ok')
            return
        if command == 'gitlab-get-events':
            command_results = CommandResults(
                readable_output=tableToMarkdown('gitlab Logs', events, headerTransform=pascalToSpace),
                raw_response=events,
            )
            return_results(command_results)
        elif command == 'fetch-events':
            demisto.setLastRun(get_events.get_last_run(events))
            demisto_params['push_events'] = True
        if demisto_params.get('push_events'):
            send_events_to_xsiam(events, demisto_params.get('vendor', 'gitlab'),
                                 demisto_params.get('product', 'gitlab'))
        else:
            return_error(f'Command not found: {command}')
    except Exception as exc:
        raise exc
        return_error(f'Failed to execute {command} command.\nError:\n{str(exc)}', error=exc)


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
