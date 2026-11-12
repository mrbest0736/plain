import os

import pytest

from plain.errors import PlainRuntimeError, PlainSyntaxError
from plain import builtins

from conftest import run_src, run_error, parse_src


class TestVariables:
    def test_set_and_say(self):
        assert run_src("Set score to 10. Say score.") == "10\n"

    def test_change(self):
        src = "Set score to 10. Change score by 5. Say score."
        assert run_src(src) == "15\n"

    def test_change_negative(self):
        src = "Set score to 10. Change score by negative 2. Say score."
        assert run_src(src) == "8\n"

    def test_multiword_names(self):
        src = "Set total score to 99. Say total score."
        assert run_src(src) == "99\n"

    def test_undefined_variable(self):
        error = run_error("Say mystery value.")
        assert "could not find a variable called mystery value" in str(error)

    def test_kinds(self):
        src = ("Set n to 42. Set d to 3 point 5. Set t to text hi end text. "
               "Set y to yes. Set e to nothing. Say n, d, t, y, e.")
        assert run_src(src) == "42 3.5 hi yes nothing\n"


class TestMath:
    def test_operators(self):
        src = ("Say 2 plus 3. Say 7 minus 4. Say 6 times 7. Say 7 divided by 2. "
               "Say 7 remainder of 3. Say 2 to the power of 10.")
        assert run_src(src) == "5\n3\n42\n3.5\n1\n1024\n"

    def test_precedence(self):
        assert run_src("Say 2 plus 3 times 4.") == "14\n"
        assert run_src("Say group 2 plus 3 end group times 4.") == "20\n"

    def test_power_right_associative(self):
        assert run_src("Say 2 to the power of 3 to the power of 2.") == "512\n"

    def test_negative_numbers(self):
        assert run_src("Say negative 5. Say 3 minus negative 2.") == "-5\n5\n"

    def test_square_root(self):
        assert run_src("Say the square root of 16.") == "4\n"

    def test_square_root_of_negative(self):
        error = run_error("Say the square root of negative 9.")
        assert "square root" in str(error)

    def test_absolute_value(self):
        assert run_src("Say the absolute value of negative 5.") == "5\n"

    def test_rounded(self):
        assert run_src("Say 3 point 7 rounded. Say 2 point 5 rounded. Say negative 2 point 5 rounded.") == "4\n3\n-3\n"

    def test_larger_smaller(self):
        assert run_src("Say the larger of 3 and 9. Say the smaller of 3 and 9.") == "9\n3\n"

    def test_larger_of_text(self):
        assert run_src("Say the larger of text apple end text and text banana end text.") == "banana\n"

    def test_plus_on_text_suggests_joined_with(self):
        error = run_error("Say text a end text plus text b end text.")
        assert "joined with" in str(error)

    def test_divide_by_zero(self):
        error = run_error("Set x to 5 divided by 0.")
        assert "divide" in str(error).lower() and "zero" in str(error).lower()

    def test_decimal_display(self):
        assert run_src("Say 1 divided by 4.") == "0.25\n"
        assert run_src("Say 6 divided by 2.") == "3\n"


class TestComparisonsAndLogic:
    def test_comparisons(self):
        src = ("Say 1 is equal to 1. Say 1 is equal to 1 point 0. Say 1 is not equal to 2. "
               "Say 3 is greater than 2. Say 2 is less than 3. Say 2 is at least 2. Say 2 is at most 1.")
        assert run_src(src) == "yes\nyes\nyes\nyes\nyes\nyes\nno\n"

    def test_text_comparison(self):
        assert run_src("Say text apple end text is equal to text apple end text.") == "yes\n"
        assert run_src("Say text apple end text is less than text banana end text.") == "yes\n"

    def test_mixed_types_not_equal(self):
        assert run_src("Say 1 is equal to text 1 end text.") == "no\n"
        assert run_src("Say yes is equal to 1.") == "no\n"

    def test_and_or_not(self):
        src = ("Say yes and yes. Say yes and no. Say no or yes. Say no or no. "
               "Say not yes. Say not no.")
        assert run_src(src) == "yes\nno\nyes\nno\nno\nyes\n"

    def test_condition_must_be_yes_or_no(self):
        error = run_error("If 5, then Say text hi end text. end if.")
        assert "yes or no" in str(error)


