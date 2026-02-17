from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .forms import AgentRegistrationForm
from .models import Agent, Order

def agent_portal(request):
    # If already logged in, send them to the dashboard
    if request.user.is_authenticated:
        return redirect('delivery_dashboard')

    login_form = AuthenticationForm()
    signup_form = AgentRegistrationForm()
    active_tab = 'signin'

    if request.method == 'POST':
        action = request.POST.get('action')
        active_tab = action 

        if action == 'signup':
            signup_form = AgentRegistrationForm(request.POST)
            if signup_form.is_valid():
                user = signup_form.save()
                login(request, user) 
                messages.success(request, f"Welcome {user.username}! Account created.")
                return redirect('delivery_dashboard')
            
        elif action == 'login':
            login_form = AuthenticationForm(request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                return redirect('delivery_dashboard')
            else:
                messages.error(request, "Invalid username or password.")

    return render(request, 'delivery_agent/delivery_login.html', {
        'login_form': login_form,
        'signup_form': signup_form,
        'active_tab': active_tab,
    })

@login_required
def delivery_dashboard(request):
    # Ensure these queries work with your Agent model
    available_orders = Order.objects.filter(status='AVAILABLE')
    delivered_orders = Order.objects.filter(assigned_to=request.user, status='DELIVERED')
    active_orders = Order.objects.filter(assigned_to=request.user, status='ON_ROUTE')

    total_earnings = sum(order.earning for order in delivered_orders)

    context = {
        'available_orders': available_orders,
        'delivered_orders': delivered_orders,
        'active_orders_count': active_orders.count(),
        'total_earnings': total_earnings,
    }
    return render(request, 'delivery_agent/delivery_dashboard.html', context)

@login_required
@require_POST
def accept_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status == 'AVAILABLE':
        order.status = 'ON_ROUTE'
        order.assigned_to = request.user
        order.save()
        messages.success(request, f"Order {order.id} accepted!") # Changed to .id or .order_id based on your model
    else:
        messages.error(request, "This order is no longer available.")

    return redirect('delivery_dashboard')