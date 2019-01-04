import itertools
import string

import attr
import graham
import marshmallow
import PyQt5.QtCore

import epyqlib.attrsmodel
import epyqlib.pm.parametermodel
import epyqlib.treenode
import epyqlib.utils.general
import epyqlib.utils.qt

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


class ConsistencyError(Exception):
    pass


def based_int(v):
    if isinstance(v, str):
        return int(v, 0)

    return int(v)


def hex_upper(_, value, width=8, prefix='0x', model=None):
    return f'{prefix}{value:0{width}X}'


class HexadecimalIntegerField(marshmallow.fields.Field):
    def _serialize(self, value, attr, obj):
        if self.allow_none and value is None:
            return None

        return hex(value)

    def _deserialize(self, value, attr, data):
        if self.allow_none and value is None:
            return None

        return int(value, 0)


@staticmethod
def child_from(node):
    if isinstance(node, epyqlib.pm.parametermodel.Parameter):
        return Signal(name=node.name, parameter_uuid=node.uuid)

    if isinstance(node, epyqlib.pm.parametermodel.Table):
        return CanTable(table_uuid=node.uuid)


@graham.schemify(tag='signal')
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Signal(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Signal',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    bits = attr.ib(
        default=0,
        converter=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    )
    signed = attr.ib(
        default=False,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    factor = attr.ib(
        default=1,
        converter=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(as_string=True),
        ),
    )
    start_bit = attr.ib(
        default=0,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    )

    parameter_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=parameter_uuid,
        human_name='Parameter UUID',
    )

    enumeration_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=enumeration_uuid,
        human_name='Enumeration',
        data_display=epyqlib.attrsmodel.name_from_uuid,
        delegate=epyqlib.attrsmodel.SingleSelectByRootDelegateCache(
            list_selection_root='enumerations',
        )
    )

    path = attr.ib(
        factory=tuple,
    )
    epyqlib.attrsmodel.attrib(
        attribute=path,
        no_column=True,
    )
    graham.attrib(
        attribute=path,
        field=graham.fields.Tuple(marshmallow.fields.UUID()),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return False

    can_delete = epyqlib.attrsmodel.childless_can_delete

    def calculated_min_max(self):
        bits = self.bits

        if self.signed:
            bits -= 1

        r = 2 ** bits

        if self.signed:
            minimum = -r
            maximum = r - 1
        else:
            minimum = 0
            maximum = r - 1

        minimum *= self.factor
        maximum *= self.factor

        return minimum, maximum


@graham.schemify(tag='message')
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Message(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Message',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )

    identifier = attr.ib(
        default=0x1fffffff,
        convert=based_int,
        metadata=graham.create_metadata(
            field=HexadecimalIntegerField(),
        ),
    )
    epyqlib.attrsmodel.attrib(
        data_display=hex_upper,
        attribute=identifier,
    )

    extended = attr.ib(
        default=True,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    length = attr.ib(
        default=0,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Int(),
        ),
    )
    cycle_time = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(allow_none=True, as_string=True),
        ),
    )
    sendable = attr.ib(
        default=True,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    receivable = attr.ib(
        default=True,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    comment = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(Signal)),
            )),
        ),
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    child_from = child_from

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types((Signal,))

    def addable_types(self):
        return {}

    def can_drop_on(self, node):
        return isinstance(node, epyqlib.pm.parametermodel.Parameter)

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True


