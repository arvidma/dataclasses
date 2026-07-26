"""Tests for dataclasses.py — pure Python, no test framework."""

import io
import os
import pickle
import sys
import traceback
import typing
import weakref
from collections import OrderedDict, namedtuple
from copy import deepcopy

if sys.version_info < (3, 6):
    print(
        f"ERROR: These tests require Python 3.6+, got {sys.version_info[0]}.{sys.version_info[1]}"
    )
    sys.exit(1)

# Ensure we import from the current directory, not stdlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dataclasses import (
    KW_ONLY,
    MISSING,
    FrozenInstanceError,
    InitVar,
    asdict,
    astuple,
    dataclass,
    field,
    fields,
    is_dataclass,
    make_dataclass,
    replace,
)

print(f"Running on Python {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")

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
section("Field named 'object'")
# ============================================================


@dataclass
class FieldNamedObject:
    object: str


fno = FieldNamedObject("foo")
check("field named object works", fno.object == "foo")


@dataclass(frozen=True)
class FieldNamedObjectFrozen:
    object: str


fnof = FieldNamedObjectFrozen("bar")
check("field named object frozen works", fnof.object == "bar")


# ============================================================
section("Field named 'BUILTINS' (frozen)")
# ============================================================


# gh-96151: field named BUILTINS should work in frozen dataclasses
@dataclass(frozen=True)
class FieldNamedBUILTINS:
    BUILTINS: int


fnb = FieldNamedBUILTINS(5)
check("BUILTINS field frozen works", fnb.BUILTINS == 5)


# ============================================================
section("Field with special underscore names")
# ============================================================

# gh-98886: fields with names like _dflt_<field> or _HAS_DEFAULT_FACTORY
# could clash with internal generated code


@dataclass
class SpecialUnderscoreX:
    x: int = field(default_factory=lambda: 111)
    _dflt_x: int = field(default_factory=lambda: 222)


sux = SpecialUnderscoreX()
check("_dflt_x field default works", sux.x == 111 and sux._dflt_x == 222)


@dataclass
class SpecialUnderscoreY:
    y: int = field(default_factory=lambda: 111)
    _HAS_DEFAULT_FACTORY: int = 222


suy = SpecialUnderscoreY(y=222)
check("_HAS_DEFAULT_FACTORY field works", suy.y == 222)


# ============================================================
section("Recursive eq")
# ============================================================


@dataclass
class RecEq:
    recursive: object = ...


req = RecEq()
req.recursive = req
check("recursive eq doesn't crash", req == req)


# ============================================================
section("Frozen deepcopy")
# ============================================================

@dataclass(frozen=True, slots=False)
class FrozenDeepCopyNoSlots:
    s: str


fdc = FrozenDeepCopyNoSlots("hello")
check("frozen deepcopy without slots", deepcopy(fdc) == fdc)


@dataclass(frozen=True, slots=True)
class FrozenDeepCopyWithSlots:
    s: str


fdcs = FrozenDeepCopyWithSlots("hello")
check("frozen deepcopy with slots", deepcopy(fdcs) == fdcs)


# ============================================================
section("Slots with default no init")
# ============================================================

# bpo-44649: slots + default + init=False


@dataclass(slots=True)
class SlotsDefaultNoInit:
    a: str
    b: str = field(default="b", init=False)


sdni = SlotsDefaultNoInit("a")
check("slots default no init", sdni.a == "a" and sdni.b == "b")


@dataclass(slots=True)
class SlotsFactoryNoInit:
    a: str
    b: str = field(default_factory=lambda: "b", init=False)


sfni = SlotsFactoryNoInit("a")
check("slots factory no init", sfni.a == "a" and sfni.b == "b")


# ============================================================
section("Slots no weakref without weakref_slot")
# ============================================================


@dataclass(slots=True)
class SlotsNoWeakref:
    x: int


check("__weakref__ not in slots", "__weakref__" not in SlotsNoWeakref.__slots__)
check_raises(
    "slots without weakref_slot rejects weakref",
    TypeError,
    lambda: weakref.ref(SlotsNoWeakref(1)),
)


# ============================================================
section("Frozen+slots pickle with custom __getstate__/__setstate__")
# ============================================================