class TestTextHelpers:
    def test_joined_with(self):
        assert run_src("Say text Total is end text joined with text  42 end text.") == "Total is 42\n"

    def test_joined_with_number(self):
        assert run_src("Say text score, end text joined with text  10 end text.") == "score, 10\n"

    def test_length(self):
        assert run_src("Say the length of text hello end text.") == "5\n"
        assert run_src("Make a list called l holding 1, 2, 3. Say the length of l.") == "3\n"

    def test_uppercase_lowercase(self):
        src = "Say uppercase of text hi there end text. Say lowercase of text HI THERE end text."
        assert run_src(src) == "HI THERE\nhi there\n"

    def test_contains_text(self):
        assert run_src("Say text hello world end text contains text o w end text.") == "yes\n"
        assert run_src("Say text hello end text contains text z end text.") == "no\n"

    def test_versions(self):
        assert run_src("Say the text version of 42.") == "42\n"
        assert run_src("Say the number version of text 42 end text plus 1.") == "43\n"
        assert run_src("Say the number version of text 3 point 5 end text.") == "3.5\n"
        assert run_src("Say the text version of yes.") == "yes\n"
        assert run_src("Say the text version of nothing.") == "nothing\n"

    def test_bad_number_version(self):
        error = run_error("Set x to the number version of text hello end text.")
        assert "number" in str(error)


class TestConditions:
    def test_if_otherwise(self):
        src = ("Set score to 7. "
               "If score is greater than 5, then Say text big end text. "
               "otherwise Say text small end text. end if.")
        assert run_src(src) == "big\n"

    def test_otherwise_if_chain(self):
        src = ("Set score to 5. "
               "If score is greater than 5, then Say text big end text. "
               "otherwise if score is equal to 5, then Say text five end text. "
               "otherwise Say text small end text. end if.")
        assert run_src(src) == "five\n"

    def test_no_branch_taken(self):
        src = "If no, then Say text a end text. end if. Say text done end text."
        assert run_src(src) == "done\n"


class TestLoops:
    def test_repeat(self):
        src = "Set n to 0. Repeat 4 times, Change n by 1. end loop. Say n."
        assert run_src(src) == "4\n"

    def test_while(self):
        src = ("Set count to 1. "
               "While count is less than 4, Say count. Change count by 1. end loop.")
        assert run_src(src) == "1\n2\n3\n"

    def test_for_each(self):
        src = ("Make a list called shopping list holding text apples end text, text pears end text. "
               "For each item in shopping list, Say item. end loop.")
        assert run_src(src) == "apples\npears\n"

    def test_for_each_named_variable(self):
        src = ("Make a list called l holding 1, 2. "
               "For each thing in l, Say thing. end loop.")
        assert run_src(src) == "1\n2\n"

    def test_count(self):
        src = "Count from 1 to 4 using i, Say i. end loop."
        assert run_src(src) == "1\n2\n3\n4\n"

    def test_count_by(self):
        src = "Count from 1 to 10 using i by 3, Say i. end loop."
        assert run_src(src) == "1\n4\n7\n10\n"

    def test_count_backwards(self):
        src = "Count from 3 to 1 using i by negative 1, Say i. end loop."
        assert run_src(src) == "3\n2\n1\n"

    def test_stop_the_loop(self):
        src = ("Set n to 0. "
               "Repeat 100 times, Change n by 1. If n is equal to 3, then Stop the loop. end if. end loop. "
               "Say n.")
        assert run_src(src) == "3\n"

    def test_skip_to_the_next_one(self):
        src = ("Count from 1 to 5 using i, "
               "If i is equal to 3, then Skip to the next one. end if. Say i. end loop.")
        assert run_src(src) == "1\n2\n4\n5\n"

    def test_for_each_over_non_list(self):
        error = run_error("For each item in 5, Say item. end loop.")
        assert "list" in str(error)


