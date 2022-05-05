from django import forms

class BitcoinAddressForm(forms.Form):
    address = forms.CharField(label="Add an address", max_length=100)