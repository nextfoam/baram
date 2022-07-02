# coding=utf-8
"""Simple public key authentication with RSA based on the
implementation
http://code.activestate.com/recipes/578797-public-key-encryption-rsa/"""

from __future__ import division, absolute_import
from base64 import b32encode,b32decode
try:
    from fractions import gcd
except ImportError:
    from math import gcd
from random import randrange
from collections import namedtuple
from math import log
from binascii import hexlify, unhexlify
import binascii
import sys

from PyFoam.ThirdParty.six import print_,PY3,binary_type,u
if PY3:
    range_func = range
else:
    range_func = xrange

from PyFoam.Infrastructure.Hardcoded import authDirectory,assertDirectory
from PyFoam.FoamInformation import getUserName
from PyFoam.Error import warning
from os import path

def myPrivateKeyFile():
    return path.join(authDirectory(),"privateKey")

def myPublicKeyFile():
    return path.join(authDirectory(),"publicKey")

def myAuthenticatedKeysFile():
    return path.join(authDirectory(),"myAuthenticatedKeys")

def ensureKeyPair():
    from os import chmod
    assertDirectory(authDirectory(),dirMode="700")
    if PY3:
        perm=eval("0o700")
    else:
        perm=eval("0700")

    if not path.exists(myPrivateKeyFile()) and not path.exists(myPublicKeyFile()):
        warning("No key pair in",authDirectory()," .... Creating")
        pubkey, privkey = keygen(2 ** 64)
        open(myPublicKeyFile(),"w").write(key_to_str(pubkey))
        open(myPrivateKeyFile(),"w").write(key_to_str(privkey))

    chmod(myPublicKeyFile(),perm)
    chmod(myPrivateKeyFile(),perm)

    if not path.exists(myAuthenticatedKeysFile()):
        f=open(myAuthenticatedKeysFile(),"w")
        f.close()
    chmod(myAuthenticatedKeysFile(),perm)

def myPublicKeyText():
    return open(myPublicKeyFile()).read()

def myPublicKey():
    return str_to_key(open(myPublicKeyFile()).read())

def myPrivateKey():
    return str_to_key(open(myPrivateKeyFile()).read())

def is_prime(n, k=30):
    # http://en.wikipedia.org/wiki/Miller%E2%80%93Rabin_primality_test
    if n <= 3:
        return n == 2 or n == 3
    neg_one = n - 1

    # write n-1 as 2^s*d where d is odd
    s, d = 0, neg_one
    while not d & 1:
        s, d = s + 1, d >> 1
    assert 2 ** s * d == neg_one and d & 1

    for _ in range_func(k):
        a = randrange(2, neg_one)
        x = pow(a, d, n)
        if x in (1, neg_one):
            continue
        for _ in range_func(s - 1):
            x = x ** 2 % n
            if x == 1:
                return False
            if x == neg_one:
                break
        else:
            return False
    return True


def randprime(n=10 ** 8):
    p = 1
    while not is_prime(p):
        p = randrange(n)
    return p


def multinv(modulus, value):
    """
        Multiplicative inverse in a given modulus

        >>> multinv(191, 138)
        18
        >>> multinv(191, 38)
        186
        >>> multinv(120, 23)
        47
    """
    # http://en.wikipedia.org/wiki/Extended_Euclidean_algorithm
    x, lastx = 0, 1
    a, b = modulus, value
    while b:
        a, q, b = b, a // b, a % b
        x, lastx = lastx - q * x, x
    result = (1 - lastx * modulus) // value
    if result < 0:
        result += modulus
    assert 0 <= result < modulus and value * result % modulus == 1
    return result


KeyPair = namedtuple('KeyPair', 'public private')
Key = namedtuple('Key', 'exponent modulus')


def keygen(n, public=None):
    """ Generate public and private keys from primes up to N.

    Optionally, specify the public key exponent (65537 is popular choice).

        >>> pubkey, privkey = keygen(2**64)
        >>> msg = 123456789012345
        >>> coded = pow(msg, *pubkey)
        >>> plain = pow(coded, *privkey)
        >>> assert msg == plain

    """
    # http://en.wikipedia.org/wiki/RSA
    prime1 = randprime(n)
    prime2 = randprime(n)
    composite = prime1 * prime2
    totient = (prime1 - 1) * (prime2 - 1)
    if public is None:
        private = None
        while True:
            private = randrange(totient)
            if gcd(private, totient) == 1:
                break
        public = multinv(totient, private)
    else:
        private = multinv(totient, public)
    assert public * private % totient == gcd(public, totient) == gcd(private, totient) == 1
    assert pow(pow(1234567, public, composite), private, composite) == 1234567
    return KeyPair(Key(public, composite), Key(private, composite))


