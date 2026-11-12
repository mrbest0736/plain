"""AST node classes for the Plain language.

Every node carries the line it came from so that errors can point at it.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


class Node:
    line = 0


# --- program ---------------------------------------------------------------

@dataclass
class Program(Node):
    statements: List[Any] = field(default_factory=list)


# --- statements -------------------------------------------------------------

@dataclass
class SetVar(Node):
    name: str
    value: Any


@dataclass
class SetItem(Node):
    name: str
    index: Any
    value: Any


@dataclass
class ChangeBy(Node):
    name: str
    amount: Any


@dataclass
class If(Node):
    branches: List[Tuple[Any, List[Any]]]  # (condition, statements)
    otherwise: List[Any]


@dataclass
class While(Node):
    condition: Any
    body: List[Any]


@dataclass
class Repeat(Node):
    count: Any
    body: List[Any]


@dataclass
class ForEach(Node):
    name: str
    iterable: Any
    body: List[Any]


@dataclass
class CountLoop(Node):
    start: Any
    stop: Any
    name: str
    step: Optional[Any]
    body: List[Any]


@dataclass
class Say(Node):
    args: List[Any]


@dataclass
class Write(Node):
    args: List[Any]


@dataclass
class Ask(Node):
    name: str
    kind: str  # "text" or "number"


@dataclass
class MakeList(Node):
    name: str
    items: List[Any]


@dataclass
class AddTo(Node):
    value: Any
    name: str


@dataclass
class RemoveLast(Node):
    name: str


@dataclass
class RemoveItem(Node):
    index: Any
    name: str


@dataclass
class SortList(Node):
    name: str


@dataclass
class ReverseList(Node):
    name: str


@dataclass
class FunctionDef(Node):
    name: str
    params: List[str]
    body: List[Any]


@dataclass
class RunCall(Node):
    name: str
    args: List[Any]


@dataclass
class TryBlock(Node):
    body: List[Any]
    handler: Optional[List[Any]]


@dataclass
class UseFile(Node):
    filename: str


@dataclass
class WaitStmt(Node):
    seconds: Any


@dataclass
class GiveBack(Node):
    value: Any


@dataclass
class Discard(Node):
    value: Any


@dataclass
class StopLoop(Node):
    pass


@dataclass
class SkipOne(Node):
    pass


# --- expressions ------------------------------------------------------------

@dataclass
class Number(Node):
    value: Any  # int or float


@dataclass
class TextLiteral(Node):
    value: str


@dataclass
class Bool(Node):
    value: bool


@dataclass
class Nothing(Node):
    pass


@dataclass
class Var(Node):
    name: str


@dataclass
class ListLiteral(Node):
    items: List[Any]


@dataclass
class BinOp(Node):
    op: str  # plus minus times divided remainder power
    left: Any
    right: Any


@dataclass
class Compare(Node):
    op: str  # equal not_equal greater less at_least at_most
    left: Any
    right: Any


@dataclass
class Contains(Node):
    left: Any
    right: Any


@dataclass
class Joined(Node):
    left: Any
    right: Any


@dataclass
class And(Node):
    left: Any
    right: Any


@dataclass
class Or(Node):
    left: Any
    right: Any


@dataclass
class Not(Node):
    value: Any


@dataclass
class Negative(Node):
    value: Any


@dataclass
class SquareRoot(Node):
    value: Any


@dataclass
class AbsoluteValue(Node):
    value: Any


@dataclass
class Rounded(Node):
    value: Any


@dataclass
class LargerOf(Node):
    left: Any
    right: Any


@dataclass
class SmallerOf(Node):
    left: Any
    right: Any


@dataclass
class ItemOf(Node):
    index: Any
    container: Any


@dataclass
class LengthOf(Node):
    value: Any


@dataclass
class FirstItemOf(Node):
    value: Any


@dataclass
class LastItemOf(Node):
    value: Any


@dataclass
class UppercaseOf(Node):
    value: Any


@dataclass
class LowercaseOf(Node):
    value: Any


@dataclass
class ToText(Node):
    value: Any


@dataclass
class ToNumber(Node):
    value: Any


@dataclass
class Call(Node):
    name: str
    args: List[Any]


@dataclass
class RandomNumber(Node):
    start: Any
    stop: Any


@dataclass
class CurrentTime(Node):
    pass


@dataclass
class SplitText(Node):
    value: Any
    separator: Any


@dataclass
class ReadFile(Node):
    path: Any


@dataclass
class WriteFile(Node):
    path: Any
    content: Any


@dataclass
class TheProblem(Node):
    pass
