"""Tests for dataclasses.py — pure Python, no test framework."""

import sys
import os

if sys.version_info[:2] != (3, 6):
    print(
        f"ERROR: These tests require Python 3.6, got {sys.version_info[0]}.{sys.version_info[1]}"
    )
    sys.exit(1)

# Ensure we import from the current directory, not stdlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dataclasses import (
    dataclass,
    field,
    fields,
    asdict,
    astuple,
    make_dataclass,
    replace,
    is_dataclass,
    FrozenInstanceError,
    InitVar,
    KW_ONLY,
    MISSING,
)

passed = 0
failed = 0


def check(description, condition):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {description}")


def check_raises(description, exc_type, fn):
    global passed, failed
    try:
        fn()
        failed += 1
        print(f"  FAIL: {description} (no exception raised)")
    except exc_type:
        passed += 1
    except Exception as e:
        failed += 1
        print(f"  FAIL: {description} (got {type(e).__name__}: {e})")


def section(name):
    print(f"\n--- {name} ---")


# ============================================================
section("Basic @dataclass")
# ============================================================


@dataclass
class Point:
    x: int
    y: int


p = Point(1, 2)
check("init sets fields", p.x == 1 and p.y == 2)
check("repr", repr(p) == "Point(x=1, y=2)")
check("eq same values", Point(1, 2) == Point(1, 2))
check("eq different values", Point(1, 2) != Point(3, 4))
check("identity eq", p == p)


# ============================================================
section("@dataclass with parens")
# ============================================================


@dataclass()
class PointP:
    x: int
    y: int


pp = PointP(10, 20)
check("init with parens", pp.x == 10 and pp.y == 20)


# ============================================================
section("Default values")
# ============================================================


@dataclass
class WithDefaults:
    x: int
    y: int = 10
    z: str = "hello"


wd1 = WithDefaults(1)
check("positional + defaults", wd1.x == 1 and wd1.y == 10 and wd1.z == "hello")
wd2 = WithDefaults(1, 20, "world")
check("override defaults", wd2.y == 20 and wd2.z == "world")


# ============================================================
section("default_factory")
# ============================================================


@dataclass
class WithFactory:
    items: list = field(default_factory=list)
    data: dict = field(default_factory=dict)


wf1 = WithFactory()
wf2 = WithFactory()
check("factory creates new instances", wf1.items is not wf2.items)
check("factory list is empty", wf1.items == [])
wf1.items.append(1)
check("mutation doesn't leak", wf2.items == [])


# ============================================================
section("Mutable default rejected")
# ============================================================

check_raises(
    "list default raises ValueError",
    ValueError,
    lambda: dataclass(type("Bad", (), {"__annotations__": {"x": list}, "x": []})),
)

check_raises(
    "dict default raises ValueError",
    ValueError,
    lambda: dataclass(type("Bad2", (), {"__annotations__": {"x": dict}, "x": {}})),
)


# ============================================================
section("field() options")
# ============================================================


@dataclass
class FieldOpts:
    visible: int = 10
    hidden: int = field(default=20, repr=False)
    no_compare: int = field(default=30, compare=False)
    no_init: int = field(default=99, init=False)


fo = FieldOpts(1)
check("repr excludes hidden", "hidden" not in repr(fo))
check("repr includes visible", "visible=1" in repr(fo))
check("no_compare ignored in eq", FieldOpts(1, 2, 100) == FieldOpts(1, 2, 200))
check("no_init uses default", fo.no_init == 99)
check_raises(
    "no_init field rejected in constructor", TypeError, lambda: FieldOpts(1, 2, 3, 4)
)


# ============================================================
section("fields() function")
# ============================================================

fs = fields(Point)
check("fields returns tuple", isinstance(fs, tuple))
check("fields count", len(fs) == 2)
check("field names", fs[0].name == "x" and fs[1].name == "y")
check("fields on instance", fields(Point(0, 0)) == fs)


