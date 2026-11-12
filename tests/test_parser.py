import pytest

from plain.errors import PlainSyntaxError, PlainIncomplete
from plain.ast_nodes import (
    SetVar, SetItem, ChangeBy, If, While, Repeat, ForEach, CountLoop,
    Say, Write, Ask, MakeList, AddTo, RemoveLast, RemoveItem, SortList,
    ReverseList, FunctionDef, RunCall, TryBlock, UseFile, WaitStmt,
    GiveBack, StopLoop, SkipOne,
    Number, TextLiteral, Bool, Nothing, Var, ListLiteral, BinOp, Compare,
    Contains, Joined, And, Or, Not, Negative, SquareRoot, AbsoluteValue,
    Rounded, LargerOf, SmallerOf, ItemOf, LengthOf, FirstItemOf,
    LastItemOf, UppercaseOf, LowercaseOf, ToText, ToNumber, Call,
    RandomNumber, CurrentTime, SplitText, ReadFile, WriteFile, TheProblem,
)

from conftest import parse_src


def first(src):
    return parse_src(src).statements[0]


class TestStatements:
    def test_set(self):
        node = first("Set total score to 10.")
        assert isinstance(node, SetVar)
        assert node.name == "total score"
        assert isinstance(node.value, Number)

    def test_set_item(self):
        node = first("Set item 2 of scores to 99.")
        assert isinstance(node, SetItem)
        assert node.name == "scores"

    def test_change(self):
        node = first("Change score by negative 2.")
        assert isinstance(node, ChangeBy)
        assert isinstance(node.amount, Negative)

    def test_if(self):
        node = first("If score is greater than 5, then Say text big end text. end if.")
        assert isinstance(node, If)
        assert len(node.branches) == 1
        assert node.otherwise == []

    def test_if_full_chain(self):
        src = ("If alpha is equal to 1, then Say text one end text. "
               "otherwise if alpha is equal to 2, then Say text two end text. "
               "otherwise Say text many end text. end if.")
        node = first(src)
        assert isinstance(node, If)
        assert len(node.branches) == 2
        assert len(node.otherwise) == 1

    def test_while(self):
        node = first("While count is less than 10, Change count by 1. end loop.")
        assert isinstance(node, While)

    def test_repeat(self):
        node = first("Repeat 10 times, Say text knock end text. end loop.")
        assert isinstance(node, Repeat)

    def test_for_each(self):
        node = first("For each item in shopping list, Say item. end loop.")
        assert isinstance(node, ForEach)
        assert node.name == "item"

    def test_for_each_named(self):
        node = first("For each thing in shopping list, Say thing. end loop.")
        assert isinstance(node, ForEach)
        assert node.name == "thing"

    def test_count(self):
        node = first("Count from 1 to 10 using i, Say i. end loop.")
        assert isinstance(node, CountLoop)
        assert node.step is None

    def test_count_by(self):
        node = first("Count from 1 to 10 using i by 2, Say i. end loop.")
        assert isinstance(node, CountLoop)
        assert isinstance(node.step, Number)

    def test_say_multiple(self):
        node = first("Say text Total is end text, total.")
        assert isinstance(node, Say)
        assert len(node.args) == 2

    def test_write(self):
        node = first("Write text loading end text.")
        assert isinstance(node, Write)

    def test_ask_text(self):
        node = first("Ask the user for age.")
        assert isinstance(node, Ask)
        assert node.kind == "text"
        assert node.name == "age"

    def test_ask_number(self):
        node = first("Ask the user for a number called age.")
        assert isinstance(node, Ask)
        assert node.kind == "number"

    def test_make_list(self):
        node = first("Make a list called scores holding 5, 10, 15.")
        assert isinstance(node, MakeList)
        assert len(node.items) == 3

    def test_make_empty_list(self):
        node = first("Make a list called scores.")
        assert isinstance(node, MakeList)
        assert node.items == []

    def test_add(self):
        node = first("Add 20 to scores.")
        assert isinstance(node, AddTo)

    def test_remove_last(self):
        node = first("Remove the last item from scores.")
        assert isinstance(node, RemoveLast)

    def test_remove_item(self):
        node = first("Remove item 2 from scores.")
        assert isinstance(node, RemoveItem)

    def test_sort_and_reverse(self):
        assert isinstance(first("Sort scores."), SortList)
        assert isinstance(first("Reverse scores."), ReverseList)

    def test_function(self):
        node = first("To add numbers with first and second, do give back first plus second. end function.")
        assert isinstance(node, FunctionDef)
        assert node.name == "add numbers"
        assert node.params == ["first", "second"]
        assert isinstance(node.body[0], GiveBack)

    def test_function_no_params(self):
        node = first("To greet, do Say text hi end text. end function.")
        assert isinstance(node, FunctionDef)
        assert node.params == []

    def test_run(self):
        node = first("Run greet with text Bob end text.")
        assert isinstance(node, RunCall)
        assert len(node.args) == 1

    def test_run_no_args(self):
        node = first("Run cleanup.")
        assert isinstance(node, RunCall)
        assert node.args == []

    def test_try(self):
        node = first("Try, Set x to 1. if something goes wrong, Say text no end text. end try.")
        assert isinstance(node, TryBlock)
        assert len(node.body) == 1
        assert len(node.handler) == 1

    def test_use(self):
        node = first("Use the file text helpers.pln end text.")
        assert isinstance(node, UseFile)
        assert node.filename == "helpers.pln"

    def test_wait(self):
        node = first("Wait 2 seconds.")
        assert isinstance(node, WaitStmt)

    def test_stop_and_skip(self):
        src = "Repeat 5 times, Stop the loop. end loop."
        assert isinstance(first(src), Repeat)
        src = "Repeat 5 times, Skip to the next one. end loop."
        assert isinstance(first(src), Repeat)


