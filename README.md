# protobuf-typeddict

Tiny tool for generating the TypedDicts describing the protobuf's `MessageToDict`/`ParseDict` (aka `json`) representations.

Some data are better manipulated as simple (typesafe) dicts instead of the python-protobuf's rich objects. Now the protobufs are just the binary serialization library.

## Example

Given this ...

```protobuf
message Project {
    optional fixed64 id = 1;
    optional float billing = 2;
    optional bool is_active = 3;
}

message User {
    optional int32 id = 1;
    optional string name = 2;
    repeated string email = 3;
    map<string, Project> project = 4;
}
```

generates this:

```python
Project = TypedDict(
    "Project",
    {
        "id": NotRequired[int],
        "billing": NotRequired[float],
        "is_active": NotRequired[bool],
    }
)

User = TypedDict(
    "User",
    {
        "id": NotRequired[int],
        "name": NotRequired[str],
        "email": list[str],
        "project": dict[str, "Project"],
    }
)
```

## Installation

The pb2td is not on the PyPI yet.
Download the code and run

```shell
pip install <path>
```

## Usage

### Cli

pb2td installs the script `pb2td`. Run it as

```shell
pb2td src_pb2.py dst.py
```

to generate the `dst.py` types.

### Programmatic

```python
import my_module_pb2
import pb2td
# the result is str
result = pb2tf.generate(my_module_pb2)
print(result)
```

NOTE: The pb2td makes TypedDicts from protoc-generated `_pb2.py`/`_pb3.py` files, not the `.proto`.

## Limitations

- No RPC/services. Just the plain data protobufs
- No well-known types (`datetime` etc)
- Enums are typed as int
- No pb2 extensions
