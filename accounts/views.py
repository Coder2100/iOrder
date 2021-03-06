
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db import models
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import (
    authenticate,
    login,
    logout,
)

from .forms import MyUserLoginForm, MyUserRegistrationForm
from . models import Profile
from menus.models import Topping
import stripe
from datetime import datetime

# Create your views here.

def login_view(request):
    next = request.GET.get('next')
    form = MyUserLoginForm(request.POST or None)
    if form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        login(request, user)
        if next:
            return redirect(next)
        return redirect('orders:index')
    return render(request, 'accounts/login.html', {'form': form})

def register(request):
    if not request.user.is_authenticated:
        next = request.GET.get('next')
        form = MyUserRegistrationForm(request.POST or None)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            email = form.cleaned_data.get('email1')
            user.set_password(password)
            user.email = email
            user.save()
            new_user = authenticate(username=user.username, password=password)
            login(request, new_user)
            if next:
                return redirect(next)
            return redirect('orders:index')
        return render(request, 'accounts/register.html', {'form': form})
    else:
        return redirect('orders:index')


@login_required(login_url='accounts:login')
def logout_view(request):
    logout(request)
    return redirect('orders:index')

def my_profile(request):
    my_user_profile = Profile.objects.filter(user=request.user).first()
    my_orders = Order.objects.filter(is_ordered=True, owner=my_user_profile)
    context = {
      'my_orders': my_orders
      }
    return render(request, "accounts/index.html", context)


class Orders(models.Model):
    title = models.CharField(max_length=40)
    size = models.CharField(max_length=15, null=True, blank=True)
    pizza_toppings = models.ManyToManyField(Topping, related_name="orders", blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    username = models.CharField(max_length=30)
    time = models.DateTimeField(auto_now=True)
    order_status = models.CharField(max_length=10, default='Draft')

    def to_tuple(self, query, object):
        list = query
        output = []
        if object == 'topping':
            for elem in list:
                output.append(elem.topping)
        return tuple(output)

    def __str__(self):
        return f"{self.id} | {self.title} Size: {self.size} Toppings: {self.to_tuple(self.pizza_toppings.all(), 'topping')}"

class Confirmations(models.Model):
    title = models.CharField(max_length=40)
    size = models.CharField(max_length=15, null=True, blank=True)
    pizza_toppings = models.ManyToManyField(Topping, related_name="confirmations", blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    username = models.CharField(max_length=30)
    time = models.DateTimeField(auto_now=True)
    order_status = models.CharField(max_length=10, default='Draft')

    def to_tuple(self, query, object):
        list = query
        output = []
        if object == 'topping':
            for elem in list:
                output.append(elem.topping)
        return tuple(output)

    def __str__(self):
        return f"{self.id} | {self.title} Size: {self.size} Toppings: {self.to_tuple(self.pizza_toppings.all(), 'topping')}"

def added(request):

    title = request.POST["title"]
    size = request.POST["size"]
    price = request.POST["price"]

    try:
        topping1 = request.POST["toppings0"]
    except KeyError:
        topping1 = None
    try:
        topping2 = request.POST["toppings1"]
    except KeyError:
        topping2 = None
    try:
        topping3 = request.POST["toppings2"]
    except KeyError:
        topping3 = None

    if topping1: topping_to_add1 = Toppings.objects.get(id=topping1)
    if topping2: topping_to_add2 = Toppings.objects.get(id=topping2)
    if topping3: topping_to_add3 = Toppings.objects.get(id=topping3)
    order = Orders(title=title, size=size, price=price, username=request.user.username, order_status="draft")

    order.save()

    if topping1: order.pizza_toppings.add(topping_to_add1)
    if topping2: order.pizza_toppings.add(topping_to_add2)
    if topping3: order.pizza_toppings.add(topping_to_add3)


    order.save()

    request.session["blue_cart"] = True

    return JsonResponse({"success": True})
    
@login_required(login_url='accounts:login')
def cart(request):

    orders = Orders.objects.filter(username=request.user.username)

    return render(request, "menus/menu.html", {"orders": orders})

def checkout(request):
    amount = request.POST['amount']
    stripe.api_key = ""

    if request.method == 'POST':
        token = request.POST['stripeToken']
        amount = request.POST['amount']

        username = request.POST['username']
        date = datetime.now()
    try:
        charge = stripe.Charge.create(
            amount      = amount,
            currency    = "usd",
            source      = token,
            description = f"Customer: {username}, on {date.day}/{date.month}/{date.year} at {date.hour}:{date.minute}"
        )

    except stripe.error.CardError as ce:
        return False, ce

    else:
        orders = Orders.objects.filter(username=request.user.username)

        for order in orders:
            confirmation = Confirmations(title=order.title, size=order.size, price=order.price,
            username=order.username, order_status='Confirmed')
            confirmation.save()
            confirmation.pizza_toppings.set(order.pizza_toppings.all())
            confirmation.save()
            order.delete()

        confirmations = Confirmations.objects.filter(username=request.user.username, order_status='Confirmed')
        return render(request, "accounts/confirmation.html" , {"confirmations": confirmations} )
