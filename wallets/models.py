from django.db import models

# Create your models here.
class BitcoinAddress(models.Model):
    address = models.CharField(max_length=100, unique=True)
    balance = models.DecimalField(default=0, decimal_places=3, max_digits=15)

class Transaction(models.Model):
    fromAddress = models.ManyToManyField(BitcoinAddress, related_name='from_address')
    toAddress = models.ManyToManyField(BitcoinAddress, related_name='to_address')
    timestamp = models.DateTimeField()
    amount = models.DecimalField(default=0, decimal_places=3, max_digits=15)