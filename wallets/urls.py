from django.urls import path

from . import views

urlpatterns = [
    # ex: /wallets/
    path("", views.index, name="index"),
    # ex: /wallets/2/
    path("<int:address_id>/", views.detail, name="detail"),
    # ex: /polls/add/
    path("add/", views.add, name="add"),
]