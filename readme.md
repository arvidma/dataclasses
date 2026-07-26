# Backports of Python dataclass features of 3.8+ to 3.6+

Adds most dataclass features from Python versions after 3.7 to the excellent but long-since 
abandoned backport by Eric V. Smith (https://github.com/ericvsmith/dataclasses/).

For those of us still stuck writing Python for systems tied hard to the oldest LTS releases 
of Ubuntu and RedHat.

Matrix of backported and not-yet-backported features:

| Python version | Feature | Status |
|---|---|---|
| 3.8 | `InitVar[T]` generic syntax | Backported |
| 3.8 | `replace()` handling of `InitVar` fields with defaults | Backported |
| 3.10 | `kw_only` parameter and `KW_ONLY` sentinel | Backported |
| 3.10 | `match_args` parameter (`__match_args__` generation) | Backported |
| 3.10 | `slots` parameter (`__slots__` generation) | Backported |
| 3.11 | `weakref_slot` parameter | Backported |
| 3.11 | Frozen+slots pickling (`__getstate__`/`__setstate__`) | Backported |
| 3.11 | Slots with `init=False` default fields (bpo-44649) | Backported |
| 3.11–3.12 | `fields()` traceback improvements | Backported |
| 3.11–3.12 | Mutable default value validation | Backported |
| 3.12 | Field named `BUILTINS` in frozen classes (gh-96151) | Backported |
| 3.12 | Special underscore field names like `_dflt_x` (gh-98886) | Backported |
| 3.12 | Inherited `__dict__` slot handling | Backported |
| 3.12–3.13 | Optimized `__eq__` and `__repr__` recursion guards | Backported |
| 3.13 | Non-frozen subclass of frozen: mutable attr set/delete | Backported |
| 3.14 | `decorator` parameter for `make_dataclass()` | Backported |
| 3.12 | `module` parameter for `make_dataclass()` | Not backported |
| 3.12 | `defaultdict` support in `asdict()`/`astuple()` | Not backported |
| 3.13 | `__replace__()` method (`copy.replace()` support) | Not backported |

## Usage

Drop the single `dataclasses.py` file into your project (vendoring), or add it to
your Python path. It is a drop-in replacement for the standard library module and
can transparently replace the stdlib if running on a Python version that doesn't
support some feature you like.

Supports Python 3.6 and later from a single codebase — the only
version-sensitive code is the `ClassVar` detection, which adapts to the
`typing` internals of the running interpreter. The test suite runs in CI on
Python 3.6 through 3.13.

Note: don't mix this module with the stdlib `dataclasses` in the same class.
`InitVar`, `Field`, `field()` and the `KW_ONLY` sentinel are compared by
identity, so e.g. a stdlib `InitVar` annotation on a class decorated with this
module's `@dataclass` will not be recognized. Import everything from one module,
as in the example below.

```python
try:
    from dataclasses import dataclass, field, KW_ONLY
except ImportError:
    from myproj.vendor.dataclasses import dataclass, field, KW_ONLY  # type: ignore[no-redef]

@dataclass(slots=True, kw_only=True)
class Point:
    x: float
    y: float
    z: float = 0.0
```

## Full `@dataclass` decorator signature

```python
@dataclass(
    init=True,           # 3.7
    repr=True,           # 3.7
    eq=True,             # 3.7
    order=False,         # 3.7
    unsafe_hash=False,   # 3.7
    frozen=False,        # 3.7
    match_args=True,     # 3.10
    kw_only=False,       # 3.10
    slots=False,         # 3.10
    weakref_slot=False,  # 3.11
)
```