def encode(msg, pubkey, verbose=False):
    chunksize = int(log(pubkey.modulus, 256))
    outchunk = chunksize + 1
    outfmt = '%%0%dx' % (outchunk * 2,)
    bmsg = msg if isinstance(msg, binary_type) else msg.encode('utf-8')
    result = []
    for start in range_func(0, len(bmsg), chunksize):
        chunk = bmsg[start:start + chunksize]
        chunk += b'\x00' * (chunksize - len(chunk))
        plain = int(hexlify(chunk), 16)
        coded = pow(plain, *pubkey)
        bcoded = unhexlify((outfmt % coded).encode())
        if verbose:
            print_('Encode:', chunksize, chunk, plain, coded, bcoded)
        result.append(bcoded)
    return b''.join(result)


def decode(bcipher, privkey, verbose=False):
    try:
        chunksize = int(log(privkey.modulus, 256))
        outchunk = chunksize + 1
        outfmt = '%%0%dx' % (chunksize * 2,)
        result = []
        for start in range_func(0, len(bcipher), outchunk):
            bcoded = bcipher[start: start + outchunk]
            coded = int(hexlify(bcoded), 16)
            plain = pow(coded, *privkey)
            chunk = unhexlify((outfmt % plain).encode())
            if verbose:
                print_('Decode:', chunksize, chunk, plain, coded, bcoded)
            result.append(chunk)
        return b''.join(result).rstrip(b'\x00').decode('utf-8')
    except (UnicodeDecodeError,binascii.Error,TypeError) as e:
        return u(b'Failed decode for'+bcipher)

def key_to_str(key):
    """
    Convert `Key` to string representation
    >>> key_to_str(Key(50476910741469568741791652650587163073, 95419691922573224706255222482923256353))
    '25f97fd801214cdc163796f8a43289c1:47c92a08bc374e96c7af66eb141d7a21'
    """
    return ':'.join((('%%0%dx' % ((int(log(number, 256)) + 1) * 2)) % number) for number in key)


def str_to_key(key_str):
    """
    Convert string representation to `Key` (assuming valid input)
    >>> (str_to_key('25f97fd801214cdc163796f8a43289c1:47c92a08bc374e96c7af66eb141d7a21') ==
    ...  Key(exponent=50476910741469568741791652650587163073, modulus=95419691922573224706255222482923256353))
    True
    """
    return Key(*(int(number, 16) for number in key_str.split(':')))

def createChallengeString(msg):
    return (b32encode(msg.encode('utf-8'))+b":"+b32encode(encode(msg,myPrivateKey()))).decode()

def checkChallenge(challenge,pubKey):
    org,encoded=challenge.split(":")
    org=b32decode(org).decode('utf-8')
    encoded=decode(b32decode(encoded),pubKey)
    return org==encoded

def authenticatedKeys():
    keys={}
    for l in open(myAuthenticatedKeysFile()).readlines():
        try:
            u,k=l.split()
            keys[u]=k
        except ValueError:
            pass
    return keys

def checkAuthentication(userName,challenge):
    if userName==getUserName():
        pub=myPublicKey()
    else:
        pub=None
        keys=authenticatedKeys()
        if userName in keys:
            pub=str_to_key(keys[userName])
        else:
            return False

    return checkChallenge(challenge,pub)

if __name__ == '__main__':
    ensureKeyPair()
    pub=myPublicKey()
    priv=myPrivateKey()
    msg = u'the quick brown fox jumped over the lazy dog ® ⌀'
    challenge=createChallengeString(msg)
    print_("Challenge:",challenge)
    print_("Checking:",checkChallenge(challenge,myPublicKey()))
    pubkey, privkey = keygen(2 ** 64)
    print_("Checking False:",False==checkChallenge(challenge,pubkey))
    print_("Checking MyUsername:",checkAuthentication(getUserName(),challenge))
    print_("Checking user 'test':",checkAuthentication("test",challenge))