class TestExpressions:
    def test_decimal(self):
        node = first("Set x to 3 point 14.")
        assert isinstance(node.value, Number)
        assert node.value.value == 3.14

    def test_negative(self):
        node = first("Set x to negative 5.")
        assert isinstance(node.value, Negative)
        assert isinstance(node.value.value, Number)

    def test_literals(self):
        assert isinstance(first("Set x to yes.").value, Bool)
        assert isinstance(first("Set x to no.").value, Bool)
        assert isinstance(first("Set x to nothing.").value, Nothing)
        assert isinstance(first("Set x to text hi end text.").value, TextLiteral)

    def test_precedence_times_before_plus(self):
        node = first("Set x to 2 plus 3 times 4.")
        assert node.value.op == "plus"
        assert node.value.right.op == "times"

    def test_power_is_right_associative(self):
        node = first("Set x to 2 to the power of 3 to the power of 2.")
        assert node.value.op == "power"
        assert node.value.right.op == "power"

    def test_power_binds_tighter_than_times(self):
        node = first("Set x to 2 times 3 to the power of 2.")
        assert node.value.op == "times"
        assert node.value.right.op == "power"

    def test_group_forces_order(self):
        node = first("Set x to group 2 plus 3 end group times 4.")
        assert node.value.op == "times"
        assert node.value.left.op == "plus"

    def test_joined_with_binds_looser_than_plus(self):
        node = first("Set x to text a end text joined with text b end text joined with text c end text.")
        assert isinstance(node.value, Joined)

    def test_not_binds_looser_than_comparison(self):
        node = first("If not score is greater than 5, then Say text no end text. end if.")
        condition = node.branches[0][0]
        assert isinstance(condition, Not)
        assert isinstance(condition.value, Compare)

    def test_comparison_ops(self):
        for src, op in [
            ("is equal to", "equal"), ("is not equal to", "not_equal"),
            ("is greater than", "greater"), ("is less than", "less"),
            ("is at least", "at_least"), ("is at most", "at_most"),
        ]:
            node = first("If x %s y, then Say text ok end text. end if." % src)
            assert node.branches[0][0].op == op

    def test_contains(self):
        node = first("If scores contains 10, then Say text yes end text. end if.")
        assert isinstance(node.branches[0][0], Contains)

    def test_larger_and_smaller(self):
        node = first("Set x to the larger of 3 and 9.")
        assert isinstance(node.value, LargerOf)
        node = first("Set x to the smaller of 3 and 9.")
        assert isinstance(node.value, SmallerOf)

    def test_larger_of_takes_and_as_separator_not_logic(self):
        node = first("Set x to the larger of 1 plus 2 and 4.")
        assert isinstance(node.value, LargerOf)
        assert isinstance(node.value.left, BinOp)

    def test_math_words(self):
        assert isinstance(first("Set x to 7 divided by 2.").value, BinOp)
        assert first("Set x to 7 divided by 2.").value.op == "divided"
        assert first("Set x to 7 remainder of 2.").value.op == "remainder"

    def test_unary_helpers(self):
        assert isinstance(first("Set x to the square root of 16.").value, SquareRoot)
        assert isinstance(first("Set x to the absolute value of negative 3.").value, AbsoluteValue)
        assert isinstance(first("Set x to 3 point 7 rounded.").value, Rounded)
        assert isinstance(first("Set x to the length of text hi end text.").value, LengthOf)
        assert isinstance(first("Set x to uppercase of name.").value, UppercaseOf)
        assert isinstance(first("Set x to lowercase of name.").value, LowercaseOf)

    def test_item_of(self):
        node = first("Say item 1 of scores.")
        arg = node.args[0]
        assert isinstance(arg, ItemOf)
        assert isinstance(arg.container, Var)

    def test_nested_item_of(self):
        node = first("Say item 2 of item 1 of grid.")
        arg = node.args[0]
        assert isinstance(arg.container, ItemOf)

    def test_first_and_last_item(self):
        assert isinstance(first("Say the first item of scores.").args[0], FirstItemOf)
        assert isinstance(first("Say the last item of scores.").args[0], LastItemOf)

    def test_call_in_expression(self):
        node = first("Set answer to the result of add numbers with 3 and 4.")
        call = node.value
        assert isinstance(call, Call)
        assert call.name == "add numbers"
        assert len(call.args) == 2

    def test_call_argument_stops_before_another_call(self):
        node = first("Set x to the result of f with n minus 1 plus the result of g with n minus 2.")
        left = node.value.left
        right = node.value.right
        assert isinstance(left, Call)
        assert isinstance(right, Call)
        assert left.args[0].op == "minus"

    def test_list_literal_expression(self):
        node = first("Set x to a list holding 1, 2, 3.")
        assert isinstance(node.value, ListLiteral)
        assert len(node.value.items) == 3

    def test_nested_list_literal(self):
        # commas belong to the nearest open list, so the inner list wins
        node = first("Set grid to a list holding a list holding 1, 2, a list holding 3, 4.")
        outer = node.value
        assert len(outer.items) == 1
        inner = outer.items[0]
        assert isinstance(inner, ListLiteral)
        assert len(inner.items) == 3
        assert isinstance(inner.items[2], ListLiteral)

    def test_random_number(self):
        node = first("Set x to random number from 1 to 10.")
        assert isinstance(node.value, RandomNumber)

    def test_split(self):
        node = first("Set pieces to split sentence by text , end text.")
        assert isinstance(node.value, SplitText)

    def test_read_and_write_file(self):
        assert isinstance(first("Set data to read file text a.txt end text.").value, ReadFile)
        node = first("Write file text a.txt end text with text hi end text.")
        assert isinstance(node.value, WriteFile)

    def test_versions(self):
        assert isinstance(first("Set x to the text version of 42.").value, ToText)
        assert isinstance(first("Set x to the number version of text 42 end text.").value, ToNumber)


