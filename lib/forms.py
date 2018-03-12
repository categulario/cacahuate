from coralillo import Form, fields, errors
from coralillo.validation import validation_rule

from .errors import ElementNotFound, NoPointerAlive


class ContinueProcess(Form):
    execution_id = fields.Text()
    node_id      = fields.Text()

    @validation_rule
    def custom_validations(obj):
        ''' Ensures that execution_id points to a currently running execution,
        that node_id is a real node from the same process file as the provided
        execution and that a pointer pointing to that node belonging to the
        given execution exists '''
        # validates the existence of the execution
        if not obj.execution_id or not obj.node_id:
            return # previous validation didn't pass

        from .models import Execution

        execution = Execution.get(obj.execution_id)

        if execution is None:
            raise errors.InvalidFieldError(field='execution_id')

        # validates the existence of the node
        from .process import load, iter_nodes, find
        from pvm_api import app

        name, xmlfile = load(app.config, execution.process_name)
        xmliter = iter_nodes(xmlfile)

        def testfunc(e):
            return 'id' in e.attrib and e.attrib['id'] == obj.node_id

        try:
            find(xmliter, testfunc)
        except ElementNotFound:
            raise errors.InvalidFieldError(field='node_id')

        # validates the existence of a pointer asociated to the node and execution
        ptrs = execution.proxy.pointers.get()

        for ptr in ptrs:
            if ptr.node_id == obj.node_id:
                break
        else:
            raise NoPointerAlive(field='node_id')

        obj.execution = execution
        obj.pointer = pointer


def bind_forms(engine):
    ContinueProcess.set_engine(engine)