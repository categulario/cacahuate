from flask import json
import pytest
import case_conversion
import pika
from base64 import b64encode

from pvm.models import Execution, Pointer, User, Token, Activity
from pvm.handler import Handler

def test_continue_process_requires(client):
    user = User(identifier='juan').save()
    token = Token(token='123456').save()
    token.proxy.user.set(user)

    res = client.post('/v1/pointer', headers={
        'Content-Type': 'application/json',
        'Authorization': 'Basic {}'.format(
            b64encode('{}:{}'.format(user.identifier, token.token).encode()).decode()
        ),
    }, data=json.dumps({}))

    assert res.status_code == 400
    assert json.loads(res.data) == {
        'errors': [
            {
                'detail': 'execution_id is required',
                'code': 'validation.required',
                'where': 'request.body.execution_id',
            },
            {
                'detail': 'node_id is required',
                'code': 'validation.required',
                'where': 'request.body.node_id',
            },
        ],
    }

def test_continue_process_asks_living_objects(client):
    ''' the app must validate that the ids sent are real objects '''
    res = client.post('/v1/pointer', headers={
        'Content-Type': 'application/json',
    }, data=json.dumps({
        'execution_id': 'verde',
        'node_id': 'nada',
    }))

    assert res.status_code == 400
    assert json.loads(res.data) == {
        'errors': [
            {
                'detail': 'execution_id is not valid',
                'code': 'validation.invalid',
                'where': 'request.body.execution_id',
            },
        ],
    }

def test_continue_process_requires_valid_node(client, models):
    exc = Execution(
        process_name = 'decision.2018-02-27',
    ).save()

    res = client.post('/v1/pointer', headers={
        'Content-Type': 'application/json',
    }, data=json.dumps({
        'execution_id': exc.id,
        'node_id': 'notarealnode',
    }))

    assert res.status_code == 400
    assert json.loads(res.data) == {
        'errors': [
            {
                'detail': 'node_id is not a valid node',
                'code': 'validation.invalid_node',
                'where': 'request.body.node_id',
            },
        ],
    }

def test_continue_process_requires_living_pointer(client, models):
    exc = Execution(
        process_name = 'decision.2018-02-27',
    ).save()

    res = client.post('/v1/pointer', headers={
        'Content-Type': 'application/json',
    }, data=json.dumps({
        'execution_id': exc.id,
        'node_id': '57TJ0V3nur6m7wvv',
    }))

    assert res.status_code == 400
    assert json.loads(res.data) == {
        'errors': [
            {
                'detail': 'node_id does not have a live pointer',
                'code': 'validation.no_live_pointer',
                'where': 'request.body.node_id',
            },
        ],
    }

def test_continue_process_asks_for_user(client, models):
    exc = Execution(
        process_name = 'exit_request.2018-03-20.xml',
    ).save()
    ptr = Pointer(
        node_id = 'manager-node',
    ).save()
    ptr.proxy.execution.set(exc)

    res = client.post('/v1/pointer', headers={
        'Content-Type': 'application/json',
    }, data=json.dumps({
        'execution_id': exc.id,
        'node_id': ptr.node_id,
    }))

    assert res.status_code == 401
    assert 'WWW-Authenticate' in res.headers
    assert res.headers['WWW-Authenticate'] == 'Basic realm="User Visible Realm"'
    assert json.loads(res.data) == {
        'errors': [{
            'detail': 'You must provide basic authorization headers',
            'where': 'request.authorization',
        }],
    }

def test_continue_process_asks_for_data(client, models):
    user = User(identifier='juan').save()
    token = Token(token='123456').save()
    token.proxy.user.set(user)
    exc = Execution(
        process_name = 'exit_request.2018-03-20.xml',
    ).save()
    ptr = Pointer(
        node_id = 'manager-node',
    ).save()
    ptr.proxy.execution.set(exc)

    res = client.post('/v1/pointer', headers={
        'Content-Type': 'application/json',
        'Authorization': 'Basic {}'.format(
            b64encode('{}:{}'.format(user.identifier, token.token).encode()).decode()
        ),
    }, data=json.dumps({
        'execution_id': exc.id,
        'node_id': ptr.node_id,
    }))

    assert res.status_code == 400
    assert json.loads(res.data) == {
        'errors': [{
            'detail': "'auth' input is required",
            'where': 'request.body.form_array.0.auth',
            'code': 'validation.required',
        }],
    }

