from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from user.models import Order, OrderItem, Dispute, OrderTracking
from vendor.models import VendorProfile, Product
from deliveryAgent.models import DeliveryAgentProfile, DeliveryAssignment
from .models import (
    VendorApprovalLog, ProductApprovalLog, DeliveryAgentApprovalLog,
    CommissionStructure, SystemConfiguration, DisputeResolution, ActivityLog
)
from .serializers import (
    AdminVendorListSerializer, AdminVendorDetailSerializer,
    AdminProductListSerializer, AdminProductDetailSerializer,
    BlockProductSerializer, UnblockProductSerializer,
    VendorApprovalLogSerializer, ProductApprovalLogSerializer
)

User = get_user_model()

class AdminAuthViewSet(viewsets.ViewSet):
    """
    Check admin status and permissions
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def verify(self, request):
        if not request.user.is_staff and not request.user.role in ['admin', 'customer']:
            return Response({'error': 'Not authorized as admin'}, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            'status': 'authorized',
            'user': {
                'username': request.user.username,
                'email': request.user.email,
                'role': request.user.role,
                'is_staff': request.user.is_staff
            }
        })

class AdminDashboardViewSet(viewsets.ViewSet):
    """
    API Endpoint for SuperAdmin Dashboard Statistics
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        # 1. User Statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        new_users_today = User.objects.filter(date_joined__date=timezone.now().date()).count()

        # 2. Vendor Statistics
        total_vendors = VendorProfile.objects.count()
        pending_vendors = VendorProfile.objects.filter(approval_status='pending').count()
        approved_vendors = VendorProfile.objects.filter(approval_status='approved').count()

        # 3. Order & Revenue Statistics
        total_orders = Order.objects.count()
        total_revenue = Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        
        # 4. Product Statistics
        total_products = Product.objects.count()
        active_products = Product.objects.filter(status='active').count()

        # 5. Delivery Agent Statistics
        total_agents = DeliveryAgentProfile.objects.count()
        pending_agents = DeliveryAgentProfile.objects.filter(approval_status='pending').count()
        approved_agents = DeliveryAgentProfile.objects.filter(approval_status='approved').count()

        # 6. Order Status Breakdown
        order_stats = Order.objects.values('status').annotate(count=Count('id'))
        status_counts = {s: 0 for s in ['pending', 'confirmed', 'shipping', 'delivered', 'cancelled']}
        for stat in order_stats:
            if stat['status'] in status_counts:
                status_counts[stat['status']] = stat['count']

        # 7. Recent Orders (especially those needing attention)
        recent_orders_queryset = Order.objects.all().select_related('user').order_by('-created_at')[:5]
        recent_orders = []
        for o in recent_orders_queryset:
            recent_orders.append({
                'id': o.id,
                'order_number': o.order_number,
                'customer': o.user.username,
                'status': o.status,
                'total': str(o.total_amount),
                'date': o.created_at
            })

        return Response({
            "users": {
                "total": total_users,
                "active": active_users,
                "new_today": new_users_today
            },
            "vendors": {
                "total": total_vendors,
                "pending": pending_vendors,
                "approved": approved_vendors
            },
            "orders": {
                "total": total_orders,
                "revenue": str(total_revenue),
                "status_counts": status_counts
            },
            "recent_orders": recent_orders,
            "products": {
                "total": total_products,
                "active": active_products
            },
            "delivery": {
                "total": total_agents,
                "pending": pending_agents,
                "approved": approved_agents
            }
        })

