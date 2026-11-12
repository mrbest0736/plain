"""Tests for the security layer: AES-256 crypto, hashing, secure random,
safety limits and path confinement, in both engines.
"""

import io

import pytest

from plain.errors import PlainError, PlainRuntimeError
from plain.interpreter import Interpreter
from plain.lexer import lex
from plain.parser import Parser
from plain.security import (
    Limits, decrypt_text, encrypt_text, format_limit,
    secure_hash_text, secure_random_int,
)
from plain.vm import Runtime


def run_with(engine_class, src, inputs=None, filename=None, limits=None):
    out = io.StringIO()
    pending = list(inputs or [])

    def input_fn():
        if not pending:
            raise EOFError
        return pending.pop(0)

    engine = engine_class(source=src, filename=filename, output=out.write,
                          input_fn=input_fn, limits=limits)
    program = Parser(lex(src), src).parse_program()
    engine.run(program)
    return out.getvalue()


def run_both(src, inputs=None, filename=None, limits=None):
    tree_out = run_with(Interpreter, src, inputs, filename, limits)
    vm_out = run_with(Runtime, src, inputs, filename, limits)
    assert vm_out == tree_out
    return tree_out


def run_error(engine_class, src, inputs=None, filename=None, limits=None):
    with pytest.raises(PlainError) as exc_info:
        run_with(engine_class, src, inputs, filename, limits)
    return exc_info.value


# --- crypto primitives ------------------------------------------------------

def test_aes256_fips197_vector():
    from plain.security import _expand_key, decrypt_block, encrypt_block
    words = _expand_key(bytes(range(32)))
    block = bytes.fromhex("00112233445566778899aabbccddeeff")
    expected = "8ea2b7ca516745bfeafc49904b496089"
    cipher = bytes(encrypt_block(block, words))
    assert cipher.hex() == expected
    assert bytes(decrypt_block(cipher, words)) == block


def test_encrypt_decrypt_roundtrip_lengths():
    for size in (0, 1, 15, 16, 17, 39):
        message = "x" * size
        blob = encrypt_text(message, "key one")
        assert decrypt_text(blob, "key one") == message


def test_blob_shape():
    import base64
    blob = encrypt_text("hello", "key")
    raw = base64.b64decode(blob)
    assert raw[:4] == b"PLN1"
    assert len(raw) == 4 + 16 + 16 + 16


def test_same_input_different_blob():
    assert encrypt_text("hello", "key") != encrypt_text("hello", "key")


def test_wrong_key_rejected():
    blob = encrypt_text("secret words", "right key")
    with pytest.raises(ValueError):
        decrypt_text(blob, "wrong key")


def test_garbage_rejected():
    with pytest.raises(ValueError):
        decrypt_text("this is not a plain message", "key")


def test_sha256_vector():
    assert (secure_hash_text("hello") ==
            "2cf24dba5fb0a30e26e83b2ac5b9e29e"
            "1b161e5c1fa7425e73043362938b9824")


def test_secure_random_bounds():
    for _ in range(200):
        value = secure_random_int(5, 7)
        assert 5 <= value <= 7


# --- the language level -----------------------------------------------------

def test_encrypt_decrypt_program_both_engines():
    out = run_both(
        "Set message to text hello plain end text.\n"
        "Set locked to encrypt message with key text k end text.\n"
        "Set opened to decrypt locked with key text k end text.\n"
        "Say opened.\n")
    assert out == "hello plain\n"


def test_secure_hash_program_both_engines():
    out = run_both(
        "Set stamp to the secure hash of text hello end text.\n"
        "Say the length of stamp.\n")
    assert out == "64\n"


def test_secure_hash_needs_text():
    for engine in (Interpreter, Runtime):
        with pytest.raises(PlainError) as exc_info:
            run_with(engine, "Say the secure hash of 42.\n")
        assert "the secure hash of works on text" in str(exc_info.value)


def test_secure_random_program_both_engines():
    for engine in (Interpreter, Runtime):
        out = run_with(engine, "Set dice to secure random number from 1 to 6.\n"
                               "If dice is at least 1, then Say text ok end text. end if.\n")
        assert out == "ok\n"


def test_encrypt_needs_text_args():
    for engine in (Interpreter, Runtime):
        with pytest.raises(PlainError) as exc_info:
            run_with(engine, "Set x to encrypt 42 with key text k end text.\n")
        assert "encrypt works on text and a key" in str(exc_info.value)


def test_decrypt_wrong_key_friendly_error():
    src = ("Set locked to encrypt text hi end text with key text good end text.\n"
           "Set junk to decrypt locked with key text bad end text.\n")
    for engine in (Interpreter, Runtime):
        with pytest.raises(PlainError) as exc_info:
            run_with(engine, src)
        message = str(exc_info.value)
        assert "I cannot decrypt this message on line 2." in message
        assert "Decrypt it with the same key it was encrypted with." in message


def test_decrypt_garbage_friendly_error():
    for engine in (Interpreter, Runtime):
        with pytest.raises(PlainError) as exc_info:
            run_with(engine, "Set junk to decrypt text nonsense end text with key text k end text.\n")
        assert "I cannot decrypt this message on line 1." in str(exc_info.value)


def test_encrypt_decrypt_inside_try():
    src = ("Set locked to encrypt text hi end text with key text good end text.\n"
           "Try,\n"
           "  Set junk to decrypt locked with key text bad end text.\n"
           "if something goes wrong,\n"
           "  Say text caught end text.\n"
           "end try.\n")
    assert run_both(src) == "caught\n"