@graham.schemify(tag='multiplexer')
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Multiplexer(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Multiplexer',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    identifier = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_int_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(allow_none=True),
        )
    )
    length = attr.ib(
        default=0,
        convert=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Int(),
        ),
    )
    cycle_time = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(allow_none=True, as_string=True),
        ),
    )
    comment = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(Signal)),
            )),
        ),
    )

    path = attr.ib(
        factory=tuple,
    )
    epyqlib.attrsmodel.attrib(
        attribute=path,
        no_column=True,
    )
    graham.attrib(
        attribute=path,
        field=graham.fields.Tuple(marshmallow.fields.UUID()),
    )

    path_children = attr.ib(
        factory=tuple,
    )
    epyqlib.attrsmodel.attrib(
        attribute=path_children,
        no_column=True,
    )
    graham.attrib(
        attribute=path_children,
        field=graham.fields.Tuple(marshmallow.fields.UUID()),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    child_from = child_from

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types((Signal,))

    def addable_types(self):
        return {}

    def can_drop_on(self, node):
        return isinstance(
            node,
            (
                epyqlib.pm.parametermodel.Parameter,
                Signal,
            ),
        )

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True


@graham.schemify(tag='multiplexed_message')
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class MultiplexedMessage(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Multiplexed Message',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )

    identifier = attr.ib(
        default=0x1fffffff,
        convert=based_int,
        metadata=graham.create_metadata(
            field=HexadecimalIntegerField(),
        ),
    )
    epyqlib.attrsmodel.attrib(
        data_display=hex_upper,
        attribute=identifier,
    )

    extended = attr.ib(
        default=True,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    length = attr.ib(
        default=0,
        convert=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    )
    sendable = attr.ib(
        default=True,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    receivable = attr.ib(
        default=True,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    comment = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(Signal)),
                marshmallow.fields.Nested(graham.schema(Multiplexer)),
                marshmallow.fields.Nested('CanTable'),
            )),
        ),
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    child_from = child_from

    def can_drop_on(self, node):
        return isinstance(
            node,
            (
                *self.addable_types().values(),
                epyqlib.pm.parametermodel.Table,
            ),
        )

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types(
            (
                Signal,
                Multiplexer,
                CanTable,
            ),
        )

    def addable_types(self):
        types = (Signal,)

        if len(self.children) > 0:
            types += (Multiplexer, CanTable)

        return epyqlib.attrsmodel.create_addable_types(types)


@graham.schemify(tag='table', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class CanTable(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Table',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    multiplexer_range_first = attr.ib(
        default=0,
        convert=based_int,
        metadata=graham.create_metadata(
            field=HexadecimalIntegerField(),
        ),
    )
    multiplexer_range_last = attr.ib(
        default=0x100,
        convert=based_int,
        metadata=graham.create_metadata(
            field=HexadecimalIntegerField(),
        ),
    )

    table_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=table_uuid,
        human_name='Table UUID',
    )

    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(Multiplexer)),
                marshmallow.fields.Nested(graham.schema(Signal)),
            )),
        ),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types(())

    def addable_types(self):
        return {}

    def can_drop_on(self, node):
        return isinstance(node, epyqlib.pm.parametermodel.Table)

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True

    def update(self, table=None):
        array_uuid_to_signal = {
            child.parameter_uuid: child
            for child in self.children
            if isinstance(child, Signal)
        }

        for signal in array_uuid_to_signal.values():
            self.remove_child(child=signal)

        nodes = self.recursively_remove_children()

        if self.table_uuid is None:
            return

        root = self.find_root()
        model = root.model

        if table is None:
            table = model.node_from_uuid(self.table_uuid)
        elif table.uuid != self.table_uuid:
            raise ConsistencyError()

        old_by_path = {}
        for node in nodes:
            if isinstance(node, Multiplexer):
                path = (*node.path, node.path_children)
            else:
                path = node.path
            old_by_path[path] = node

        arrays = [
            child
            for child in table.children
            if isinstance(child, epyqlib.pm.parametermodel.Array)
        ]

        groups = [
            child
            for child in table.children
            if isinstance(child, epyqlib.pm.parametermodel.Group)
        ]

        for array in arrays:
            signal = array_uuid_to_signal.get(array.uuid)

            if signal is None:
                signal = Signal(
                    name=array.name,
                    parameter_uuid=array.uuid,
                )
                array_uuid_to_signal[array.uuid] = signal

            self.append_child(signal)

        for group in groups:
            for parameter in group.children:
                signal = array_uuid_to_signal.get(parameter.uuid)

                if signal is None:
                    signal = Signal(
                        name=parameter.name,
                        parameter_uuid=parameter.uuid,
                    )
                    array_uuid_to_signal[parameter.uuid] = signal

                self.append_child(signal)

        # TODO: backmatching
        def my_sorted(sequence, order):
            s = sequence
            for o, r in reversed(order):
                d = {c: i for i, c in enumerate(r)}
                s = sorted(s, key=lambda x: d[model.node_from_uuid(x.path[o]).name])

            return s

        # TODO: backmatching
        leaves = table.group.leaves()
        if table.name == 'Frequency':
            leaves = my_sorted(
                leaves,
                (
                    (1, ('RideThrough', 'Trip')),
                    (0, ('Low', 'High')),
                    (2, ('0', '1', '2', '3')),
                    (3, ('seconds', 'hertz')),
                ),
            )
        elif table.name == 'Voltage':
            leaves = my_sorted(
                leaves,
                (
                    (1, ('RideThrough', 'Trip')),
                    (0, ('Low', 'High')),
                    (2, ('0', '1', '2', '3')),
                    (3, ('seconds', 'percent')),
                ),
            )
        elif table.name == 'VoltVar':
            leaves = my_sorted(
                leaves,
                (
                    (0, ('0', '1', '2', '3')),
                    (1, ('Settings', 'percent_nominal_volts',
                         'percent_nominal_var')),
                ),
            )
        elif table.name == 'HertzWatts':
            leaves = my_sorted(
                leaves,
                (
                    (0, ('0', '1', '2', '3')),
                    (1, ('Settings', 'hertz', 'percent_nominal_pwr')),
                ),
            )
        elif table.name == 'HertzWatts':
            leaves = my_sorted(
                leaves,
                (
                    (0, ('0', '1', '2', '3')),
                    (1, ('Settings', 'percent_nominal_volts', 'percent_nominal_pwr')),
                ),
            )

        # TODO: this is arrays and groups...
        leaf_groups = [
            list(group[1])
            for group in itertools.groupby(
                leaves,
                key=lambda leaf: leaf.path[:-1],
            )
        ]

        mux_value = self.multiplexer_range_first

        for leaf_group in leaf_groups:
            is_group = False
            type_reference = leaf_group[0].original.tree_parent
            if isinstance(type_reference, epyqlib.pm.parametermodel.Array):
                signal = array_uuid_to_signal[leaf_group[0].path[-2]]
            elif isinstance(type_reference, epyqlib.pm.parametermodel.Group):
                signal = array_uuid_to_signal[leaf_group[0].path[-1]]
                is_group = True
            else:
                raise ConsistencyError()

            if signal.bits == 0:
                continue

            if not is_group:
                # TODO: actually calculate space to use
                per_message = int(48 / signal.bits)
            else:
                # TODO: yeah...
                per_message = 9999

            chunks = list(
                epyqlib.utils.general.chunker(leaf_group, n=per_message),
            )
            for chunk, letter in zip(chunks, string.ascii_uppercase):
                path = chunk[0].path

                path_nodes = [model.node_from_uuid(u) for u in path]

                enumerators = []
                other = []
                for node in path_nodes[:-1]:
                    if len(other) > 0:
                        other.append(node.name)
                        continue

                    # TODO: backmatching
                    if node.tree_parent.name != 'Curves' and isinstance(node, epyqlib.pm.parametermodel.Enumerator):
                        enumerators.append(node.name)
                        continue

                    other.append(node.name)

                path_string = '_'.join([
                    ''.join(name for name in enumerators),
                    *other,
                    *([letter] if len(chunks) > 1 else []),
                ])
                multiplexer_path = chunk[0].path[:-1]
                multiplexer_path_children = tuple(
                    element.path[-1]
                    for element in chunk
                )
                multiplexer = old_by_path.get(
                    (*multiplexer_path, multiplexer_path_children)
                )
                if multiplexer is None:
                    multiplexer = Multiplexer(
                        name=path_string,
                        identifier=mux_value,
                        path=multiplexer_path,
                        path_children=multiplexer_path_children,
                    )
                mux_value += 1

                # TODO: backmatching
                if not is_group:
                    start_bit = 64 - per_message * signal.bits
                    if signal.name == 'Settings':
                        start_bit = 64 - len(chunk) * signal.bits
                else:
                    total_bits = sum(
                        array_uuid_to_signal[element.path[-1]].bits
                        for element in chunk
                    )
                    start_bit = 64 - total_bits

                for array_element in chunk:
                    if is_group:
                        reference_signal = array_uuid_to_signal[array_element.path[-1]]
                    else:
                        reference_signal = signal
                    signal_path = array_element.path

                    new_signal = old_by_path.get(signal_path)
                    if new_signal is None:
                        new_signal = Signal(
                            name=array_element.name,
                            # TODO: backmatching
                            start_bit=start_bit if array_element.name != 'YScale' else 16,
                            bits=reference_signal.bits,
                            factor=reference_signal.factor,
                            signed=reference_signal.signed,
                            enumeration_uuid=reference_signal.enumeration_uuid,
                            parameter_uuid=array_element.uuid,
                            path=signal_path,
                        )
                    multiplexer.append_child(new_signal)
                    start_bit += new_signal.bits

                self.append_child(multiplexer)


