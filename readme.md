# Backports of Python dataclass features of 3.8+ to 3.6

Adds most dataclass features from Python versions after 3.7 to the excellent but long-since 
abondoned backport by Eric V. Smith (https://github.com/ericvsmith/dataclasses/).

For those of us still stuck writing Python for systems tied hard to the the oldest LTS releases 
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
| 3.11–3.12 | `fields()` traceback improvements | Backported |
| 3.11–3.12 | Mutable default value validation | Backported |
| 3.12–3.13 | Optimized `__eq__` and `__repr__` recursion guards | Backported |
| 3.14 | `decorator` parameter for `make_dataclass()` | Backported |

## Usage

Drop the single `dataclasses.py` file into your project (vendoring), or add it to
your Python path. It is a drop-in replacement for the standard library module:

```python
from dataclasses import dataclass, field, KW_ONLY

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
