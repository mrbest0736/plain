"""Built-in helpers for the Plain language.

These are the runtime helpers behind: random number from ... to ...,
the current time, wait ... seconds, the text version of, the number
version of, split ... by ..., read file and write file.
"""

import math
import os
import random as _random
import time as _time

from plain.errors import PlainRuntimeError
from plain.security import format_limit, secure_random_int


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def display_value(value):
    """Turn a Plain value into readable text for Say and Write."""
    if value is None:
        return "nothing"
    if value is True:
        return "yes"
    if value is False:
        return "no"
    if isinstance(value, float):
        r = round(value, 10)
        if r.is_integer():
            return str(int(r))
        return str(r)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "[" + ", ".join(display_value(v) for v in value) + "]"
    return str(value)


def to_text(value, line):
    if value is None:
        return "nothing"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if is_number(value):
        return display_value(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "[" + ", ".join(display_value(v) for v in value) + "]"
    raise PlainRuntimeError(
        "I do not know how to turn %s into text on line %s." % (describe_type(value), line),
        "The text version of works on numbers, text, yes and no, nothing and lists.",
        line=line)


def to_number(value, line):
    if is_number(value):
        return value
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, str):
        cleaned = value.strip().lower()
        try:
            return float(cleaned) if "." in cleaned else int(cleaned)
        except ValueError:
            pass
        swapped = cleaned.replace("negative", "-").replace("point", ".").replace(" ", "").strip()
        try:
            return float(swapped) if "." in swapped else int(swapped)
        except ValueError:
            pass
    raise PlainRuntimeError(
        "I could not read %s as a number on line %s." % (display_value(value), line),
        "The number version of works on text like 42 or 3 point 14, and on yes and no.",
        line=line)


def describe_type(value):
    if value is None:
        return "nothing"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if is_number(value):
        return "the number %s" % display_value(value)
    if isinstance(value, str):
        return "the text %s" % display_value(value)
    if isinstance(value, list):
        return "a list of %s %s" % (len(value), "item" if len(value) == 1 else "items")
    return "an unknown value"


def builtin_random(start, stop, line):
    if not is_number(start) or not is_number(stop):
        raise PlainRuntimeError(
            "random number from needs two numbers on line %s, but I got %s and %s." % (
                line, describe_type(start), describe_type(stop)),
            "Write it like: random number from 1 to 10.",
            line=line)
    a = int(round(start))
    b = int(round(stop))
    if a > b:
        raise PlainRuntimeError(
            "I cannot pick a random number from %s to %s on line %s, because the first number is larger." % (a, b, line),
            "Write the smaller number first: random number from 1 to 10.",
            line=line)
    return _random.randint(a, b)


def builtin_current_time():
    return _time.time()


def builtin_wait(seconds, line, max_seconds=None):
    if not is_number(seconds) or seconds < 0:
        raise PlainRuntimeError(
            "wait needs a number of seconds that is zero or more on line %s, but I got %s." % (
                line, display_value(seconds)),
            "Write it like: wait 2 seconds.",
            line=line)
    if max_seconds is not None and seconds > max_seconds:
        raise PlainRuntimeError(
            "I cannot wait %s seconds on line %s, because the longest wait allowed is %s seconds." % (
                display_value(seconds), line, format_limit(max_seconds)),
            "Wait for a shorter time. Long waits are usually a mistake.",
            line=line)
    _time.sleep(seconds)


def builtin_secure_random(start, stop, line):
    if not is_number(start) or not is_number(stop):
        raise PlainRuntimeError(
            "secure random number from needs two numbers on line %s, but I got %s and %s." % (
                line, describe_type(start), describe_type(stop)),
            "Write it like: secure random number from 1 to 10.",
            line=line)
    a = int(round(start))
    b = int(round(stop))
    if a > b:
        raise PlainRuntimeError(
            "I cannot pick a secure random number from %s to %s on line %s, because the first number is larger." % (a, b, line),
            "Write the smaller number first: secure random number from 1 to 10.",
            line=line)
    return secure_random_int(a, b)


def builtin_split(value, separator, line):
    if not isinstance(value, str):
        raise PlainRuntimeError(
            "split needs text to split on line %s, but I got %s." % (line, describe_type(value)),
            "split works on text, for example: split sentence by text , end text",
            line=line)
    if not isinstance(separator, str):
        raise PlainRuntimeError(
            "split needs text to split by on line %s, but I got %s." % (line, describe_type(separator)),
            "The separator is text, for example: split sentence by text , end text",
            line=line)
    if separator == "":
        raise PlainRuntimeError(
            "I cannot split text by an empty text on line %s." % line,
            "Choose a separator that appears in the text, like a space or a comma.",
            line=line)
    return value.split(separator)


def builtin_read_file(path, line, max_bytes=None):
    if not isinstance(path, str):
        raise PlainRuntimeError(
            "read file needs the file name as text on line %s, but I got %s." % (line, describe_type(path)),
            "Write it like: read file text notes.txt end text",
            line=line)
    if max_bytes is not None:
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        if size > max_bytes:
            raise PlainRuntimeError(
                "I cannot read the file %s on line %s, because it is bigger than %s characters." % (
                    path, line, format_limit(max_bytes)),
                "Read smaller files, or raise the limit with --max-read-bytes.",
                line=line)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        raise PlainRuntimeError(
            "I could not find a file called %s on line %s." % (path, line),
            "Check the file name and where the file is saved.",
            line=line)
    except OSError as exc:
        raise PlainRuntimeError(
            "I could not read the file %s on line %s because %s." % (path, line, exc.strerror or exc),
            "Check that the file exists and can be read.",
            line=line)


def builtin_write_file(path, content, line):
    if not isinstance(path, str):
        raise PlainRuntimeError(
            "write file needs the file name as text on line %s, but I got %s." % (line, describe_type(path)),
            "Write it like: write file text notes.txt end text with text hello end text",
            line=line)
    text = to_text(content, line)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as exc:
        raise PlainRuntimeError(
            "I could not write the file %s on line %s because %s." % (path, line, exc.strerror or exc),
            "Check that the folder exists and can be written to.",
            line=line)
    return None


def builtin_sqrt(value, line):
    if not is_number(value):
        raise PlainRuntimeError(
            "the square root of needs a number on line %s, but I got %s." % (line, describe_type(value)),
            "Write it like: the square root of 16",
            line=line)
    if value < 0:
        raise PlainRuntimeError(
            "I cannot take the square root of %s on line %s, because it is negative." % (display_value(value), line),
            "Use the absolute value of first if you want the size of the number.",
            line=line)
    return math.sqrt(value)


def builtin_rounded(value, line):
    if not is_number(value):
        raise PlainRuntimeError(
            "rounded needs a number on line %s, but I got %s." % (line, describe_type(value)),
            "Write it like: 3 point 7 rounded",
            line=line)
    if value >= 0:
        return math.floor(value + 0.5)
    return math.ceil(value - 0.5)