# ============================================================
section("is_dataclass()")
# ============================================================

check("is_dataclass on class", is_dataclass(Point))
check("is_dataclass on instance", is_dataclass(Point(0, 0)))
check("is_dataclass on non-dc class", not is_dataclass(int))
check("is_dataclass on non-dc instance", not is_dataclass(42))


# ============================================================
section("__eq__ and __hash__")
# ============================================================

# Default: eq=True, frozen=False => __hash__ is None (unhashable)
check("default dc is unhashable", Point.__hash__ is None)
check_raises("hash raises", TypeError, lambda: hash(Point(1, 2)))


@dataclass(frozen=True)
class FrozenPoint:
    x: int
    y: int


check("frozen dc is hashable", hash(FrozenPoint(1, 2)) == hash(FrozenPoint(1, 2)))
check("frozen eq", FrozenPoint(1, 2) == FrozenPoint(1, 2))


@dataclass(eq=False)
class NoEq:
    x: int


ne1 = NoEq(1)
ne2 = NoEq(1)
check("eq=False uses identity", ne1 != ne2)
check("eq=False self", ne1 == ne1)
check("eq=False is hashable (inherits object.__hash__)", hash(ne1) is not None)


@dataclass(unsafe_hash=True)
class UnsafeHash:
    x: int
    y: int


check("unsafe_hash works", hash(UnsafeHash(1, 2)) == hash(UnsafeHash(1, 2)))


# ============================================================
section("order=True")
# ============================================================


@dataclass(order=True)
class Ordered:
    x: int
    y: int


check("lt", Ordered(1, 2) < Ordered(1, 3))
check("le", Ordered(1, 2) <= Ordered(1, 2))
check("gt", Ordered(2, 0) > Ordered(1, 9))
check("ge", Ordered(1, 2) >= Ordered(1, 2))
check("not lt", not (Ordered(1, 3) < Ordered(1, 2)))

# Cross-type comparison returns NotImplemented
check("cross-type lt", Ordered(1, 2).__lt__(42) is NotImplemented)

check_raises(
    "order without eq raises",
    ValueError,
    lambda: dataclass(
        type("Bad", (), {"__annotations__": {"x": int}}), order=True, eq=False
    ),
)


# ============================================================
section("frozen=True")
# ============================================================


@dataclass(frozen=True)
class Frozen:
    x: int
    y: int


f = Frozen(1, 2)
check("frozen init works", f.x == 1 and f.y == 2)
check_raises("frozen setattr raises", FrozenInstanceError, lambda: setattr(f, "x", 10))
check_raises("frozen delattr raises", FrozenInstanceError, lambda: delattr(f, "x"))


# ============================================================
section("__post_init__")
# ============================================================


@dataclass
class WithPostInit:
    x: int
    y: int
    magnitude: float = field(init=False)

    def __post_init__(self):
        self.magnitude = (self.x**2 + self.y**2) ** 0.5


wpi = WithPostInit(3, 4)
check("post_init computed field", wpi.magnitude == 5.0)


# ============================================================
section("InitVar")
# ============================================================


@dataclass
class WithInitVar:
    x: int
    scale: InitVar[int] = 1

    def __post_init__(self, scale):
        self.x = self.x * scale


wiv = WithInitVar(5, scale=3)
check("InitVar used in post_init", wiv.x == 15)
check("InitVar not a field", all(f.name != "scale" for f in fields(wiv)))
check("InitVar default", WithInitVar(5).x == 5)


# ============================================================
section("ClassVar")
# ============================================================

import typing


@dataclass
class WithClassVar:
    x: int
    class_count: typing.ClassVar[int] = 0


wcv = WithClassVar(10)
check("ClassVar not in fields", all(f.name != "class_count" for f in fields(wcv)))
check("ClassVar not in init", wcv.x == 10)
check("ClassVar accessible", WithClassVar.class_count == 0)


# ============================================================
section("KW_ONLY")
# ============================================================


