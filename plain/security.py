"""Security for Plain: AES-256 encryption, secure hashing, safe randomness.

Everything in this module uses only the Python standard library, so Plain
keeps its zero-dependency promise.  It provides three things:

1. Real cryptography for .pln programs: AES-256 in CBC mode with PKCS#7
   padding, keys derived from a passphrase with PBKDF2-HMAC-SHA256
   (100,000 rounds), a fresh random salt and IV for every message, and
   SHA-256 hashing.  The AES core below is written from the specification
   and verified against the official FIPS-197 test vector.
2. Safe randomness: secrets-based random numbers for anything security
   related (codes, tokens, keys).
3. The sandbox policy (Limits): the safety guarantees every Plain program
   runs under - bounds-checked everything, files confined to the program's
   folder, and limits on loop rounds, call depth, output size, waiting and
   file size, so no program can hang the machine, flood the disk or eat
   memory by accident.

The encrypted form of a message looks like this:

    b"PLN1" + salt(16) + iv(16) + AES-256-CBC ciphertext

written out as base64 text, so it can live in a Plain text value, be said
aloud, or be saved with write file and decrypted later.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass


# --- the sandbox policy -------------------------------------------------------

@dataclass
class Limits:
    """Safety limits applied to every run.  None means unlimited."""

    max_loop_rounds: int = 10_000_000
    max_call_depth: int = 200
    max_output_chars: int = 10_000_000
    max_wait_seconds: float = 60
    max_read_bytes: int = 10_000_000

    @classmethod
    def unlimited(cls):
        return cls(None, None, None, None, None)


def format_limit(number):
    if number is None:
        return "unlimited"
    return format(number, ",")


# --- GF(2^8) arithmetic and the AES tables ------------------------------------

def _xtime(a):
    a <<= 1
    if a & 0x100:
        a ^= 0x11B
    return a & 0xFF


def _rotl8(byte, count):
    return ((byte << count) | (byte >> (8 - count))) & 0xFF


def _build_tables():
    exp = [0] * 256
    log = [0] * 256
    value = 1
    for power in range(255):
        exp[power] = value
        log[value] = power
        value ^= _xtime(value)
        value &= 0xFF
    exp[255] = exp[0]

    sbox = [0] * 256
    inv_sbox = [0] * 256
    for i in range(256):
        inverse = 0 if i == 0 else exp[(255 - log[i]) % 255]
        mixed = (inverse ^ _rotl8(inverse, 1) ^ _rotl8(inverse, 2)
                 ^ _rotl8(inverse, 3) ^ _rotl8(inverse, 4) ^ 0x63)
        sbox[i] = mixed
        inv_sbox[mixed] = i
    return sbox, inv_sbox


SBOX, INV_SBOX = _build_tables()


def _expand_key(key):
    """AES-256 key schedule: 8 key words in, 60 round-key words out."""
    words = [list(key[i * 4:i * 4 + 4]) for i in range(8)]
    rcon = 1
    for i in range(8, 60):
        temp = list(words[i - 1])
        if i % 8 == 0:
            temp = [SBOX[temp[1]], SBOX[temp[2]], SBOX[temp[3]], SBOX[temp[0]]]
            temp[0] ^= rcon
            rcon = _xtime(rcon)
        elif i % 8 == 4:
            temp = [SBOX[b] for b in temp]
        previous = words[i - 8]
        words.append([previous[j] ^ temp[j] for j in range(4)])
    return words


def _add_round_key(state, words, round_index):
    for column in range(4):
        word = words[round_index * 4 + column]
        base = column * 4
        state[base] ^= word[0]
        state[base + 1] ^= word[1]
        state[base + 2] ^= word[2]
        state[base + 3] ^= word[3]


def _mix_column(state, base):
    a, b, c, d = state[base], state[base + 1], state[base + 2], state[base + 3]
    ta, tb, tc, td = _xtime(a), _xtime(b), _xtime(c), _xtime(d)
    state[base] = ta ^ (tb ^ b) ^ c ^ d
    state[base + 1] = a ^ tb ^ (tc ^ c) ^ d
    state[base + 2] = a ^ b ^ tc ^ (td ^ d)
    state[base + 3] = (ta ^ a) ^ b ^ c ^ td


def _inv_mix_column(state, base):
    a, b, c, d = state[base], state[base + 1], state[base + 2], state[base + 3]
    ta, tb, tc, td = _xtime(a), _xtime(b), _xtime(c), _xtime(d)
    tta, ttb, ttc, ttd = _xtime(ta), _xtime(tb), _xtime(tc), _xtime(td)
    ttta, tttb, tttc, tttd = _xtime(tta), _xtime(ttb), _xtime(ttc), _xtime(ttd)
    state[base] = (ttta ^ tta ^ ta) ^ (tttb ^ tb ^ b) ^ (tttc ^ ttc ^ c) ^ (tttd ^ d)
    state[base + 1] = (ttta ^ a) ^ (tttb ^ ttb ^ tb) ^ (tttc ^ tc ^ c) ^ (tttd ^ ttd ^ d)
    state[base + 2] = (ttta ^ tta ^ a) ^ (tttb ^ b) ^ (tttc ^ ttc ^ tc) ^ (tttd ^ td ^ d)
    state[base + 3] = (ttta ^ ta ^ a) ^ (tttb ^ ttb ^ b) ^ (tttc ^ c) ^ (tttd ^ ttd ^ td)


def encrypt_block(block, words):
    state = list(block)
    _add_round_key(state, words, 0)
    for round_index in range(1, 14):
        state = [SBOX[b] for b in state]
        shifted = list(state)
        for row in range(1, 4):
            for column in range(4):
                shifted[column * 4 + row] = state[((column + row) % 4) * 4 + row]
        for column in range(4):
            _mix_column(shifted, column * 4)
        _add_round_key(shifted, words, round_index)
        state = shifted
    state = [SBOX[b] for b in state]
    shifted = list(state)
    for row in range(1, 4):
        for column in range(4):
            shifted[column * 4 + row] = state[((column + row) % 4) * 4 + row]
    _add_round_key(shifted, words, 14)
    return shifted


def decrypt_block(block, words):
    state = list(block)
    _add_round_key(state, words, 14)
    for round_index in range(13, 0, -1):
        shifted = list(state)
        for row in range(1, 4):
            for column in range(4):
                shifted[((column + row) % 4) * 4 + row] = state[column * 4 + row]
        state = [INV_SBOX[b] for b in shifted]
        _add_round_key(state, words, round_index)
        for column in range(4):
            _inv_mix_column(state, column * 4)
    shifted = list(state)
    for row in range(1, 4):
        for column in range(4):
            shifted[((column + row) % 4) * 4 + row] = state[column * 4 + row]
    state = [INV_SBOX[b] for b in shifted]
    _add_round_key(state, words, 0)
    return state


def _xor_bytes(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def _cbc_encrypt(padded, key, iv):
    words = _expand_key(key)
    result = []
    previous = iv
    for start in range(0, len(padded), 16):
        block = _xor_bytes(padded[start:start + 16], previous)
        previous = bytes(encrypt_block(block, words))
        result.append(previous)
    return b"".join(result)


def _cbc_decrypt(ciphertext, key, iv):
    words = _expand_key(key)
    result = []
    previous = iv
    for start in range(0, len(ciphertext), 16):
        block = ciphertext[start:start + 16]
        result.append(_xor_bytes(bytes(decrypt_block(block, words)), previous))
        previous = block
    return b"".join(result)


# --- the face Plain programs see ------------------------------------------------

MAGIC = b"PLN1"
SALT_BYTES = 16
IV_BYTES = 16
BLOCK_BYTES = 16
KDF_ROUNDS = 100_000


def _pad(data):
    fill = BLOCK_BYTES - (len(data) % BLOCK_BYTES)
    return data + bytes([fill]) * fill


def _unpad(data):
    fill = data[-1]
    if fill < 1 or fill > BLOCK_BYTES or data[-fill:] != bytes([fill]) * fill:
        raise ValueError("bad padding")
    return data[:-fill]


def encrypt_text(plaintext, passphrase):
    """Encrypt text with a passphrase.  Returns base64 text."""
    salt = secrets.token_bytes(SALT_BYTES)
    iv = secrets.token_bytes(IV_BYTES)
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"),
                              salt, KDF_ROUNDS, dklen=32)
    ciphertext = _cbc_encrypt(_pad(plaintext.encode("utf-8")), key, iv)
    blob = MAGIC + salt + iv + ciphertext
    return base64.b64encode(blob).decode("ascii")


def decrypt_text(encrypted, passphrase):
    """Decrypt text made by encrypt_text.  Raises ValueError when the key is
    wrong or the text is not a Plain-encrypted message."""
    try:
        blob = base64.b64decode(encrypted.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("not a Plain-encrypted message")
    header = len(MAGIC) + SALT_BYTES + IV_BYTES
    if len(blob) < header + BLOCK_BYTES or blob[:len(MAGIC)] != MAGIC:
        raise ValueError("not a Plain-encrypted message")
    if (len(blob) - header) % BLOCK_BYTES != 0:
        raise ValueError("not a Plain-encrypted message")
    salt = blob[len(MAGIC):len(MAGIC) + SALT_BYTES]
    iv = blob[len(MAGIC) + SALT_BYTES:header]
    ciphertext = blob[header:]
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"),
                              salt, KDF_ROUNDS, dklen=32)
    try:
        padded = _cbc_decrypt(ciphertext, key, iv)
        return _unpad(padded).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        raise ValueError("wrong key or corrupted message")


def secure_hash_text(text):
    """The SHA-256 hash of text, as 64 hex characters."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def secure_random_int(start, stop):
    """A cryptographically safe random whole number from start to stop."""
    return start + secrets.randbelow(stop - start + 1)
