from django.shortcuts import render
from django.http import HttpResponse

from .models import BitcoinAddress

def index(request):
    most_recent_addresses = BitcoinAddress.objects.order_by('-pk')[:10]

    output = ', '.join([a.address for a in most_recent_addresses])
    return HttpResponse(output)