# --- safety limits ----------------------------------------------------------

LOOP_CAP = "Set n to 0. While yes, Change n by 1. end loop."
DEPTH_SRC = ("To go deeper with n, do\n"
             "  Set again to the result of go deeper with n plus 1.\n"
             "end function.\n"
             "Set out to the result of go deeper with 1.\n")
OUTPUT_SRC = "Repeat 100 times, Say text spam spam spam spam end text. end loop."
WAIT_SRC = "Wait 500 seconds."


@pytest.mark.parametrize("engine_class", [Interpreter, Runtime])
class TestLimits:
    def test_loop_cap(self, engine_class):
        with pytest.raises(PlainRuntimeError) as exc_info:
            run_with(engine_class, LOOP_CAP, limits=Limits(max_loop_rounds=10))
        message = str(exc_info.value)
        assert "more than 10 loop rounds in total" in message
        assert "--max-loop-rounds" in message

    def test_depth_cap(self, engine_class):
        with pytest.raises(PlainRuntimeError) as exc_info:
            run_with(engine_class, DEPTH_SRC, limits=Limits(max_call_depth=10))
        message = str(exc_info.value)
        assert "nested more than 10 deep" in message
        assert "--max-call-depth" in message

    def test_output_cap(self, engine_class):
        with pytest.raises(PlainRuntimeError) as exc_info:
            run_with(engine_class, OUTPUT_SRC, limits=Limits(max_output_chars=50))
        message = str(exc_info.value)
        assert "said more than 50 characters" in message
        assert "--max-output-chars" in message

    def test_wait_cap(self, engine_class):
        with pytest.raises(PlainRuntimeError) as exc_info:
            run_with(engine_class, WAIT_SRC, limits=Limits(max_wait_seconds=60))
        message = str(exc_info.value)
        assert "longest wait allowed is 60 seconds" in message

    def test_default_limits_allow_normal_programs(self, engine_class):
        out = run_with(engine_class, "Repeat 100 times, Say text ok end text. end loop.")
        assert out.count("ok") == 100

    def test_default_limits_allow_long_loops(self, engine_class):
        src = "Set n to 0. While n is less than 20000, Change n by 1. end loop. Say n.\n"
        assert run_with(engine_class, src) == "20000\n"


def test_wait_cap_message_vm_matches_interpreter():
    with pytest.raises(PlainRuntimeError) as tree_error:
        run_with(Interpreter, WAIT_SRC, limits=Limits(max_wait_seconds=60))
    with pytest.raises(PlainRuntimeError) as vm_error:
        run_with(Runtime, WAIT_SRC, limits=Limits(max_wait_seconds=60))
    assert str(tree_error.value) == str(vm_error.value)


def test_loop_cap_message_vm_matches_interpreter():
    with pytest.raises(PlainRuntimeError) as tree_error:
        run_with(Interpreter, LOOP_CAP, limits=Limits(max_loop_rounds=10))
    with pytest.raises(PlainRuntimeError) as vm_error:
        run_with(Runtime, LOOP_CAP, limits=Limits(max_loop_rounds=10))
    assert str(tree_error.value) == str(vm_error.value)


# --- path confinement -------------------------------------------------------

@pytest.mark.parametrize("engine_class", [Interpreter, Runtime])
class TestPathConfinement:
    def test_read_inside_program_folder_works(self, engine_class, tmp_path):
        (tmp_path / "notes.txt").write_text("found it")
        program = tmp_path / "main.pln"
        program.write_text("Say read file text notes.txt end text.\n")
        out = run_with(engine_class, program.read_text(), filename=str(program))
        assert out == "found it\n"

    def test_parent_escape_rejected(self, engine_class, tmp_path):
        (tmp_path.parent / "secret.txt").write_text("top secret")
        program = tmp_path / "main.pln"
        program.write_text("Say read file text ../secret.txt end text.\n")
        with pytest.raises(PlainRuntimeError) as exc_info:
            run_with(engine_class, program.read_text(), filename=str(program))
        message = str(exc_info.value)
        assert "points outside it" in message
        assert "Move the file next to the program" in message

    def test_absolute_path_outside_rejected(self, engine_class, tmp_path):
        program = tmp_path / "main.pln"
        program.write_text("Say read file text /etc/hostname end text.\n")
        with pytest.raises(PlainRuntimeError) as exc_info:
            run_with(engine_class, program.read_text(), filename=str(program))
        assert "points outside it" in str(exc_info.value)

    def test_use_file_escape_rejected(self, engine_class, tmp_path):
        program = tmp_path / "main.pln"
        program.write_text("Use the file text ../other.pln end text.\n")
        with pytest.raises(PlainRuntimeError) as exc_info:
            run_with(engine_class, program.read_text(), filename=str(program))
        assert "points outside it" in str(exc_info.value)

    def test_non_text_path_rejected(self, engine_class):
        with pytest.raises(PlainRuntimeError) as exc_info:
            run_with(engine_class, "Say read file 42.\n")
        message = str(exc_info.value)
        assert "need the file name as text on line 1" in message
        assert "I got the number 42" in message


# --- limits plumbing --------------------------------------------------------

def test_format_limit():
    assert format_limit(1000000) == "1,000,000"
    assert format_limit(None) == "unlimited"


def test_limits_unlimited():
    limits = Limits.unlimited()
    for name in ("max_loop_rounds", "max_call_depth", "max_output_chars",
                 "max_wait_seconds", "max_read_bytes"):
        assert getattr(limits, name) is None
