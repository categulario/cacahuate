import xml.etree.ElementTree as ET
import os

from .context import *

def test_etree_from_list_empty():
    nodes = []
    etree = lib.xml.etree_from_list(ET.Element('process'), nodes)

    root = etree.getroot()
    assert root.tag == 'process'

    for elem, expct in zip(root.iter(), nodes):
        assert elem.tag == expct.tag
        assert elem.id == expct.id

def test_etree_from_list_withnodes():
    nodes = [
        ET.Element('foo', attrib={'a': 0}),
        ET.Element('var', attrib={'a': 1}),
        ET.Element('log', attrib={'a': 2}),
    ]
    nodes[2].append(ET.Element('sub'))

    etree = lib.xml.etree_from_list(ET.Element('process'), nodes)

    root = etree.getroot()
    assert root.tag == 'process'

    for i, (elem, expct) in enumerate(zip(root, nodes)):
        assert elem.tag == expct.tag
        assert elem.attrib['a'] == i

    ch = root[2][0]
    assert ch.tag == 'sub'

def test_nodes_from(config):
    xml = ET.parse(os.path.join(config['XML_PATH'], 'unsorted.xml'))

    start_node = list(xml.getroot())[10]

    assert start_node.attrib['id'] == 'B'

    given = list(lib.xml.nodes_from(start_node, xml.getroot()))
    expct = [
        (ET.Element('node', {'id':'D'}), ET.Element('connector', {'id':'B-D'})),
        (ET.Element('node', {'id':'C'}), ET.Element('connector', {'id':'B-C'})),
        (ET.Element('node', {'id':'E'}), ET.Element('connector', {'id':'B-E'})),
    ]

    assert len(given) == len(expct)

    for (node, edge), (expct_node, expct_edge) in zip(given, expct):
        assert node.attrib['id'] == expct_node.attrib['id']
        assert edge.attrib['id'] == expct_edge.attrib['id']

def test_has_no_incoming_sorted(config):
    xml = ET.parse(os.path.join(config['XML_PATH'], 'sorted.xml'))

    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'A'}), xml.getroot()) == True
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'B'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'C'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'D'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'E'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'F'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'G'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'H'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'I'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'J'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'K'}), xml.getroot()) == False

def test_has_no_incoming_unsorted(config):
    xml = ET.parse(os.path.join(config['XML_PATH'], 'unsorted.xml'))

    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'A'}), xml.getroot()) == True
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'B'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'C'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'D'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'E'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'F'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'G'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'H'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'I'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'J'}), xml.getroot()) == False
    assert lib.xml.has_no_incoming(ET.Element('node', {'id':'K'}), xml.getroot()) == False

def test_has_edges(config):
    sortedxml = ET.parse(os.path.join(config['XML_PATH'], 'sorted.xml'))
    unsorted = ET.parse(os.path.join(config['XML_PATH'], 'unsorted.xml'))
    no_edges = ET.parse(os.path.join(config['XML_PATH'], 'no_edges.xml'))

    assert lib.xml.has_edges(sortedxml) == True
    assert lib.xml.has_edges(unsorted) == True
    assert lib.xml.has_edges(no_edges) == False

def test_toposort(config):
    xml = ET.parse(os.path.join(config['XML_PATH'], 'unsorted.xml'))
    new_xml = lib.xml.topological_sort(xml.find(".//*[@id='A']"), xml.getroot())

    expct_tree = ET.parse(os.path.join(config['XML_PATH'], 'sorted.xml'))

    assert len(new_xml.getroot()) == len(expct_tree.getroot())
    assert len(new_xml.getroot()) == 21

    for elem, expct in zip(new_xml.iter(), expct_tree.iter()):
        assert elem.tag == expct.tag
        assert elem.attrib == expct.attrib