@dataclass(frozen=True, slots=True)
class FrozenSlotsCustomState:
    foo: str
    bar: int
    getstate_called: bool = field(default=False, compare=False)
    setstate_called: bool = field(default=False, compare=False)

    def __getstate__(self):
        object.__setattr__(self, "getstate_called", True)
        return [self.foo, self.bar]

    def __setstate__(self, state):
        object.__setattr__(self, "setstate_called", True)
        object.__setattr__(self, "foo", state[0])
        object.__setattr__(self, "bar", state[1])


fscs = FrozenSlotsCustomState("a", 1)
fscs2 = pickle.loads(pickle.dumps(fscs))
check("custom getstate called", fscs.getstate_called)
check("custom setstate called", fscs2.setstate_called)
check("custom state pickle roundtrip", fscs == fscs2)


# ============================================================
section("KW_ONLY with field(kw_only=False) override")
# ============================================================


@dataclass
class KwOnlyOverride:
    a: int
    _: KW_ONLY
    b: int
    c: int = field(kw_only=False)


kwo = KwOnlyOverride(1, 2, b=3)
check("kw_only override positional c", kwo.a == 1 and kwo.b == 3 and kwo.c == 2)
kwo2 = KwOnlyOverride(1, b=3, c=2)
check("kw_only override named c", kwo2.a == 1 and kwo2.b == 3 and kwo2.c == 2)


# ============================================================
section("KW_ONLY twice raises")
# ============================================================


def _make_kw_only_twice():
    @dataclass
    class Bad:
        a: int
        X: KW_ONLY
        Y: KW_ONLY
        b: int


check_raises(
    "KW_ONLY specified twice raises TypeError",
    TypeError,
    _make_kw_only_twice,
)


# ============================================================
section("KW_ONLY defaults after non-defaults ok")
# ============================================================


@dataclass
class KwOnlyDefaults:
    a: int = 0
    _: KW_ONLY
    b: int = 1
    c: int = 2
    d: int = 3


kwod = KwOnlyDefaults(d=4, b=3)
check(
    "kw_only allows defaults after non-defaults",
    kwod.a == 0 and kwod.b == 3 and kwod.c == 2 and kwod.d == 4,
)

# But non-kwarg non-defaults after defaults still fail
check_raises(
    "non-kw non-default after default still fails",
    TypeError,
    lambda: dataclass(
        type(
            "Bad",
            (),
            {"__annotations__": {"a": int, "z": int}, "a": 0},
        )
    ),
)


# ============================================================
section("match_args with kw_only")
# ============================================================


@dataclass(kw_only=True)
class MatchArgsKwOnly:
    a: int


check(
    "kw_only fields not in __match_args__",
    MatchArgsKwOnly(a=42).__match_args__ == (),
)


@dataclass
class MatchArgsMixed:
    a: int
    b: int = field(kw_only=True)


check(
    "mixed kw_only match_args",
    MatchArgsMixed(42, b=10).__match_args__ == ("a",),
)


# ============================================================
section("Explicit __match_args__ preserved")
# ============================================================

ma = ()


@dataclass
class ExplicitMatchArgs:
    a: int
    __match_args__ = ma


check("explicit match_args preserved", ExplicitMatchArgs(42).__match_args__ is ma)


# ============================================================
section("match_args via make_dataclass")
# ============================================================

MdcMatchArgs = make_dataclass("MdcMatchArgs", [("x", int), ("y", int)])
check("make_dataclass match_args", MdcMatchArgs.__match_args__ == ("x", "y"))

MdcNoMatchArgs = make_dataclass(
    "MdcNoMatchArgs", [("x", int), ("y", int)], match_args=False
)
check(
    "make_dataclass match_args=False", "__match_args__" not in MdcNoMatchArgs.__dict__
)


# ============================================================
section("make_dataclass with namespace")
# ============================================================

MdcNs = make_dataclass(
    "MdcNs",
    [("x", int), ("y", int, field(default=5))],
    namespace={"add_one": lambda self: self.x + 1},
)
mdc_ns = MdcNs(10)
check("make_dataclass namespace", mdc_ns.x == 10 and mdc_ns.y == 5)
check("make_dataclass namespace method", mdc_ns.add_one() == 11)

# Provided namespace is not mutated
ns = {}
make_dataclass("MdcNsMutate", [("x", int)], namespace=ns)
check("make_dataclass namespace not mutated", ns == {})


# ============================================================
section("make_dataclass with decorator parameter")
# ============================================================


