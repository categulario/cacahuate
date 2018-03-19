from flask import json
import pytest
import case_conversion
import pika

from pvm.models import Execution, Pointer

def test_continue_process_requires(client):
    res = client.post('/v1/pointer')

    assert res.status_code == 400
    assert json.loads(res.data) == {
        'errors': [
            {
                'detail': 'execution_id is required',
                'i18n': 'errors.execution_id.required',
                'field': 'execution_id',
            },
            {
                'detail': 'node_id is required',
                'i18n': 'errors.node_id.required',
                'field': 'node_id',
            },
        ],
    }

def test_continue_process_asks_living_objects(client):
    ''' the app must validate that the ids sent are real objects '''
    res = client.post('/v1/pointer', data={
        'execution_id': 'verde',
        'node_id': 'nada',
    })

    assert res.status_code == 400
    assert json.loads(res.data) == {
        'errors': [
            {
                'detail': 'execution_id is not valid',
                'i18n': 'errors.execution_id.invalid',
                'field': 'execution_id',
            },
        ],
    }

def test_continue_process_requires_living_pointer(client):
    exc = Execution(
        process_name = 'decision_2018-02-27',
    ).save()
    res = client.post('/v1/pointer', data={
        'execution_id': exc.id,
        'node_id': '57TJ0V3nur6m7wvv',
    })

    assert res.status_code == 400
    assert json.loads(res.data) == {
        'errors': [
            {
                'detail': 'node_id does not have a live pointer',
                'i18n': 'errors.node_id.no_live_pointer',
                'field': 'node_id',
            },
        ],
    }

def test_can_continue_process(client, models, mocker):
    exc = Execution(
        process_name = 'decision_2018-02-27',
    ).save()
    ptr = Pointer(node_id='57TJ0V3nur6m7wvv').save()
    ptr.proxy.execution.set(exc)

    mocker.patch('pika.adapters.blocking_connection.BlockingChannel.basic_publish')

    res = client.post('/v1/pointer', data={
        'execution_id': exc.id,
        'node_id': '57TJ0V3nur6m7wvv',
    })

    pika.adapters.blocking_connection.BlockingChannel.basic_publish.assert_called_once()

    assert res.status_code == 202
    assert json.loads(res.data) == {
        'data': {
            'detail': 'accepted',
        },
    }


@pytest.mark.skip(reason='not implemented yet')
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

@pytest.mark.skip(reason='not implemented yet')
def test_execution_start(client, models):
    assert Execution.count() == 0
    assert Pointer.count() == 0

    res = client.post('/v1/execution')

    assert res.status_code == 201
    assert res.json() == {
        'data': {
            '_type': 'execution',
            'id': '',
            'process_name': 'simple',
        },
    }

    assert Execution.count() == 1
    assert Pointer.count() == 1
