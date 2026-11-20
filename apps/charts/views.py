from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.shortcuts import render

from apps.pages.models import Product


@login_required
def index(request):
    products = serializers.serialize('json', Product.objects.all())
    context = {
        'segment': 'charts',
        'products': products
    }
    return render(request, 'charts/index.html', context)