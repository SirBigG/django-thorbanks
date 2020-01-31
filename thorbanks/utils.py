from base64 import b64decode, b64encode
from functools import reduce

from django.urls import reverse
from django.utils.encoding import force_str

from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from thorbanks import settings


IPIZZA_REQUEST_ORDER = {
    "3012": (
        "VK_SERVICE",
        "VK_VERSION",
        "VK_USER",
        "VK_DATETIME",
        "VK_SND_ID",
        "VK_REC_ID",
        "VK_USER_NAME",
        "VK_USER_ID",
        "VK_COUNTRY",
        "VK_OTHER",
        "VK_TOKEN",
        "VK_RID",
    ),
    "3013": (
        "VK_SERVICE",
        "VK_VERSION",
        "VK_DATETIME",
        "VK_SND_ID",
        "VK_REC_ID",
        "VK_NONCE",
        "VK_USER_NAME",
        "VK_USER_ID",
        "VK_COUNTRY",
        "VK_OTHER",
        "VK_TOKEN",
        "VK_RID",
    ),
    "4011": (
        "VK_SERVICE",
        "VK_VERSION",
        "VK_SND_ID",
        "VK_REPLY",
        "VK_RETURN",
        "VK_DATETIME",
        "VK_RID",
    ),
    "4012": (
        "VK_SERVICE",
        "VK_VERSION",
        "VK_SND_ID",
        "VK_REC_ID",
        "VK_NONCE",
        "VK_RETURN",
        "VK_DATETIME",
        "VK_RID",
    ),
}


def get_ordered_request(request, auth=False, response=False):
    def append_if_exists(target, source, the_value):
        if the_value in source:
            target.append(source[the_value])
        return target

    if not auth:
        if response:
            expected_values = (
                "VK_SERVICE",
                "VK_VERSION",
                "VK_SND_ID",
                "VK_REC_ID",
                "VK_STAMP",
                "VK_T_NO",
                "VK_AMOUNT",
                "VK_CURR",
                "VK_REC_ACC",
                "VK_REC_NAME",
                "VK_SND_ACC",
                "VK_SND_NAME",
                "VK_REF",
                "VK_MSG",
                "VK_T_DATETIME",
            )

        else:
            expected_values = (
                "VK_SERVICE",
                "VK_VERSION",
                "VK_SND_ID",
                "VK_STAMP",
                "VK_AMOUNT",
                "VK_CURR",
                "VK_REF",
                "VK_MSG",
                "VK_RETURN",
                "VK_CANCEL",
                "VK_DATETIME",
            )

    else:
        if response:
            expected_values = IPIZZA_REQUEST_ORDER["3013"]

        else:
            expected_values = IPIZZA_REQUEST_ORDER["4012"]

    ordered_request = []
    for value in expected_values:
        ordered_request = append_if_exists(ordered_request, request, value)
    return ordered_request


def request_digest(request, bank_name, auth=False, response=False):
    """
        return request digest in Banklink signature form (see docs for format)
    """
    request = get_ordered_request(request, auth=auth, response=response)
    digest = ""
    for value in request:
        value_len = len(value)
        digest += force_str(value_len).rjust(3, "0")
        digest += force_str(value)
    return digest.encode("UTF-8")


def get_pkey(bank_name):
    with open(settings.get_private_key(bank_name)) as handle:
        private_key = RSA.importKey(handle.read())
        handle.close()

    return PKCS1_v1_5.new(private_key)


def create_signature(request, bank_name, auth=False):
    """
        sign BankLink request in dict format with private_key
    """
    digest = request_digest(request, bank_name, auth=auth)
    key_binary = get_pkey(bank_name).sign(SHA.new(digest))

    return force_str(b64encode(key_binary))


def verify_signature(request, bank_name, signature, auth=False, response=False):
    """
        verify BankLink reply signature
    """
    signature = force_str(signature)

    with open(settings.get_public_key(bank_name)) as handle:
        public_key = RSA.importKey(handle.read())
        handle.close()

    the_key = PKCS1_v1_5.new(public_key)
    digest = request_digest(request, bank_name, auth=auth, response=response)

    return the_key.verify(SHA.new(digest), b64decode(signature))


def weight_generator():
    """ Used for weight generation by calculate_731_checksum
    """
    while True:
        yield 7
        yield 3
        yield 1


def calculate_731_checksum(number):
    # Check if number is integer, then cast to string
    number = str(int(number))[::-1]
    gen = weight_generator()
    weight_sum = reduce(lambda x, y: x + int(y) * next(gen), number, 0)
    checksum = (10 - weight_sum % 10) % 10
    return int(number[::-1] + str(checksum))


def pingback_url(request=None, base_url=None):
    assert request or base_url

    if request:
        base_url = "%s://%s" % (
            "https" if request.is_secure() else "http",
            request.META["HTTP_HOST"],
        )

    return "%s%s" % (base_url, reverse("thorbanks_response"))