def custom_dataclass(cls, *args, **kwargs):
    dc = dataclass(cls, *args, **kwargs)
    dc.__custom__ = True
    return dc


MdcDecorator = make_dataclass("MdcDecorator", [("x", int)], decorator=custom_dataclass)
mdc_dec = MdcDecorator(10)
check("make_dataclass custom decorator", mdc_dec.x == 10)
check("make_dataclass custom decorator applied", MdcDecorator.__custom__ is True)

# default decorator
MdcDefaultDec = make_dataclass("MdcDefaultDec", [("x", int)], decorator=dataclass)
check("make_dataclass default decorator", MdcDefaultDec(10).x == 10)


# ============================================================
section("make_dataclass invalid field specs")
# ============================================================

check_raises(
    "make_dataclass empty tuple field",
    TypeError,
    lambda: make_dataclass("Bad", ["a", ()]),
)
check_raises(
    "make_dataclass 4-tuple field",
    TypeError,
    lambda: make_dataclass("Bad", ["a", (1, 2, 3, 4)]),
)
check_raises(
    "make_dataclass duplicate field names",
    TypeError,
    lambda: make_dataclass("Bad", ["a", "a"]),
)
check_raises(
    "make_dataclass keyword field name",
    TypeError,
    lambda: make_dataclass("Bad", ["for"]),
)
check_raises(
    "make_dataclass non-identifier field name",
    TypeError,
    lambda: make_dataclass("Bad", ["x,y"]),
)


# ============================================================
section("make_dataclass with kw_only")
# ============================================================

MdcKw = make_dataclass("MdcKw", ["a"], kw_only=True)
check("make_dataclass kw_only", fields(MdcKw)[0].kw_only)

MdcKwMixed = make_dataclass(
    "MdcKwMixed",
    ["a", ("b", int, field(kw_only=False))],
    kw_only=True,
)
check("make_dataclass kw_only mixed", fields(MdcKwMixed)[0].kw_only)
check("make_dataclass kw_only mixed override", not fields(MdcKwMixed)[1].kw_only)


# ============================================================
section("replace() with init=False raises TypeError")
# ============================================================


@dataclass
class ReplaceInitFalse:
    x: int
    y: int = field(init=False, default=10)


rif = ReplaceInitFalse(1)
rif.y = 20
rif2 = replace(rif, x=5)
check("replace init=False gets default", rif2.x == 5 and rif2.y == 10)

check_raises(
    "replace init=False field raises",
    (TypeError, ValueError),
    lambda: replace(rif, x=2, y=30),
)

check_raises(
    "replace only init=False field raises",
    (TypeError, ValueError),
    lambda: replace(rif, y=30),
)


# ============================================================
section("replace() on frozen with init=False")
# ============================================================


@dataclass(frozen=True)
class FrozenReplaceInitFalse:
    x: int
    y: int
    z: int = field(init=False, default=10)
    t: int = field(init=False, default=100)


frif = FrozenReplaceInitFalse(1, 2)
frif2 = replace(frif, x=3)
check("frozen replace values", frif2.x == 3 and frif2.y == 2 and frif2.z == 10)

check_raises(
    "frozen replace init=False raises",
    (TypeError, ValueError),
    lambda: replace(frif, x=3, z=20, t=50),
)

# Make sure the result is still frozen
check_raises(
    "frozen replace result is still frozen",
    FrozenInstanceError,
    lambda: setattr(frif2, "x", 99),
)

# Invalid field name
check_raises(
    "replace invalid field name",
    TypeError,
    lambda: replace(frif, z_invalid=3),
)


# ============================================================
section("Non-frozen subclass of frozen")
# ============================================================


@dataclass(frozen=True)
class FrozenBase:
    x: int
    y: int = 10


class NonFrozenDerived(FrozenBase):
    pass


nfd = NonFrozenDerived(3)
check("non-frozen derived init", nfd.x == 3 and nfd.y == 10)

# Can set new mutable attributes
nfd.cached = True
check("non-frozen derived mutable attr", nfd.cached is True)

# But can't change frozen attributes
check_raises(
    "non-frozen derived frozen attr setattr",
    FrozenInstanceError,
    lambda: setattr(nfd, "x", 5),
)
check_raises(
    "non-frozen derived frozen attr delattr",
    FrozenInstanceError,
    lambda: delattr(nfd, "x"),
)