@dataclass
class WithKwOnly:
    x: int
    _: KW_ONLY
    y: int = 0
    z: int = 0


wkw = WithKwOnly(1, y=2, z=3)
check("kw_only init", wkw.x == 1 and wkw.y == 2 and wkw.z == 3)
check_raises("kw_only positional rejected", TypeError, lambda: WithKwOnly(1, 2, 3))


# ============================================================
section("kw_only=True on decorator")
# ============================================================


@dataclass(kw_only=True)
class AllKwOnly:
    x: int
    y: int


akw = AllKwOnly(x=1, y=2)
check("all kw_only", akw.x == 1 and akw.y == 2)
check_raises("all kw_only positional rejected", TypeError, lambda: AllKwOnly(1, 2))


# ============================================================
section("asdict()")
# ============================================================


@dataclass
class Nested:
    value: int


@dataclass
class Outer:
    name: str
    inner: Nested


o = Outer("test", Nested(42))
d = asdict(o)
check("asdict type", isinstance(d, dict))
check("asdict keys", set(d.keys()) == {"name", "inner"})
check("asdict nested", d["inner"] == {"value": 42})
check("asdict nested is dict", isinstance(d["inner"], dict))

# With custom dict_factory
from collections import OrderedDict

od = asdict(o, dict_factory=OrderedDict)
check("asdict dict_factory", isinstance(od, OrderedDict))

check_raises("asdict on non-dc", TypeError, lambda: asdict(42))


# ============================================================
section("astuple()")
# ============================================================

t = astuple(o)
check("astuple type", isinstance(t, tuple))
check("astuple values", t == ("test", (42,)))

check_raises("astuple on non-dc", TypeError, lambda: astuple(42))


# ============================================================
section("replace()")
# ============================================================


@dataclass
class Replaceable:
    x: int
    y: int
    z: int = 0


r = Replaceable(1, 2, 3)
r2 = replace(r, x=10)
check("replace creates new obj", r is not r2)
check("replace changed field", r2.x == 10)
check("replace unchanged fields", r2.y == 2 and r2.z == 3)
check("original unchanged", r.x == 1)


@dataclass(frozen=True)
class FrozenReplace:
    x: int
    y: int


fr = FrozenReplace(1, 2)
fr2 = replace(fr, x=10)
check("replace on frozen", fr2.x == 10 and fr2.y == 2)

check_raises("replace on non-dc", TypeError, lambda: replace(42, x=1))


# replace with init=False field in changes should raise
@dataclass
class ReplNoInit:
    x: int
    y: int = field(default=0, init=False)


check_raises(
    "replace with init=False field raises",
    ValueError,
    lambda: replace(ReplNoInit(1), y=5),
)


# ============================================================
section("make_dataclass()")
# ============================================================

Dynamic = make_dataclass("Dynamic", ["x", ("y", int), ("z", int, field(default=5))])
dyn = Dynamic("hello", 10)
check("make_dataclass init", dyn.x == "hello" and dyn.y == 10 and dyn.z == 5)
check("make_dataclass is_dataclass", is_dataclass(Dynamic))
check("make_dataclass repr", "Dynamic" in repr(dyn))


# With bases
@dataclass
class Base:
    a: int


Derived = make_dataclass("Derived", [("b", int)], bases=(Base,))
der = Derived(1, 2)
check("make_dataclass with bases", der.a == 1 and der.b == 2)


# ============================================================
section("Inheritance")
# ============================================================


@dataclass
class Parent:
    x: int
    y: int = 0


@dataclass
class Child(Parent):
    z: int = 0


c = Child(1, 2, 3)
check("inherited fields", c.x == 1 and c.y == 2 and c.z == 3)
check("child fields includes parent", len(fields(Child)) == 3)
check("child repr", "Child(x=1, y=2, z=3)" == repr(c))

# Parent and child eq
check("parent-child not eq", Parent(1, 2) != Child(1, 2, 0))