class TestLists:
    def test_make_and_say(self):
        src = "Make a list called scores holding 5, 10, 15. Say scores."
        assert run_src(src) == "[5, 10, 15]\n"

    def test_mixed_types(self):
        src = ("Make a list called things holding 1, text two end text, yes, nothing. Say things.")
        assert run_src(src) == "[1, two, yes, nothing]\n"

    def test_add(self):
        src = "Make a list called scores holding 5. Add 20 to scores. Say scores."
        assert run_src(src) == "[5, 20]\n"

    def test_item_of_one_based(self):
        src = "Make a list called scores holding 5, 10, 15. Say item 1 of scores. Say item 3 of scores."
        assert run_src(src) == "5\n15\n"

    def test_item_out_of_range(self):
        src = "Make a list called scores holding 5, 10, 15. Say item 4 of scores."
        error = run_error(src)
        assert "item 4" in str(error) and "3 items" in str(error)

    def test_set_item(self):
        src = "Make a list called scores holding 5, 10, 15. Set item 2 of scores to 99. Say scores."
        assert run_src(src) == "[5, 99, 15]\n"

    def test_remove_last(self):
        src = "Make a list called scores holding 5, 10, 15. Remove the last item from scores. Say scores."
        assert run_src(src) == "[5, 10]\n"

    def test_remove_item(self):
        src = "Make a list called scores holding 5, 10, 15. Remove item 2 from scores. Say scores."
        assert run_src(src) == "[5, 15]\n"

    def test_remove_from_empty(self):
        src = "Make a list called scores. Remove the last item from scores."
        error = run_error(src)
        assert "empty" in str(error)

    def test_sort_numbers(self):
        src = "Make a list called s holding 3, 1, 2. Sort s. Say s."
        assert run_src(src) == "[1, 2, 3]\n"

    def test_sort_text(self):
        src = "Make a list called s holding text c end text, text a end text, text b end text. Sort s. Say s."
        assert run_src(src) == "[a, b, c]\n"

    def test_sort_mixed_fails(self):
        src = "Make a list called s holding 1, text a end text. Sort s."
        error = run_error(src)
        assert "sort" in str(error)

    def test_reverse(self):
        src = "Make a list called s holding 1, 2, 3. Reverse s. Say s."
        assert run_src(src) == "[3, 2, 1]\n"

    def test_first_last(self):
        src = "Make a list called s holding 5, 10, 15. Say the first item of s. Say the last item of s."
        assert run_src(src) == "5\n15\n"

    def test_contains_list(self):
        src = "Make a list called s holding 5, 10. Say s contains 10. Say s contains 7."
        assert run_src(src) == "yes\nno\n"

    def test_nested_lists(self):
        src = ("Make a list called grid holding a list holding 1, 2, a list holding 3, 4. "
               "Say item 2 of item 1 of grid. Say the length of grid.")
        assert run_src(src) == "2\n1\n"

    def test_list_of_lists_display(self):
        src = "Make a list called grid holding a list holding 1, 2. Say grid."
        assert run_src(src) == "[[1, 2]]\n"

    def test_add_to_non_list(self):
        error = run_error("Set x to 5. Add 1 to x.")
        assert "not a list" in str(error)


class TestFunctions:
    def test_params_and_return(self):
        src = ("To add numbers with first and second, do give back first plus second. end function. "
               "Set answer to the result of add numbers with 3 and 4. Say answer.")
        assert run_src(src) == "7\n"

    def test_run_statement(self):
        src = "To greet with name, do Say text hi end text, name. end function. Run greet with text Bob end text."
        assert run_src(src) == "hi Bob\n"

    def test_no_return_gives_nothing(self):
        src = ("To prepare, do Set x to 1. end function. "
               "Set result to the result of prepare. Say result.")
        assert run_src(src) == "nothing\n"

    def test_recursion(self):
        src = ("To factorial with n, do "
               "If n is at most 1, then give back 1. end if. "
               "give back n times the result of factorial with n minus 1. "
               "end function. "
               "Say the result of factorial with 5.")
        assert run_src(src) == "120\n"

    def test_local_variables(self):
        src = ("Set x to 1. "
               "To hide x, do Set x to 99. Say x. end function. "
               "Run hide x. Say x.")
        assert run_src(src) == "99\n1\n"

    def test_closure_over_globals(self):
        src = ("Set counter to 0. "
               "To bump counter up, do Change counter by 1. end function. "
               "Run bump counter up. Run bump counter up. Say counter.")
        assert run_src(src) == "2\n"

    def test_undefined_function(self):
        error = run_error("Run mystery.")
        assert "could not find a function called mystery" in str(error)

    def test_wrong_argument_count(self):
        src = "To f with alpha and beta, do give back 1. end function. Run f with 1."
        error = run_error(src)
        assert "expects 2 inputs" in str(error)


class TestInputOutput:
    def test_say_joins_with_spaces(self):
        assert run_src("Say text a end text, 1, yes.") == "a 1 yes\n"

    def test_write_no_newline(self):
        assert run_src("Write text a end text. Write text b end text. Say text c end text.") == "abc\n"

    def test_ask_text(self):
        assert run_src("Ask the user for name. Say text hi end text, name.", inputs=["Ada"]) == "hi Ada\n"

    def test_ask_number(self):
        assert run_src("Ask the user for a number called age. Say age.", inputs=["42"]) == "42\n"

    def test_ask_number_reasks_on_bad_input(self):
        out = run_src("Ask the user for a number called age. Say age.", inputs=["abc", "42"])
        assert "That is not a number." in out
        assert out.endswith("42\n")

    def test_ask_number_accepts_negative_and_decimal(self):
        assert run_src("Ask the user for a number called n. Say n.", inputs=["negative 5"]) == "-5\n"
        assert run_src("Ask the user for a number called n. Say n.", inputs=["3.5"]) == "3.5\n"


