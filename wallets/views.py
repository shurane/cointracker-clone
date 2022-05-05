from multiprocessing.sharedctypes import Value
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import BitcoinAddress
from .forms import BitcoinAddressForm

import logging
logger = logging.getLogger('django')

from typing import Union
import math
from datetime import timedelta
from requests_cache import CachedSession

PAGE_SIZE = 10
BLOCKCHAIR_ADDRESS = "https://api.blockchair.com/bitcoin/dashboards/address/{}"
BLOCKCHAIR_TRANSACTIONS = "https://api.blockchair.com/bitcoin/dashboards/transactions/{}"

# is there a better place to keep the requests session?
session = CachedSession(
    "cache.sqlite3",
    use_cache_dir=True,
    cache_control=True,
    expire_after=timedelta(hours=3),
    allowable_codes=[200, 400],
    allowable_methods=["GET", "POST"],
)

def to_int(s: Union[str, None], minval: int, maxval: int, default: int = 0) -> int:
    if s is None: return default
    try:
        value = int(s)
        if value < minval:
            return minval
        elif value > maxval:
            return maxval
        else:
            return value
    except ValueError:
        return default

def validate_address(address: str) -> bool:
    address_request = session.get(BLOCKCHAIR_ADDRESS.format(address))

    type = address_request.json()["data"][address]["address"]["type"]
    return type is not None

def index(request: HttpRequest) -> HttpResponse:
    most_recent_addresses = BitcoinAddress.objects.order_by('-pk')[:10]
    form = BitcoinAddressForm()
    context = {
        "most_recent_addresses" : most_recent_addresses,
        "form": form,
    }
    return render(request, "wallets/index.html", context)

def detail(request: HttpRequest, address_id: int) -> HttpResponse:
    address = get_object_or_404(BitcoinAddress, pk=address_id)

    address_info = BLOCKCHAIR_ADDRESS.format(address.address)
    address_request = session.get(address_info)

    # blockchair doesn't expose transactions right away
    data = address_request.json()["data"]
    first_key = list(data.keys())[0]

    transactions = data[first_key]["transactions"]
    # page is offset by 1
    page_value = request.GET.get("page")
    page_total = math.ceil(len(transactions) // PAGE_SIZE)
    page = to_int(page_value, minval=1, maxval=page_total, default=1)
    offset = (page-1) * PAGE_SIZE

    transactions_page = transactions[offset:(offset+PAGE_SIZE)]

    transactions_param = ",".join(transactions_page)
    transactions_info = BLOCKCHAIR_TRANSACTIONS.format(transactions_param)
    transactions_request = session.get(transactions_info)

    # logger.info(f"URL: {transactions_info}")
    # logger.info(transactions_request)

    context = {
        "address": address,
        "transactions": transactions_page,
        "transactions_total": len(transactions),
        "page": page,
        "page_total": page_total,
        "page_size": PAGE_SIZE,
    }

    return render(request, "wallets/detail.html", context)

def add(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = BitcoinAddressForm(request.POST)
        address_value = request.POST.get("address","invalid")

        # would be nice to use as a validator on the form
        if form.is_valid() and validate_address(address_value):
            try:
                BitcoinAddress.objects.create(address=address_value)
            except IntegrityError as error:
                messages.error(request, f"was not able to store address '{address_value}' in database: {error}")
        else:
            messages.error(request, f"form is not valid for bitcoin address '{address_value}', got result: {validate_address(address_value)}")
    else:
        messages.warning(request, "invalid API call to /wallets/add/")

    return redirect("index")