# Can delete mutable attributes
del nfd.cached
check("non-frozen derived del mutable attr", not hasattr(nfd, "cached"))


# ============================================================
section("is_dataclass with __getattr__")
# ============================================================

# bpo-37868: __getattr__ returning truthy should not fool is_dataclass


class AlwaysReturns:
    def __getattr__(self, key):
        return 0


check("is_dataclass rejects __getattr__ class", not is_dataclass(AlwaysReturns))
check("is_dataclass rejects __getattr__ instance", not is_dataclass(AlwaysReturns()))


class FakeDataclass:
    pass


fdc_obj = FakeDataclass()
fdc_obj.__dataclass_fields__ = []
check("is_dataclass rejects fake __dataclass_fields__", not is_dataclass(fdc_obj))


# ============================================================
section("asdict with tuple_factory-like nested containers")
# ============================================================

@dataclass
class AsDictUser:
    name: str
    id: int


@dataclass
class AsDictGroupList:
    id: int
    users: list


a_user = AsDictUser("Alice", 1)
b_user = AsDictUser("Bob", 2)
gl = AsDictGroupList(0, [a_user, b_user])
gld = asdict(gl)
check(
    "asdict list of dataclasses",
    gld == {"id": 0, "users": [{"name": "Alice", "id": 1}, {"name": "Bob", "id": 2}]},
)


# asdict copies values (not references)
a_copy = AsDictUser("Test", 1)
d_copy = asdict(a_copy)
check("asdict returns new dict each time", asdict(a_copy) is not asdict(a_copy))
check("asdict values correct", d_copy == {"name": "Test", "id": 1})


# ============================================================
section("astuple with tuple_factory")
# ============================================================


@dataclass
class ATupleC:
    x: int
    y: int


NT = namedtuple("NT", "x y")


def nt_factory(lst):
    return NT(*lst)


atc = ATupleC(1, 2)
att = astuple(atc, tuple_factory=nt_factory)
check("astuple tuple_factory type", type(att) is NT)
check("astuple tuple_factory values", att == NT(1, 2))


# ============================================================
section("Frozen empty dataclass")
# ============================================================


@dataclass(frozen=True)
class FrozenEmpty:
    pass


fe = FrozenEmpty()
check_raises(
    "frozen empty setattr",
    FrozenInstanceError,
    lambda: setattr(fe, "i", 5),
)
check_raises(
    "frozen empty delattr",
    FrozenInstanceError,
    lambda: delattr(fe, "i"),
)


# ============================================================
section("Overwriting __hash__ on frozen")
# ============================================================


@dataclass(frozen=True)
class FrozenCustomHash:
    x: int

    def __hash__(self):
        return 301


check("frozen custom hash used", hash(FrozenCustomHash(100)) == 301)


# ============================================================
section("Overwriting __setattr__/__delattr__ on frozen raises")
# ============================================================

check_raises(
    "frozen with __setattr__ raises",
    TypeError,
    lambda: dataclass(
        type(
            "Bad",
            (),
            {
                "__annotations__": {"x": int},
                "__setattr__": lambda self, name, value: None,
            },
        ),
        frozen=True,
    ),
)

check_raises(
    "frozen with __delattr__ raises",
    TypeError,
    lambda: dataclass(
        type(
            "Bad",
            (),
            {
                "__annotations__": {"x": int},
                "__delattr__": lambda self, name: None,
            },
        ),
        frozen=True,
    ),
)


# ============================================================
section("Custom __setattr__ with frozen=False")
# ============================================================


@dataclass(frozen=False)
class CustomSetattr:
    x: int

    def __setattr__(self, name, value):
        self.__dict__["x"] = value * 2


check("custom __setattr__ used", CustomSetattr(10).x == 20)


# ============================================================
section("No dataclass fields")
# ============================================================


@dataclass
class NoFields:
    pass


nf = NoFields()
check("no fields len", len(fields(NoFields)) == 0)
check("no fields repr", repr(nf) == "NoFields()")


# ============================================================
section("Existing docstring not overridden")
# ============================================================


@dataclass
class HasDocstring:
    """My custom docstring."""

    x: int


check("existing docstring preserved", HasDocstring.__doc__ == "My custom docstring.")


# ============================================================
section("Overwritten __eq__ is kept")
# ============================================================