# ============================================================
section("Frozen inheritance")
# ============================================================


@dataclass(frozen=True)
class FrozenParent:
    x: int


@dataclass(frozen=True)
class FrozenChild(FrozenParent):
    y: int


fc = FrozenChild(1, 2)
check("frozen child init", fc.x == 1 and fc.y == 2)
check_raises("frozen child setattr", FrozenInstanceError, lambda: setattr(fc, "x", 10))

check_raises(
    "non-frozen from frozen",
    TypeError,
    lambda: dataclass(type("Bad", (FrozenParent,), {"__annotations__": {"y": int}})),
)


# ============================================================
section("slots=True")
# ============================================================


@dataclass(slots=True)
class WithSlots:
    x: int
    y: int


ws = WithSlots(1, 2)
check("slots init", ws.x == 1 and ws.y == 2)
check("has __slots__", hasattr(WithSlots, "__slots__"))
check(
    "slots contains fields", "x" in WithSlots.__slots__ and "y" in WithSlots.__slots__
)
check_raises("slots no arbitrary attr", AttributeError, lambda: setattr(ws, "q", 1))


# ============================================================
section("slots=True + frozen=True")
# ============================================================


@dataclass(slots=True, frozen=True)
class FrozenSlots:
    x: int
    y: int


fsl = FrozenSlots(1, 2)
check("frozen+slots init", fsl.x == 1 and fsl.y == 2)
check_raises("frozen+slots setattr", FrozenInstanceError, lambda: setattr(fsl, "x", 10))


# ============================================================
section("match_args")
# ============================================================


@dataclass
class MatchArgs:
    x: int
    y: int
    z: int = 0


check("__match_args__ set", hasattr(MatchArgs, "__match_args__"))
check("__match_args__ value", MatchArgs.__match_args__ == ("x", "y", "z"))


@dataclass(match_args=False)
class NoMatchArgs:
    x: int


check("match_args=False", not hasattr(NoMatchArgs, "__match_args__"))


# ============================================================
section("metadata")
# ============================================================


@dataclass
class WithMeta:
    x: int = field(metadata={"unit": "meters", "precision": 2})
    y: int = 0


fm = fields(WithMeta)[0]
check("metadata accessible", fm.metadata["unit"] == "meters")
check("metadata is mappingproxy", type(fm.metadata).__name__ == "mappingproxy")
check("empty metadata", len(fields(WithMeta)[1].metadata) == 0)
check_raises(
    "metadata is read-only",
    (TypeError, AttributeError),
    lambda: fm.metadata.__setitem__("k", "v"),
)


# ============================================================
section("init=False")
# ============================================================


@dataclass(init=False)
class NoInit:
    x: int
    y: int

    def __init__(self, val):
        self.x = val
        self.y = val * 2


ni = NoInit(5)
check("custom init used", ni.x == 5 and ni.y == 10)


# ============================================================
section("repr=False")
# ============================================================


@dataclass(repr=False)
class NoRepr:
    x: int


nr = NoRepr(1)
check("custom repr not added", "NoRepr(x=1)" != repr(nr))


# ============================================================
section("eq=False on decorator")
# ============================================================


@dataclass(eq=False)
class NoEqDec:
    x: int


check("eq=False identity only", NoEqDec(1) != NoEqDec(1))


# ============================================================
section("Field with hash=True/False")
# ============================================================


@dataclass(unsafe_hash=True)
class HashControl:
    key: int
    ignored: int = field(hash=False)


check("hash ignores field", hash(HashControl(1, 100)) == hash(HashControl(1, 200)))
check("hash uses key", hash(HashControl(1, 0)) != hash(HashControl(2, 0)))


# ============================================================
section("field with kw_only=True")
# ============================================================


@dataclass
class FieldKwOnly:
    x: int
    y: int = field(default=0, kw_only=True)