class TestBuiltins:
    def test_random_within_bounds(self):
        src = ("Set hits to 0. Repeat 50 times, "
               "Set r to random number from 1 to 10. "
               "If r is at least 1 and r is at most 10, then Change hits by 1. end if. "
               "end loop. Say hits.")
        assert run_src(src) == "50\n"

    def test_current_time_is_number(self):
        out = run_src("Set t to the current time. Say the text version of t is equal to nothing.")
        assert out == "no\n"

    def test_wait(self, monkeypatch):
        slept = []
        monkeypatch.setattr(builtins._time, "sleep", slept.append)
        run_src("Wait 2 seconds.")
        assert slept == [2]

    def test_split(self):
        src = ("Set pieces to split text a,b,c end text by text , end text. "
               "Say the length of pieces. Say item 2 of pieces.")
        assert run_src(src) == "3\nb\n"

    def test_read_write_file(self, tmp_path):
        main = tmp_path / "main.pln"
        src = ("Write file text notes.txt end text with text hello file end text. "
               "Say read file text notes.txt end text.")
        assert run_src(src, filename=str(main)) == "hello file\n"
        assert (tmp_path / "notes.txt").read_text() == "hello file"

    def test_read_missing_file(self, tmp_path):
        main = tmp_path / "main.pln"
        error = run_error("Say read file text nope.txt end text.", filename=str(main))
        assert "could not find a file" in str(error)


class TestUseFile:
    def test_import(self, tmp_path):
        helper = tmp_path / "helpers.pln"
        helper.write_text("To triple with n, do give back n times 3. end function.\n")
        main = tmp_path / "main.pln"
        source = "Use the file text helpers.pln end text. Say the result of triple with 7."
        assert run_src(source, filename=str(main)) == "21\n"

    def test_import_runs_once(self, tmp_path):
        helper = tmp_path / "helpers.pln"
        helper.write_text("Set loaded to yes.\n")
        main = tmp_path / "main.pln"
        source = ("Use the file text helpers.pln end text. "
                  "Set loaded to text changed later end text. "
                  "Use the file text helpers.pln end text. Say loaded.")
        assert run_src(source, filename=str(main)) == "changed later\n"

    def test_import_missing(self, tmp_path):
        main = tmp_path / "main.pln"
        error = run_error("Use the file text nope.pln end text.", filename=str(main))
        assert "could not find a file" in str(error)


class TestTryCatch:
    def test_catches_runtime_error(self):
        src = ("Try, Set x to 5 divided by 0. if something goes wrong, Say text caught end text. end try.")
        assert run_src(src) == "caught\n"

    def test_the_problem(self):
        out = run_src("Try, Set x to 5 divided by 0. if something goes wrong, Say the problem. end try.")
        assert "divide" in out

    def test_the_problem_outside_catch(self):
        error = run_error("Say the problem.")
        assert "only available inside" in str(error)

    def test_no_handler_swallows(self):
        src = "Try, Set x to 5 divided by 0. end try. Say text still here end text."
        assert run_src(src) == "still here\n"

    def test_execution_continues_after_catch(self):
        src = ("Try, Set x to 5 divided by 0. if something goes wrong, Say text caught end text. end try. "
               "Say text after end text.")
        assert run_src(src) == "caught\nafter\n"

    def test_undefined_variable_caught(self):
        src = "Try, Say mystery value. if something goes wrong, Say text caught end text. end try."
        assert run_src(src) == "caught\n"


class TestRuntimeErrors:
    def test_undefined_variable_message(self):
        error = run_error("Set alpha to 1.\nSet beta to 2.\nSay c.")
        message = str(error)
        assert "line 3" in message
        assert "Say c." in message

    def test_plus_on_text_suggests_fix(self):
        error = run_error("Say text a end text plus text b end text.")
        assert "joined with" in str(error)

    def test_compare_mixed_types(self):
        error = run_error("If 1 is greater than text a end text, then Say text x end text. end if.")
        assert "cannot compare" in str(error)

    def test_change_undefined(self):
        error = run_error("Change score by 5.")
        assert "could not find a variable called score" in str(error)