def test_can_continue_process(client, models, mocker, config):
    mocker.patch('pika.adapters.blocking_connection.BlockingChannel.basic_publish')

    user = User(identifier='juan').save()
    token = Token(token='123456').save()
    token.proxy.user.set(user)
    exc = Execution(
        process_name = 'exit_request.2018-03-20.xml',
    ).save()
    ptr = Pointer(
        node_id = 'manager-node',
    ).save()
    ptr.proxy.execution.set(exc)

    res = client.post('/v1/pointer', headers={
        'Content-Type': 'application/json',
        'Authorization': 'Basic {}'.format(
            b64encode('{}:{}'.format(user.identifier, token.token).encode()).decode()
        ),
    }, data=json.dumps({
        'execution_id': exc.id,
        'node_id': ptr.node_id,
        'form_array': [
            {
                'ref': '#auth-form',
                'data': {
                    'auth': 'yes',
                },
            },
        ],
    }))

    assert res.status_code == 202
    assert json.loads(res.data) == {
        'data': 'accepted',
    }

    # user is attached
    actors = exc.proxy.actors.get()

    assert len(actors) == 1

    activity = actors[0]

    assert activity.ref == '#manager'
    assert activity.proxy.user.get() == user

    # form is attached
    forms = exc.proxy.forms.get()

    assert len(forms) == 1

    form = forms[0]

    assert form.ref == '#auth-form'
    assert form.data == {
        'auth': 'yes',
    }

    # rabbit is called
    pika.adapters.blocking_connection.BlockingChannel.basic_publish.assert_called_once()

    args =  pika.adapters.blocking_connection.BlockingChannel.basic_publish.call_args[1]

    json_message = {
        'command': 'step',
        'process': exc.process_name,
        'pointer_id': ptr.id,
    }

    assert args['exchange'] == ''
    assert args['routing_key'] == config['RABBIT_QUEUE']
    assert json.loads(args['body']) == json_message

    handler = Handler(config)

    execution, pointer, xmliter, current_node = handler.recover_step(json_message)

    assert execution.id == exc.id
    assert pointer.id == ptr.id

@pytest.mark.skip
def test_can_query_process_status(client):
    res = client.get('/v1/node/{}')

    assert res.status_code == 200
    assert res.data == {
        'data': [
            {
                '_type': 'node',
                'id': '',
                'data': {},
            },
        ]
    }

@pytest.mark.skip
def test_can_list_activities_for_user():
    assert False, 'can list them'

def test_process_start_simple_requires(client, models):
    # we need the name of the process to start
    res = client.post('/v1/execution', headers={
        'Content-Type': 'application/json',
    }, data='{}')

    assert res.status_code == 400
    assert json.loads(res.data) == {
        'errors': [
            {
                'detail': 'process_name is required',
                'where': 'request.body.process_name',
                'code': 'validation.required',
            },
        ],
    }

    # we need an existing process to start
    res = client.post('/v1/execution', headers={
        'Content-Type': 'application/json',
    }, data=json.dumps({
        'process_name': 'foo',
    }))

    assert res.status_code == 404
    assert json.loads(res.data) == {
        'errors': [
            {
                'detail': 'foo process does not exist',
                'where': 'request.body.process_name',
            },
        ],
    }

    # we need a process with a start node
    res = client.post('/v1/execution', headers={
        'Content-Type': 'application/json',
    }, data=json.dumps({
        'process_name': 'nostart',
    }))

    assert res.status_code == 422
    assert json.loads(res.data) == {
        'errors': [
            {
                'detail': 'nostart process does not have a start node, thus cannot be started',
                'where': 'request.body.process_name',
            },
        ],
    }