fkw = FieldKwOnly(1, y=5)
check("field kw_only", fkw.x == 1 and fkw.y == 5)
check_raises("field kw_only positional", TypeError, lambda: FieldKwOnly(1, 2))


# ============================================================
section("MISSING sentinel")
# ============================================================

check("MISSING is singleton", MISSING is MISSING)
check("MISSING type", type(MISSING).__name__ == "_MISSING_TYPE")


# ============================================================
section("FrozenInstanceError")
# ============================================================

check(
    "FrozenInstanceError is AttributeError",
    issubclass(FrozenInstanceError, AttributeError),
)


# ============================================================
section("both default and default_factory raises")
# ============================================================

check_raises(
    "default + default_factory",
    ValueError,
    lambda: field(default=0, default_factory=list),
)


# ============================================================
section("Field without annotation raises")
# ============================================================

check_raises(
    "field no annotation",
    TypeError,
    lambda: dataclass(type("Bad", (), {"x": field(default=0)})),
)


# ============================================================
section("Non-default after default raises")
# ============================================================

check_raises(
    "non-default after default",
    TypeError,
    lambda: dataclass(
        type("Bad", (), {"__annotations__": {"x": int, "y": int}, "x": 0})
    ),
)


# ============================================================
section("asdict with lists and dicts")
# ============================================================


@dataclass
class Complex:
    items: list
    mapping: dict


cx = Complex([Nested(1), Nested(2)], {"a": Nested(3)})
cd = asdict(cx)
check("asdict list of dc", cd["items"] == [{"value": 1}, {"value": 2}])
check("asdict dict of dc", cd["mapping"] == {"a": {"value": 3}})


# ============================================================
section("replace() with InitVar")
# ============================================================


@dataclass
class InitVarReplace:
    x: int
    factor: InitVar[int] = 1

    def __post_init__(self, factor):
        self.x = self.x * factor


ivr = InitVarReplace(5, factor=2)
check("InitVar replace original", ivr.x == 10)
ivr2 = replace(ivr, x=3)
check("replace with InitVar default", ivr2.x == 3)


# ============================================================
section("weakref_slot")
# ============================================================

import weakref


@dataclass(slots=True, weakref_slot=True)
class WeakRefable:
    x: int


wr_obj = WeakRefable(42)
ref = weakref.ref(wr_obj)
check("weakref works with weakref_slot", ref() is wr_obj)

check_raises(
    "weakref_slot without slots",
    TypeError,
    lambda: dataclass(
        type("Bad", (), {"__annotations__": {"x": int}}), weakref_slot=True
    ),
)


# ============================================================
section("Pickling frozen+slots")
# ============================================================

import pickle


@dataclass(frozen=True, slots=True)
class Picklable:
    x: int
    y: str


pk = Picklable(1, "hello")
pk2 = pickle.loads(pickle.dumps(pk))
check("pickle roundtrip", pk == pk2)
check("pickle preserves values", pk2.x == 1 and pk2.y == "hello")


# ============================================================
section("Self-referencing repr")
# ============================================================


@dataclass
class SelfRef:
    x: int
    children: list = field(default_factory=list)


sr = SelfRef(1)
sr.children.append(sr)
r_str = repr(sr)
check("recursive repr doesn't crash", "..." in r_str)


# ============================================================
section("'self' as field name")
# ============================================================


@dataclass
class SelfField:
    self: int
    other: int


sf = SelfField(1, 2)
check("'self' field name works", sf.self == 1 and sf.other == 2)


# ============================================================
section("Cross-type comparison returns NotImplemented")
# ============================================================

check("eq cross-type", Point(1, 2).__eq__("not a point") is NotImplemented)


# ============================================================
section("doc string generated")
# ============================================================


@dataclass
class Documented:
    x: int
    y: int = 0


check("doc generated", Documented.__doc__ is not None)
check("doc contains class name", "Documented" in Documented.__doc__)


# ============================================================
# Summary
# ============================================================

print(f"\n{'=' * 40}")
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