Root = epyqlib.attrsmodel.Root(
    default_name='CAN',
    valid_types=(Message, MultiplexedMessage, CanTable),
)

types = epyqlib.attrsmodel.Types(
    types=(Root, Message, Signal, MultiplexedMessage, Multiplexer, CanTable),
)


# TODO: CAMPid 943896754217967154269254167
def merge(name, *types):
    return tuple((x, name) for x in types)


columns = epyqlib.attrsmodel.columns(
    merge('name', *types.types.values()),
    merge('identifier', Message, MultiplexedMessage, Multiplexer),
    merge('multiplexer_range_first', CanTable),
    merge('multiplexer_range_last', CanTable),
    (
        merge('length', Message, Multiplexer, MultiplexedMessage)
        + merge('bits', Signal)
    ),
    merge('extended', Message, MultiplexedMessage),

    merge('enumeration_uuid', Signal),

    merge('cycle_time', Message, Multiplexer),

    merge('table_uuid', CanTable),

    merge('signed', Signal),
    merge('factor', Signal),

    merge('sendable', Message, MultiplexedMessage),
    merge('receivable', Message, MultiplexedMessage),
    merge('start_bit', Signal),
    merge('comment', Message, Multiplexer, MultiplexedMessage),


    merge('parameter_uuid', Signal),
    merge('uuid', *types.types.values()),
)


# TODO: CAMPid 075454679961754906124539691347967
@attr.s
class ReferencedUuidNotifier(PyQt5.QtCore.QObject):
    changed = PyQt5.QtCore.pyqtSignal('PyQt_PyObject')

    view = attr.ib(default=None)
    selection_model = attr.ib(default=None)

    def __attrs_post_init__(self):
        super().__init__()

        if self.view is not None:
            self.set_view(self.view)

    def set_view(self, view):
        self.disconnect_view()

        self.view = view
        self.selection_model = self.view.selectionModel()
        self.selection_model.currentChanged.connect(
            self.current_changed,
        )

    def disconnect_view(self):
        if self.selection_model is not None:
            self.selection_model.currentChanged.disconnect(
                self.current_changed,
            )
        self.view = None
        self.selection_model = None

    def current_changed(self, current, previous):
        if not current.isValid():
            return

        index = epyqlib.utils.qt.resolve_index_to_model(
            index=current,
        )
        model = index.data(epyqlib.utils.qt.UserRoles.attrs_model)
        node = model.node_from_index(index)
        if isinstance(node, Signal):
            self.changed.emit(node.parameter_uuid)