@dataclass
class CustomEq:
    x: int

    def __eq__(self, other):
        return other == 3


check("custom __eq__ used", CustomEq(1) == 3)
check("custom __eq__ negative", CustomEq(1) != 1)


# ============================================================
section("Overwriting order methods raises")
# ============================================================

check_raises(
    "order=True with __lt__ raises",
    TypeError,
    lambda: dataclass(
        type(
            "Bad",
            (),
            {
                "__annotations__": {"x": int},
                "__lt__": lambda self, other: True,
            },
        ),
        order=True,
    ),
)


# ============================================================
section("InitVar without default requires specification in replace()")
# ============================================================


@dataclass
class InitVarRequired:
    x: int
    y: InitVar[int]

    def __post_init__(self, y):
        self.x *= y


ivreq = InitVarRequired(1, 10)
check("InitVar required original", ivreq.x == 10)

check_raises(
    "replace without required InitVar raises",
    (TypeError, ValueError),
    lambda: replace(ivreq, x=3),
)

ivreq2 = replace(ivreq, x=3, y=5)
check("replace with required InitVar", ivreq2.x == 15)


# ============================================================
section("Weakref slot via make_dataclass")
# ============================================================

WrMdc = make_dataclass("WrMdc", [("a", int)], slots=True, weakref_slot=True)
check("weakref_slot in make_dataclass slots", "__weakref__" in WrMdc.__slots__)
wr_mdc_obj = WrMdc(1)
wr_mdc_ref = weakref.ref(wr_mdc_obj)
check("weakref via make_dataclass works", wr_mdc_ref() is wr_mdc_obj)

check_raises(
    "weakref_slot without slots in make_dataclass",
    TypeError,
    lambda: make_dataclass("Bad", [("a", int)], weakref_slot=True),
)


# ============================================================
section("Weakref slot subclass inherits weakref")
# ============================================================


@dataclass(slots=True, weakref_slot=True)
class WrBase:
    field_val: int


@dataclass(slots=True, weakref_slot=True)
class WrSubWithSlot(WrBase):
    pass


# __weakref__ should be in base, not sub
check("weakref in base slots", "__weakref__" in WrBase.__slots__)
check(
    "weakref not duplicated in sub slots", "__weakref__" not in WrSubWithSlot.__slots__
)
wr_sub = WrSubWithSlot(1)
wr_sub_ref = weakref.ref(wr_sub)
check("weakref subclass still works", wr_sub_ref() is wr_sub)


@dataclass(slots=True)
class WrSubWithoutSlot(WrBase):
    pass


# Even without weakref_slot, should be weakref-able via base
wr_sub2 = WrSubWithoutSlot(1)
wr_sub2_ref = weakref.ref(wr_sub2)
check("weakref subclass without weakref_slot", wr_sub2_ref() is wr_sub2)


# ============================================================
section("field kw_only attribute")
# ============================================================

# Verify the kw_only attribute on Field objects is set correctly


@dataclass(kw_only=True)
class FieldKwOnlyAttr:
    a: int


check("kw_only=True sets field.kw_only", fields(FieldKwOnlyAttr)[0].kw_only)


@dataclass(kw_only=True)
class FieldKwOnlyAttrOverride:
    a: int = field(kw_only=False)


check(
    "kw_only=True field override to False",
    not fields(FieldKwOnlyAttrOverride)[0].kw_only,
)


@dataclass
class FieldKwOnlyAttrDefault:
    a: int


check(
    "default kw_only is False on field",
    not fields(FieldKwOnlyAttrDefault)[0].kw_only,
)


# ============================================================
section("KW_ONLY with __post_init__ and InitVar")
# ============================================================


@dataclass
class KwOnlyPostInit:
    a: int
    _: KW_ONLY
    b: InitVar[int]
    c: int
    d: InitVar[int]

    def __post_init__(self, b, d):
        self.a = b
        self.c = d


kopi = KwOnlyPostInit(1, c=2, b=3, d=4)
check(
    "KW_ONLY post_init with InitVar",
    kopi.a == 3 and kopi.c == 4,
)


# ============================================================
section("fields() on non-dataclass raises TypeError")
# ============================================================

check_raises("fields(0) raises", TypeError, lambda: fields(0))
check_raises("fields(int) raises", TypeError, lambda: fields(int))

