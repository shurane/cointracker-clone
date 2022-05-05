from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import BitcoinAddress
from .forms import BitcoinAddressForm

import logging
logger = logging.getLogger('django')

from typing import Union, Dict, Any, Iterable
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
    expire_after=timedelta(minutes=15),
    allowable_codes=[200, 400],
    allowable_methods=["GET", "POST"],
)

def to_int(s: Union[str, None], min_val: Union[int, None] = None, max_val: Union[int, None] = None, default: int = 0) -> int:
    if s is None: return default
    try:
        value = int(s)
        if min_val is not None and value < min_val:
            return min_val
        elif max_val is not None and value > max_val:
            return max_val
        else:
            return value
    except ValueError:
        return default

# would be nice to have a more rich AddressResponse object to then iterate over different fields
def get_address_data(address: str) -> Dict[str, Any]:
    address_request = session.get(BLOCKCHAIR_ADDRESS.format(address))
    return address_request.json()["data"]

def validate_address(address: str) -> bool:
    type = get_address_data(address)[address]["address"]["type"]
    return type is not None

def index(request: HttpRequest) -> HttpResponse:
    most_recent_addresses = BitcoinAddress.objects.order_by('-pk')
    form = BitcoinAddressForm()
    context = {
        "most_recent_addresses" : most_recent_addresses,
        "form": form,
    }
    return render(request, "wallets/index.html", context)

def detail(request: HttpRequest, address_id: int) -> HttpResponse:
    address = get_object_or_404(BitcoinAddress, pk=address_id)

    address_data = get_address_data(address.address)
    balance = address_data[address.address]["address"]["balance_usd"]

    # update the current value of balance back to the model
    address.balance = balance
    address.save()

    # get list of most recent transactions to display
    transactions_ids = address_data[address.address]["transactions"]

    # page is offset by 1
    page_value = request.GET.get("page")
    page_total = math.ceil(len(transactions_ids) // PAGE_SIZE)
    page = to_int(page_value, min_val=1, max_val=page_total, default=1)
    offset = (page-1) * PAGE_SIZE

    transactions_page = transactions_ids[offset:(offset+PAGE_SIZE)]

    transactions_param = ",".join(transactions_page)
    transactions_info = BLOCKCHAIR_TRANSACTIONS.format(transactions_param)
    transactions_data = session.get(transactions_info).json()["data"]

    # grab transactions and sort recipients from highest to lowest and track the top one
    transactions = dict()
    for t in transactions_page:
        recipients = sorted(transactions_data[t]["outputs"], key=lambda x: x["value_usd"], reverse=True)
        biggest_recipient = recipients[0]["recipient"]
        biggest_recipient_amount = recipients[0]["value_usd"]
        biggest_recipient_not_tracked = not BitcoinAddress.objects.filter(address=biggest_recipient).exists()

        transactions[t] = {
            "timestamp": transactions_data[t]["transaction"]["time"],
            "amount": transactions_data[t]["transaction"]["output_total_usd"],
            "fee": transactions_data[t]["transaction"]["fee_usd"],
            "biggest_recipient": biggest_recipient,
            "biggest_recipient_amount": biggest_recipient_amount,
            "biggest_recipient_not_tracked": biggest_recipient_not_tracked,
            "form": None,
        }

    context = {
        "address": address,
        "balance": balance,
        "transactions": transactions,
        "transactions_total": len(transactions_ids),
        "page": page,
        "page_total": page_total,
    }

    return render(request, "wallets/detail.html", context)

def add(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = BitcoinAddressForm(request.POST)
        address_value = request.POST.get("address","invalid")
        balance_value = to_int(request.POST.get("balance", ""), default=0)

        # would be nice to use as a validator on the form
        if form.is_valid() and validate_address(address_value):
            try:
                BitcoinAddress.objects.create(address=address_value, balance=balance_value)
            except IntegrityError as error:
                messages.error(request, f"was not able to store address '{address_value}' in database: {error}")
        else:
            messages.error(request, f"form is not valid for bitcoin address '{address_value}', got result: {validate_address(address_value)}")
    else:
        messages.warning(request, "invalid API call to /wallets/add/")

    return redirect("index")