class TestGrammarErrors:
    def test_missing_period(self):
        with pytest.raises(PlainSyntaxError):
            parse_src("Set x to 5")

    def test_missing_end_if(self):
        with pytest.raises(PlainIncomplete):
            parse_src("If x is equal to 1, then Say text a end text.")

    def test_missing_end_loop(self):
        with pytest.raises(PlainIncomplete):
            parse_src("Repeat 3 times, Say text a end text.")

    def test_unknown_statement_word(self):
        with pytest.raises(PlainSyntaxError) as exc:
            parse_src("Frobnicate the widget.")
        assert "Frobnicate" in str(exc.value)

    def test_give_back_outside_function(self):
        with pytest.raises(PlainSyntaxError):
            parse_src("give back 5.")

    def test_stop_outside_loop(self):
        with pytest.raises(PlainSyntaxError):
            parse_src("Stop the loop.")

    def test_skip_outside_loop(self):
        with pytest.raises(PlainSyntaxError):
            parse_src("Skip to the next one.")

    def test_double_comparison_rejected(self):
        with pytest.raises(PlainSyntaxError):
            parse_src("If 1 is less than 2 is less than 3, then Say text x end text. end if.")

    def test_missing_then(self):
        with pytest.raises(PlainSyntaxError):
            parse_src("If x is equal to 1, Say text a end text. end if.")

    def test_missing_of_after_item(self):
        with pytest.raises(PlainSyntaxError):
            parse_src("Say item 1 scores.")

    def test_incomplete_expression_at_eof(self):
        with pytest.raises(PlainIncomplete):
            parse_src("Set x to 1 plus")

    def test_statement_cannot_start_with_number(self):
        with pytest.raises(PlainSyntaxError) as exc:
            parse_src("Set x to 3. 14 more.")
        assert "point" in str(exc.value)
