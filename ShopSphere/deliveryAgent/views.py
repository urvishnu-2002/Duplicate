from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .forms import AgentRegistrationForm
from .models import Agent

# ===== Dummy Agents =====
DUMMY_AGENTS = [
    {'id': 1, 'username': 'agent_john', 'email': 'john@example.com'},
    {'id': 2, 'username': 'agent_sara', 'email': 'sara@example.com'},
    {'id': 3, 'username': 'agent_mike', 'email': 'mike@example.com'},
    {'id': 4, 'username': 'agent_lisa', 'email': 'lisa@example.com'},
    {'id': 5, 'username': 'agent_tom', 'email': 'tom@example.com'},
]

# ===== Dummy Orders =====
DUMMY_ORDERS = [
    {'id': 1, 'order_id': 'ORD-001', 'customer_name': 'John Doe', 'delivery_address': '123 Main Street, New York, NY 10001', 'earning': 10.00, 'status': 'AVAILABLE'},
    {'id': 2, 'order_id': 'ORD-002', 'customer_name': 'Jane Smith', 'delivery_address': '456 Oak Avenue, Brooklyn, NY 11201', 'earning': 12.50, 'status': 'AVAILABLE'},
    {'id': 3, 'order_id': 'ORD-003', 'customer_name': 'Michael Johnson', 'delivery_address': '789 Pine Road, Queens, NY 11375', 'earning': 8.00, 'status': 'AVAILABLE'},
    {'id': 4, 'order_id': 'ORD-004', 'customer_name': 'Alice Brown', 'delivery_address': '321 Elm Street, Bronx, NY 10453', 'earning': 15.00, 'status': 'DELIVERED'},
    {'id': 5, 'order_id': 'ORD-005', 'customer_name': 'Charlie Davis', 'delivery_address': '654 Maple Avenue, Brooklyn, NY 11215', 'earning': 9.50, 'status': 'DELIVERED'},
    {'id': 6, 'order_id': 'ORD-006', 'customer_name': 'Diana Evans', 'delivery_address': '888 Cedar Court, Staten Island, NY 10301', 'earning': 11.00, 'status': 'AVAILABLE'},
]

# ===== Shared input style =====
INPUT_STYLE = (
    'w-full p-5 bg-gray-50 border-2 border-gray-100 rounded-[2rem] '
    'font-bold tracking-wide focus:border-[#5D56D1] outline-none transition-all'
)

# ===== Agent Portal =====
def agent_portal(request):
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('delivery_dashboard')

    login_form = AuthenticationForm()
    signup_form = AgentRegistrationForm()
    active_tab = 'signin'

    style = (
        'w-full p-5 bg-gray-50 border-2 border-gray-100 rounded-[2rem] '
        'font-bold tracking-wide focus:border-[#5D56D1] outline-none transition-all'
    )
    for field in login_form.fields.values():
        field.widget.attrs.update({'class': INPUT_STYLE})

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'signup':
            active_tab = 'signup'
            signup_form = AgentRegistrationForm(request.POST)

            if signup_form.is_valid():
                user = signup_form.save()
                login(request, user)
                messages.success(request, "Account created! Welcome to the fleet 🚚")
                return redirect('delivery_dashboard')
            messages.error(request, "Please fix the errors below.")

        elif action == 'login':
            active_tab = 'signin'
            login_form = AuthenticationForm(request, data=request.POST)

            for field in login_form.fields.values():
                field.widget.attrs.update({'class': INPUT_STYLE})

            if login_form.is_valid():
                login(request, login_form.get_user())
                return redirect('delivery_dashboard')
            messages.error(request, "Invalid username or password.")

    return render(request, 'agent_portal.html', {
        'login_form': login_form,
        'signup_form': signup_form,
        'active_tab': active_tab,
        'dummy_agents': DUMMY_AGENTS,
    })


# ===== Delivery Dashboard =====
@login_required
def delivery_dashboard(request):
    if not isinstance(request.user, Agent):
        return redirect('agentPortal')

    available_orders = [o for o in DUMMY_ORDERS if o['status'] == 'AVAILABLE']
    delivered_orders = [o for o in DUMMY_ORDERS if o['status'] == 'DELIVERED']

    context = {
        'available_orders': available_orders,
        'recent_orders': delivered_orders,
        'total_earnings': sum(o['earning'] for o in delivered_orders),
        'completed_orders_count': len(delivered_orders),
        'available_orders_count': len(available_orders),
    }

    return render(request, 'delivery_dashboard.html', context)


# ===== Accept Order =====
@login_required
@require_POST
def accept_order(request, order_id):
    order = next((o for o in DUMMY_ORDERS if o['id'] == order_id), None)

    if not order:
        messages.error(request, "Order not found.")
        return redirect('delivery_dashboard')

    if order['status'] != 'AVAILABLE':
        messages.warning(request, f"Order {order['order_id']} is already accepted or delivered.")
        return redirect('delivery_dashboard')

    order['status'] = 'ON_ROUTE'
    messages.success(request, f"Order {order['order_id']} accepted! Please deliver it safely ")

    return redirect('delivery_dashboard')