_stdout = io.StringIO()
try:
    fields(object)
except TypeError as exc:
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=_stdout)

_printed = _stdout.getvalue()
check("fields() clean traceback", "AttributeError" not in _printed)
check(
    "fields() clean traceback no __dataclass_fields__",
    "__dataclass_fields__" not in _printed,
)


# ============================================================
section("is_dataclass on non-decorated subclass")
# ============================================================


@dataclass
class IsDataclassBase:
    y: int


class IsDataclassSub(IsDataclassBase):
    pass


check("is_dataclass on subclass class", is_dataclass(IsDataclassSub))
check("is_dataclass on subclass instance", is_dataclass(IsDataclassSub(y=5)))


# ============================================================
section("Non-default after default error includes field name")
# ============================================================

try:
    dataclass(type("Bad", (), {"__annotations__": {"x": int, "y": int}, "x": 0}))
    check("non-default after default error msg", False)
except TypeError as e:
    msg = str(e)
    check("error mentions non-default field name", "'y'" in msg or "y" in msg)


# ============================================================
section("Frozen multiple inheritance rules")
# ============================================================

# non-frozen from frozen base raises
check_raises(
    "non-frozen child of frozen raises",
    TypeError,
    lambda: dataclass(type("Bad", (FrozenParent,), {"__annotations__": {"j": int}})),
)

# frozen from non-frozen base raises
check_raises(
    "frozen child of non-frozen raises",
    TypeError,
    lambda: dataclass(
        type("Bad", (Parent,), {"__annotations__": {"j": int}}), frozen=True
    ),
)


# ============================================================
section("Slots with inherited __dict__")
# ============================================================


class WithDictSlot:
    __slots__ = ("__dict__",)


@dataclass(slots=True)
class InheritsDictSlot(WithDictSlot):
    pass


check(
    "inherited __dict__ slot not duplicated",
    "__dict__" not in InheritsDictSlot.__slots__,
)
check("inherited __dict__ slot works", InheritsDictSlot().__dict__ == {})


# ============================================================
section("asdict()/astuple() with namedtuple values")
# ============================================================

# bpo-34363: namedtuples must be rebuilt with positional args, and the
# result keeps the namedtuple type.

PointNT = namedtuple("PointNT", "x y")


@dataclass
class WithNamedTuple:
    pt: PointNT


wnt = WithNamedTuple(PointNT(1, 2))
wnt_d = asdict(wnt)
check("asdict namedtuple keeps type", type(wnt_d["pt"]) is PointNT)
check("asdict namedtuple values", wnt_d["pt"] == PointNT(1, 2))

wnt_t = astuple(wnt)
check("astuple namedtuple keeps type", type(wnt_t[0]) is PointNT)
check("astuple namedtuple values", wnt_t == (PointNT(1, 2),))


@dataclass
class InsideNamedTuple:
    v: int


wnt_nested = WithNamedTuple(PointNT(InsideNamedTuple(1), 2))
check(
    "asdict recurses into namedtuple members",
    asdict(wnt_nested)["pt"] == PointNT({"v": 1}, 2),
)
check(
    "astuple recurses into namedtuple members",
    astuple(wnt_nested) == (PointNT((1,), 2),),
)


# ============================================================
section("Zero-argument super() with slots=True")
# ============================================================

# gh-90562: slots=True creates a new class, so methods' __class__
# closure cells must be repointed for zero-argument super() to work.


class SuperGreetBase:
    def greet(self):
        return "base"


@dataclass(slots=True)
class SuperGreetChild(SuperGreetBase):
    x: int

    def greet(self):
        return "child:" + super().greet()

    def own_class(self):
        return __class__


sgc = SuperGreetChild(1)
check("zero-arg super() works with slots", sgc.greet() == "child:base")
check("__class__ points at the slots class", sgc.own_class() is SuperGreetChild)


@dataclass(slots=True)
class SuperGreetProperty(SuperGreetBase):
    x: int

    @property
    def label(self):
        return super().greet() + "!"


check("super() in property with slots", SuperGreetProperty(1).label == "base!")


@dataclass(slots=True, frozen=True)
class SuperGreetFrozen(SuperGreetBase):
    x: int

    def greet(self):
        return "frozen:" + super().greet()


check("super() with frozen+slots", SuperGreetFrozen(1).greet() == "frozen:base")


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