class AdminUserViewSet(viewsets.ViewSet):
    """
    Manage Users (Block/Unblock)
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        users = User.objects.all().values('id', 'username', 'email', 'role', 'is_active', 'date_joined')
        return Response(users)

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        user = generics.get_object_or_404(User, pk=pk)
        user.is_active = False
        user.save()
        ActivityLog.objects.create(
            user=request.user,
            activity_type='admin_action',
            description=f"Blocked user: {user.username}"
        )
        return Response({'message': f'User {user.username} blocked successfully'})

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        user = generics.get_object_or_404(User, pk=pk)
        user.is_active = True
        user.save()
        ActivityLog.objects.create(
            user=request.user,
            activity_type='admin_action',
            description=f"Unblocked user: {user.username}"
        )
        return Response({'message': f'User {user.username} unblocked successfully'})

class VendorRequestViewSet(viewsets.ViewSet):
    """
    Explicitly handle vendor applications (for Adminservice)
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        pending = VendorProfile.objects.filter(approval_status='pending').select_related('user')
        serializer = AdminVendorListSerializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        vendor = generics.get_object_or_404(VendorProfile, pk=pk)
        vendor.approval_status = 'approved'
        vendor.save()
        
        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='approved',
            reason=request.data.get('reason', '')
        )
        return Response({'message': 'Vendor approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        vendor = generics.get_object_or_404(VendorProfile, pk=pk)
        vendor.approval_status = 'rejected'
        vendor.rejection_reason = request.data.get('reason', 'Rejected by admin')
        vendor.save()
        
        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='rejected',
            reason=vendor.rejection_reason
        )
        return Response({'message': 'Vendor rejected'})

class AdminVendorViewSet(viewsets.ViewSet):
    """
    Manage All Vendors (Block/Unblock/List)
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        vendors = VendorProfile.objects.select_related('user').all()
        serializer = AdminVendorListSerializer(vendors, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        vendor = generics.get_object_or_404(VendorProfile, pk=pk)
        serializer = AdminVendorDetailSerializer(vendor)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        vendor = generics.get_object_or_404(VendorProfile, pk=pk)
        reason = request.data.get('reason', 'Violation of terms')
        vendor.is_blocked = True
        vendor.blocked_reason = reason
        vendor.save()
        
        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='blocked',
            reason=reason
        )
        return Response({'message': 'Vendor blocked'})

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        vendor = generics.get_object_or_404(VendorProfile, pk=pk)
        vendor.is_blocked = False
        vendor.save()
        
        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='unblocked'
        )
        return Response({'message': 'Vendor unblocked'})

class AdminProductViewSet(viewsets.ViewSet):
    """
    Manage Products (Moderation)
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        products = Product.objects.all().select_related('vendor').prefetch_related('images')
        serializer = AdminProductDetailSerializer(products, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get full product details for admin view"""
        product = generics.get_object_or_404(Product, pk=pk)
        serializer = AdminProductDetailSerializer(product)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        product = generics.get_object_or_404(Product, pk=pk)
        reason = request.data.get('reason', 'Policy violation')
        product.is_blocked = True
        product.blocked_reason = reason
        product.save()
        
        ProductApprovalLog.objects.create(
            product=product,
            admin_user=request.user,
            action='blocked',
            reason=reason
        )
        return Response({'message': f'Product {product.name} blocked'})

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        product = generics.get_object_or_404(Product, pk=pk)
        product.is_blocked = False
        product.save()
        
        ProductApprovalLog.objects.create(
            product=product,
            admin_user=request.user,
            action='unblocked'
        )
        return Response({'message': f'Product {product.name} unblocked'})

class AdminOrderViewSet(viewsets.ViewSet):
    """
    Admin Order Management - view all orders, update status, assign delivery
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List all orders with their items, address, and vendor info"""
        orders = Order.objects.all().select_related(
            'user', 'delivery_agent', 'delivery_address'
        ).prefetch_related(
            'items__vendor', 'items__product'
        ).order_by('-created_at')
        
        data = []
        for order in orders:
            items = []
            for item in order.items.all():
                items.append({
                    'id': item.id,
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'subtotal': str(item.subtotal),
                    'vendor_status': item.vendor_status,
                    'vendor_name': item.vendor.shop_name if item.vendor else 'N/A',
                    'vendor_id': item.vendor.id if item.vendor else None,
                })
            
            data.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer': order.user.username,
                'customer_email': order.user.email,
                'status': order.status,
                'total_amount': str(order.total_amount),
                'payment_method': order.payment_method,
                'payment_status': order.payment_status,
                'delivery_agent': order.delivery_agent.user.username if order.delivery_agent else None,
                'delivery_address': order.delivery_address.full_address if order.delivery_address else "No Address",
                'delivery_city': order.delivery_address.city if order.delivery_address else "City N/A",
                'created_at': order.created_at,
                'items': items,
            })
        return Response(data)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Admin updates order item status"""
        order_item = generics.get_object_or_404(OrderItem, pk=pk)
        new_status = request.data.get('status')
        valid_statuses = dict(OrderItem.VENDOR_STATUS_CHOICES)
        if new_status not in valid_statuses:
            return Response({'error': f'Invalid status. Valid: {list(valid_statuses.keys())}'}, status=400)

        order_item.vendor_status = new_status
        order_item.save()

        # Sync main order status based on all items
        order = order_item.order
        all_items = order.items.all()
        all_statuses = [item.vendor_status for item in all_items]
        
        if all(s == 'delivered' for s in all_statuses):
            order.status = 'delivered'
        elif any(s == 'cancelled' for s in all_statuses) and all(s in ['cancelled', 'delivered'] for s in all_statuses):
            order.status = 'delivered'
        elif any(s in ['shipped', 'out_for_delivery'] for s in all_statuses):
            order.status = 'shipping'
        elif any(s == 'confirmed' for s in all_statuses):
            order.status = 'confirmed'
        elif all(s == 'cancelled' for s in all_statuses):
            order.status = 'cancelled'
        else:
            order.status = 'pending'
            
        order.save()

        return Response({
            'message': 'Status updated',
            'vendor_status': order_item.vendor_status,
            'order_status': order.status
        })

    @action(detail=True, methods=['post'])
    def assign_delivery(self, request, pk=None):
        """Admin assigns delivery agent to an order"""
        try:
            order = generics.get_object_or_404(Order, pk=pk)
            agent_id = request.data.get('agent_id')
            if not agent_id:
                return Response({'error': 'agent_id required'}, status=400)

            agent = generics.get_object_or_404(DeliveryAgentProfile, pk=agent_id)
            
            # Create or update DeliveryAssignment
            # For simplicity, we assume one assignment per order for now
            assignment, created = DeliveryAssignment.objects.update_or_create(
                order=order,
                defaults={
                    'agent': agent,
                    'status': 'assigned',
                    'delivery_fee': Decimal('50.00'), # Default fee, can be adjusted
                    'delivery_address': order.delivery_address.full_address if order.delivery_address else "No Address",
                    'delivery_city': order.delivery_address.city if order.delivery_address else "",
                    'pickup_address': "Multiple Vendors" if order.items.count() > 1 else (order.items.first().vendor.address if order.items.first().vendor else "N/A"),
                    'estimated_delivery_date': (timezone.now() + timedelta(days=2)).date()
                }
            )

            order.delivery_agent = agent
            order.status = 'shipping'
            order.save()

            # Create tracking record
            OrderTracking.objects.create(
                order=order,
                status='shipping',
                notes=f"Delivery agent {agent.user.username} assigned by Admin. Awaiting agent acceptance."
            )

            return Response({
                'message': f'Delivery agent {agent.user.username} assigned and status updated',
                'order_status': order.status,
                'assignment_id': assignment.id
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class AdminDeliveryViewSet(viewsets.ViewSet):
    """
    Manage Delivery Agents (Approve/Reject/Block)
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        agents = DeliveryAgentProfile.objects.filter(approval_status='pending').select_related('user')
        data = []
        for a in agents:
            data.append({
                'id': a.id,
                'user_name': a.user.username,
                'user_email': a.user.email,
                'vehicle_type': a.vehicle_type,
                'city': a.city,
                'approval_status': a.approval_status
            })
        return Response(data)

    def list(self, request):
        status_param = request.query_params.get('status')
        agents = DeliveryAgentProfile.objects.select_related('user').all()
        
        if status_param:
            agents = agents.filter(approval_status=status_param)
            
        data = []
        for a in agents:
            data.append({
                'id': a.id,
                'username': a.user.username,
                'email': a.user.email,
                'phone': a.phone_number,
                'approval_status': a.approval_status,
                'is_blocked': a.is_blocked,
                'vehicle_type': a.vehicle_type,
                'vehicle_number': a.vehicle_number,
                'city': a.city,
                'state': a.state,
                'average_rating': float(a.average_rating),
                'completed_deliveries': a.completed_deliveries,
                'created_at': a.created_at
            })
        return Response(data)

    def retrieve(self, request, pk=None):
        agent = generics.get_object_or_404(DeliveryAgentProfile, pk=pk)
        data = {
            'id': agent.id,
            'username': agent.user.username,
            'email': agent.user.email,
            'phone': agent.phone_number,
            'approval_status': agent.approval_status,
            'is_blocked': agent.is_blocked,
            'vehicle_type': agent.vehicle_type,
            'vehicle_number': agent.vehicle_number,
            'license_number': agent.license_number,
            'bank_name': agent.bank_name,
            'average_rating': float(agent.average_rating),
            'completed_deliveries': agent.completed_deliveries,
            'total_earnings': float(agent.total_earnings),
            'created_at': agent.created_at
        }
        return Response(data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        agent = generics.get_object_or_404(DeliveryAgentProfile, pk=pk)
        agent.approval_status = 'approved'
        agent.approved_at = timezone.now()
        agent.save()
        
        DeliveryAgentApprovalLog.objects.create(
            agent=agent,
            admin_user=request.user,
            action='approved',
            reason=request.data.get('reason', '')
        )
        return Response({'message': 'Delivery agent approved successfully'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        agent = generics.get_object_or_404(DeliveryAgentProfile, pk=pk)
        agent.approval_status = 'rejected'
        agent.rejection_reason = request.data.get('reason', 'Rejected by admin')
        agent.save()
        
        DeliveryAgentApprovalLog.objects.create(
            agent=agent,
            admin_user=request.user,
            action='rejected',
            reason=agent.rejection_reason
        )
        return Response({'message': 'Delivery agent rejected'})

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        agent = generics.get_object_or_404(DeliveryAgentProfile, pk=pk)
        agent.is_blocked = True
        agent.blocked_reason = request.data.get('reason', 'Blocked by admin')
        agent.save()
        return Response({'message': 'Delivery agent blocked'})

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        agent = generics.get_object_or_404(DeliveryAgentProfile, pk=pk)
        agent.is_blocked = False
        agent.save()
        return Response({'message': 'Delivery agent unblocked'})

class AdminSystemConfigViewSet(viewsets.ViewSet):
    """
    System Settings Management
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        config, created = SystemConfiguration.objects.get_or_create(id=1)
        return Response({
            'vendor_commission': str(config.default_vendor_commission_percentage),
            'agent_commission': str(config.default_delivery_agent_commission_percentage),
            'refund_window': config.refund_window_days,
            'min_withdrawal': str(config.minimum_withdrawal_amount),
            'maintenance_mode': config.is_maintenance_mode,
            'support_email': config.support_email
        })

    @action(detail=False, methods=['post'])
    def update_config(self, request):
        config, created = SystemConfiguration.objects.get_or_create(id=1)
        if 'vendor_commission' in request.data:
            config.default_vendor_commission_percentage = request.data['vendor_commission']
        if 'agent_commission' in request.data:
            config.default_delivery_agent_commission_percentage = request.data['agent_commission']
        if 'maintenance_mode' in request.data:
            config.is_maintenance_mode = request.data['maintenance_mode']
        config.updated_by = request.user
        config.save()
        return Response({'message': 'System configuration updated'})

class AdminReportViewSet(viewsets.ViewSet):
    """
    Admin Reports
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def sales_revenue(self, request):
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Aggregate daily sales
        from django.db.models.functions import TruncDate
        daily_sales = Order.objects.filter(
            created_at__gte=start_date,
            status='delivered'
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            revenue=Sum('total_amount'),
            count=Count('id')
        ).order_by('date')

        chart_data = []
        for s in daily_sales:
            chart_data.append({
                'date': s['date'].strftime('%Y-%m-%d'),
                'revenue': str(s['revenue']),
                'count': s['count']
            })

        total_orders = Order.objects.filter(created_at__gte=start_date)
        total_revenue = total_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        return Response({
            'period': f'Last {days} days',
            'total_revenue': str(total_revenue),
            'total_count': total_orders.count(),
            'chart_data': chart_data
        })

    @action(detail=False, methods=['get'])
    def activity_logs(self, request):
        logs = ActivityLog.objects.all()[:100]
        data = []
        for l in logs:
            data.append({
                'type': l.activity_type,
                'description': l.description,
                'user': l.user.username if l.user else 'System',
                'timestamp': l.created_at
            })
        return Response(data)