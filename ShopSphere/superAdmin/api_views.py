from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from user.models import Order, OrderItem
from vendor.models import VendorProfile, Product, VendorCommission

User = get_user_model()

class AdminDashboardViewSet(viewsets.ViewSet):
    """
    API Endpoint for SuperAdmin Dashboard Statistics
    """
    permission_classes = [IsAdminUser]

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
                "revenue": total_revenue
            },
            "products": {
                "total": total_products,
                "active": active_products
            }
        })

class AdminUserViewSet(viewsets.ViewSet):
    """
    Manage Users (Block/Unblock)
    """
    permission_classes = [IsAdminUser]

    def list(self, request):
        users = User.objects.all().values('id', 'username', 'email', 'role', 'is_active', 'date_joined')
        return Response(users)

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
            user.is_active = False
            user.save()
            return Response({'message': f'User {user.username} blocked successfully'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
            user.is_active = True
            user.save()
            return Response({'message': f'User {user.username} unblocked successfully'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class AdminVendorViewSet(viewsets.ViewSet):
    """
    Manage Vendors (Approve/Reject/Block)
    """
    permission_classes = [IsAdminUser]

    def list(self, request):
        status_param = request.query_params.get('status')
        vendors = VendorProfile.objects.select_related('user').all()
        
        if status_param:
            vendors = vendors.filter(approval_status=status_param)
            
        data = []
        for v in vendors:
            data.append({
                'id': v.id,
                'username': v.user.username,
                'shop_name': v.shop_name,
                'approval_status': v.approval_status,
                'is_blocked': v.is_blocked,
                'created_at': v.created_at
            })
        return Response(data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        vendor = generics.get_object_or_404(VendorProfile, pk=pk)
        vendor.approval_status = 'approved'
        vendor.save()
        return Response({'message': 'Vendor approved successfully'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        vendor = generics.get_object_or_404(VendorProfile, pk=pk)
        vendor.approval_status = 'rejected'
        vendor.save()
        return Response({'message': 'Vendor rejected'})

class AdminReportViewSet(viewsets.ViewSet):
    """
    Admin Reports
    """
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'])
    def sales_revenue(self, request):
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        orders = Order.objects.filter(created_at__gte=start_date)
        revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        return Response({
            'period': f'Last {days} days',
            'total_orders': orders.count(),
            'total_revenue': revenue
        })

    @action(detail=False, methods=['get'])
    def commission_settings(self, request):
        # Placeholder for commission settings logic
        return Response({
            'default_commission_rate': 10.0,
            'delivery_commission_rate': 5.0
        })