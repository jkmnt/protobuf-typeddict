"""protobuf-typeddict: Create TypedDict definitions for protobuf json"""

# Licenced under the MIT License: https://www.opensource.org/licenses/mit-license.php

__version__ = "0.1.0"


from pathlib import Path
from dataclasses import dataclass
import importlib
import importlib.util
import enum
from types import ModuleType
from typing import NamedTuple

from google.protobuf.descriptor import Descriptor, FieldDescriptor
import click


@dataclass
class Options:
    add_extra_anno: bool
    maps_as_dict: bool
    preserve_names: bool


class Typ(NamedTuple):
    name: str
    pytype: str


TYPES: dict[int, Typ] = {
    8: Typ("bool", "bool"),
    # 12: Typ("bytes", "str | bytes"),
    12: Typ("bytes", "_Base64"),
    1: Typ("double", "float"),
    14: Typ("enum", "int"),
    7: Typ("fixed32", "int"),
    6: Typ("fixed64", "int"),
    2: Typ("float", "float"),
    # 10: ("group", 'list'),
    5: Typ("int32", "int"),
    3: Typ("int64", "int"),
    11: Typ("message", "dict"),
    15: Typ("sfixed32", "int"),
    16: Typ("sfixed64", "int"),
    17: Typ("sint32", "int"),
    18: Typ("sint64", "int"),
    9: Typ("string", "str"),
    13: Typ("uint32", "int"),
    4: Typ("uint64", "int"),
}


class Kinds(enum.IntEnum):
    OPTIONAL = 1
    REPEATED = 3
    REQUIRED = 2


# vendored in from protobuf
def to_lowercamel(name: str):
    capitalize_next = False
    result = []

    for c in name:
        if c == "_":
            capitalize_next = True
        elif capitalize_next:
            result.append(c.upper())
            capitalize_next = False
        else:
            result += c

    return "".join(result)


def compose_path(d: Descriptor):
    path: list[Descriptor] = []
    path.append(d)
    while d.containing_type:
        d = d.containing_type
        path.append(d)
    return "".join(p.name for p in path[::-1])


def is_map(field: Descriptor | FieldDescriptor):
    submsg: Descriptor | None = field.message_type if isinstance(field, FieldDescriptor) else field
    return submsg and submsg.GetOptions().map_entry


def gen_type(field: FieldDescriptor, options: Options):

    submsg: Descriptor | None = field.message_type

    if submsg:
        if options.maps_as_dict and is_map(field):
            ky = gen_type(submsg.fields_by_number[1], options)
            vt = gen_type(submsg.fields_by_number[2], options)
            typ = f"dict[{ky}, {vt}]"
        else:
            typ = f'"{ compose_path(submsg) }"'
    else:
        typ = TYPES[field.type].pytype
    return typ


def gen_field(field: FieldDescriptor, options: Options):
    typ = gen_type(field, options)

    if options.add_extra_anno:
        typ = f'Annotated[{ typ }, {field.number}, "{TYPES[field.type].name}"]'

    if options.maps_as_dict and is_map(field):
        anno = typ  # already provided in gen_type
    else:
        kind = Kinds(field.label)
        if kind == Kinds.OPTIONAL:
            anno = f"NotRequired[{typ}]"
        elif kind == Kinds.REPEATED:
            anno = f"NotRequired[list[{typ}]]"
        else:
            anno = typ

    name = field.name if options.preserve_names else to_lowercamel(field.name)
    return f'"{ name }": { anno }'


def gen_td(desc: Descriptor, options: Options):
    path = compose_path(desc)
    fields = [gen_field(desc.fields_by_name[field.name], options) for field in desc.fields]
    indent = "    " * 2

    items = "\n".join([f"{ indent }{ f }," for f in fields])

    return f"""\
{path} = TypedDict(
    "{ path }",
    {{
{ items }
    }}
)"""


def gen_document(descs: list[Descriptor], options: Options):
    tds = [gen_td(desc, options) for desc in descs]

    type_imports = ["TypedDict", "NotRequired", "TypeAlias"]
    if options.add_extra_anno:
        type_imports.append("Annotated")

    return f"""\
# Generated file. Do not edit.
from typing import { ', '.join(type_imports) }

_Base64: TypeAlias = str

{ '\n\n'.join(tds) }
"""


def generate(module: ModuleType, extra_anno: bool = False, maps: bool = True, preserve_names: bool = True):
    options = Options(add_extra_anno=extra_anno, maps_as_dict=maps, preserve_names=preserve_names)

    descs: list[Descriptor] = []

    for obj in vars(module).values():
        if not isinstance(obj, Descriptor):
            continue
        if options.maps_as_dict and is_map(obj):
            continue
        descs.append(obj)

    return gen_document(descs, options)


@click.command()
@click.argument("src", type=click.Path(dir_okay=False, exists=True, path_type=Path))
@click.argument("dst", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--extra-anno/--no-extra-anno", help="Add field numbers/protobuf types for reference")
@click.option("--maps/--no-maps", help="Describe protobuf maps as dicts", default=True)
@click.option("--camel-names/--no-camel-name", help="Convert field names to lowerCamel")
def cli(src: Path, dst: Path, extra_anno: bool, maps: bool, camel_names: bool):
    """Create TypedDict declarations from protoc-generated Python code"""

    src = Path(src)

    spec = importlib.util.spec_from_file_location(src.stem, src)
    assert spec
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)

    doc = generate(module, extra_anno=extra_anno, maps=maps, preserve_names=not camel_names)
    dst.write_text(doc)