def test_process_start_simple(client, models, mocker, config):
    mocker.patch('pika.adapters.blocking_connection.BlockingChannel.basic_publish')

    res = client.post('/v1/execution', headers={
        'Content-Type': 'application/json',
    }, data=json.dumps({
        'process_name': 'simple',
    }))

    assert res.status_code == 201

    exc = Execution.get_all()[0]

    assert exc.process_name == 'simple.2018-02-19.xml'

    ptr = exc.proxy.pointers.get()[0]

    assert ptr.node_id == 'gYcj0XjbgjSO'

    pika.adapters.blocking_connection.BlockingChannel.basic_publish.assert_called_once()

    args =  pika.adapters.blocking_connection.BlockingChannel.basic_publish.call_args[1]

    json_message = {
        'command': 'step',
        'process': exc.process_name,
        'pointer_id': ptr.id,
    }

    assert args['exchange'] == ''
    assert args['routing_key'] == config['RABBIT_QUEUE']
    assert json.loads(args['body']) == json_message

    handler = Handler(config)

    execution, pointer, xmliter, current_node = handler.recover_step(json_message)

    assert execution.id == exc.id
    assert pointer.id == ptr.id

def test_exit_request_requirements(client, models):
    # first requirement is to have authentication
    res = client.post('/v1/execution', headers={
        'Content-Type': 'application/json',
    }, data=json.dumps({
        'process_name': 'exit_request',
    }))

    assert res.status_code == 401
    assert 'WWW-Authenticate' in res.headers
    assert res.headers['WWW-Authenticate'] == 'Basic realm="User Visible Realm"'
    assert json.loads(res.data) == {
        'errors': [{
            'detail': 'You must provide basic authorization headers',
            'where': 'request.authorization',
        }],
    }

    assert Execution.count() == 0
    assert Activity.count() == 0

    # next, validate the form data
    user = User(identifier='juan').save()
    token = Token(token='123456').save()
    token.proxy.user.set(user)

    res = client.post('/v1/execution', headers={
        'Content-Type': 'application/json',
        'Authorization': 'Basic {}'.format(
            b64encode('{}:{}'.format(user.identifier, token.token).encode()).decode()
        ),
    }, data=json.dumps({
        'process_name': 'exit_request',
    }))

    assert res.status_code == 400
    assert json.loads(res.data) == {
        'errors': [{
            'detail': "'reason' input is required",
            'where': 'request.body.form_array.0.reason',
            'code': 'validation.required',
        }],
    }

    assert Execution.count() == 0
    assert Activity.count() == 0

def test_exit_request_start(client, models, mocker):
    user = User(identifier='juan').save()
    token = Token(token='123456').save()
    token.proxy.user.set(user)

    assert Execution.count() == 0
    assert Activity.count() == 0

    res = client.post('/v1/execution', headers={
        'Content-Type': 'application/json',
        'Authorization': 'Basic {}'.format(
            b64encode('{}:{}'.format(user.identifier, token.token).encode()).decode()
        ),
    }, data=json.dumps({
        'process_name': 'exit_request',
        'form_array': [
            {
                'ref': '#exit-form',
                'data': {
                    'reason': 'tenía que salir al baño',
                },
            },
        ],
    }))

    assert res.status_code == 201

    exc = Execution.get_all()[0]

    assert json.loads(res.data) == {
        'data': exc.to_json(),
    }

    # user is attached
    actors = exc.proxy.actors.get()

    assert len(actors) == 1

    activity = actors[0]

    assert activity.ref == '#requester'
    assert activity.proxy.user.get() == user

    # form is attached
    forms = exc.proxy.forms.get()

    assert len(forms) == 1

    form = forms[0]

    assert form.ref == '#exit-form'
    assert form.data == {
        'reason': 'tenía que salir al baño',
    }
