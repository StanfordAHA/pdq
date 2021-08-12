from typing import List, Mapping, Tuple, Union

import magma as m


FlatBiMap = List[Tuple[str, str]]
CktRefType = Union[m.circuit.CircuitKind, m.Circuit]  # defn/decl or inst


def _collect_instances(
        curr_path: List[CktRefType],
        ckt: m.circuit.CircuitKind,
        top: bool,
        instances: List[List[CktRefType]]):
    path = curr_path.copy()
    if top:
        path += [ckt]
    for inst in ckt.instances:
        new_path = path + [inst]
        instances.append(new_path)
        _collect_instances(new_path, type(inst), False, instances)


def _collect_modules(
        instances: List[List[CktRefType]]) -> List[m.circuit.CircuitKind]:
    # NOTE(rsetaluri): We use an insertion ordered dict (default python dict) to
    # emulate an ordered set.
    modules = {}
    for path in instances:
        tail = path[-1]
        assert isinstance(tail, m.Circuit)
        ckt = type(tail)
        modules[ckt] = None
    return list(modules.keys())


def _get_leaves_of_port(value, path=None):
    if path is None:
        path = ""
    if isinstance(value, (m.Digital, m.Bits)):
        yield path
        return
    if m.verilog_utils.is_nd_array(type(value)):
        yield path
        return
    if isinstance(value, m.Array):
        for i, elem in enumerate(value):
            yield from _get_leaves_of_port(elem, f"{path}[{i}]")
        return
    if isinstance(value, m.Tuple):
        for field_name, field_type in type(value).field_dict.items():
            yield from _get_leaves_of_port(getattr(value, field_name), f"{path}.{field_name}")
        return
    raise NotImplementedError(value)
    

def expand_symbol_table(
        ckt: m.circuit.CircuitKind,
        table: m.symbol_table.SymbolTableInterface) -> (
            FlatBiMap, Mapping[m.circuit.CircuitKind, FlatBiMap]):
    query_ifc = m.symbol_table_utils.SymbolQueryInterface(table)

    # Expand instances.
    instances = []
    _collect_instances([], ckt, True, instances)
    inst_info = []
    for path in instances:
        path_as_names = map(lambda i: i.name, path)
        flattened_path = ".".join(path_as_names)
        mapped = query_ifc.get_instance_name(flattened_path)
        inst_info.append((flattened_path, mapped))

    # Expand ports.
    modules = _collect_modules(instances)
    port_info = {}
    for module in modules:
        info = []
        for port_name, port in module.interface.ports.items():
            leaves = _get_leaves_of_port(port)
            for leaf in leaves:
                flattened_port = f"{port_name}{leaf}"
                key = (module.name, flattened_port)
                mapped = table.get_port_name(*key)
                info.append((flattened_port, mapped))
        port_info[module] = info

    return inst_info, port_info
