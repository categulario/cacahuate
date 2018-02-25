import xml.etree.ElementTree as ET
import pytest

from .context import *


def test_parse_message(config):
    handler = lib.handler.Handler(config)

    with pytest.raises(ValueError):
        handler.parse_message('not json')

    with pytest.raises(KeyError):
        handler.parse_message('{"foo":1}')

    with pytest.raises(ValueError):
        handler.parse_message('{"command":"foo"}')

    msg = handler.parse_message('{"command":"start"}')

    assert msg == {
        'command': 'start',
    }

def test_get_start_node(config, models):
    handler = lib.handler.Handler(config)

    execution, pointer, xmliter, start_node = handler.get_start({
        'process': 'simple',
    })

    conn = next(xmliter)

    assert conn.tag == 'connector'

    assert start_node is not None
    assert isinstance(start_node, lib.node.Node)
    assert isinstance(start_node, lib.node.StartNode)

    assert execution.proxy.pointers.count() == 1
    assert pointer in execution.proxy.pointers

def test_recover_step(config, models):
    handler = lib.handler.Handler(config)
    exc = lib.models.Execution.validate(
        process_name = 'simple_2018-02-19.xml',
    ).save()
    ptr = lib.models.Pointer.validate(
        node_id = '4g9lOdPKmRUf',
    ).save()
    ptr.proxy.execution.set(exc)

    execution, pointer, xmliter, node = handler.recover_step({
        'command': 'continue',
        'pointer_id': ptr.id,
    })

    assert execution.id == exc.id
    assert pointer.id == pointer.id
    assert pointer in execution.proxy.pointers

    conn = next(xmliter)
    assert conn.tag == 'connector'
    assert conn.attrib == {'from':"4g9lOdPKmRUf", 'to':"kV9UWSeA89IZ"}

    assert node.id == '4g9lOdPKmRUf'

def test_create_pointer():
    handler = lib.handler.Handler(config)

    ele = ET.Element('node', {
        'class': 'dummy',
        'id': 'chubaca',
    })
    node = lib.node.make_node(ele)
    execution = lib.models.Execution().save()
    exct_id = handler.create_pointer(node, execution)

    exct = lib.models.Execution.get(exct_id)

    assert exct.process_name == 'simple_2018-02-19'
    assert type(exct.pointers) == set
    assert len(exct.pointers) == 1
    assert type(exct.docs) == set
    assert len(exct.docs) == 0
    assert exct.pointers[0].node_id == 'chubaca'

def test_delete_pointer():
    handler = lib.handler.Handler(config)

    step = handler.recover_step()

    assert step is not None
    assert isinstance(step, lib.node.Node)

def test_call_start():
    assert False, 'execution and pointer were created'

def test_call_recover():
    assert False, 'old pointer deleted, new one created'
    assert False, 'execution remains valid, with one pointer'

def test_call_recover_end():
    assert False, 'no pointers left'
    assert False, 'execution is deleted'
