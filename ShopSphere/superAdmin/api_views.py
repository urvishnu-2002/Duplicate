from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.contrib.auth import get_user_model
# User = get_user_model() - Moved inside functions to avoid AppRegistryNotReady error

from django.db.models import Q
from vendor.models import VendorProfile, Product
from deliveryAgent.models import DeliveryProfile
from .models import VendorApprovalLog, ProductApprovalLog, DeliveryAgentApprovalLog
from .serializers import (
    VendorApprovalLogSerializer, ProductApprovalLogSerializer,
    AdminVendorDetailSerializer, AdminProductDetailSerializer,
    AdminVendorListSerializer, AdminProductListSerializer,
    ApproveVendorSerializer, RejectVendorSerializer,
    BlockVendorSerializer, UnblockVendorSerializer,
    BlockProductSerializer, UnblockProductSerializer,
    AdminDeliveryAgentDetailSerializer, AdminDeliveryAgentListSerializer,
    ApproveDeliveryAgentSerializer, RejectDeliveryAgentSerializer,
    BlockDeliveryAgentSerializer, UnblockDeliveryAgentSerializer,
    DeliveryAgentApprovalLogSerializer
)

class AdminLoginRequiredMixin:
    """Ensure user is admin"""
    permission_classes = [IsAuthenticated, IsAdminUser]

class VendorRequestViewSet(AdminLoginRequiredMixin, viewsets.ModelViewSet):
    """Manage vendor approval requests"""
    queryset = VendorProfile.objects.filter(approval_status='pending')
    serializer_class = AdminVendorDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def list(self, request, *args, **kwargs):
        queryset = VendorProfile.objects.filter(approval_status='pending')
        
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(shop_name__icontains=search) |
                Q(user__email__icontains=search)
            )
        
        serializer = AdminVendorDetailSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        vendor = self.get_object()
        
        if vendor.approval_status != 'pending':
            return Response({
                'error': 'Only pending vendors can be approved'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ApproveVendorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        vendor.approval_status = 'approved'
        vendor.save()
        
        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='approved',
            reason=serializer.validated_data.get('reason', '')
        )
        
        return Response({
            'message': 'Vendor approved successfully',
            'vendor': AdminVendorDetailSerializer(vendor).data
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        vendor = self.get_object()
        
        if vendor.approval_status != 'pending':
            return Response({
                'error': 'Only pending vendors can be rejected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = RejectVendorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        vendor.approval_status = 'rejected'
        vendor.rejection_reason = serializer.validated_data['reason']
        vendor.save()
        
        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='rejected',
            reason=serializer.validated_data['reason']
        )
        
        return Response({
            'message': 'Vendor rejected successfully',
            'vendor': AdminVendorDetailSerializer(vendor).data
        })

class VendorManagementViewSet(AdminLoginRequiredMixin, viewsets.ModelViewSet):
    queryset = VendorProfile.objects.exclude(approval_status='pending')
    serializer_class = AdminVendorListSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def list(self, request, *args, **kwargs):
        queryset = VendorProfile.objects.all()
        
        status_filter = request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(approval_status=status_filter)
        
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(shop_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__username__icontains=search)
            )
        
        blocked_filter = request.query_params.get('blocked', None)
        if blocked_filter == 'true':
            queryset = queryset.filter(is_blocked=True)
        elif blocked_filter == 'false':
            queryset = queryset.filter(is_blocked=False)
        
        serializer = AdminVendorListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def detail(self, request, pk=None):
        vendor = self.get_object()
        serializer = AdminVendorDetailSerializer(vendor)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        vendor = self.get_object()
        
        serializer = BlockVendorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        vendor.is_blocked = True
        vendor.blocked_reason = serializer.validated_data['reason']
        vendor.save()
        
        Product.objects.filter(vendor=vendor).update(is_blocked=True)
        
        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='blocked',
            reason=serializer.validated_data['reason']
        )
        
        return Response({
            'message': 'Vendor blocked successfully',
            'vendor': AdminVendorDetailSerializer(vendor).data
        })
    
    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        vendor = self.get_object()
        
        serializer = UnblockVendorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        vendor.is_blocked = False
        vendor.blocked_reason = ''
        vendor.save()
        
        VendorApprovalLog.objects.create(
            vendor=vendor,
            admin_user=request.user,
            action='unblocked',
            reason=serializer.validated_data.get('reason', '')
        )
        
        return Response({
            'message': 'Vendor unblocked successfully',
            'vendor': AdminVendorDetailSerializer(vendor).data
        })

class ProductManagementViewSet(AdminLoginRequiredMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = AdminProductListSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def list(self, request, *args, **kwargs):
        queryset = Product.objects.all()
        
        status_filter = request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        blocked_filter = request.query_params.get('blocked', None)
        if blocked_filter == 'true':
            queryset = queryset.filter(is_blocked=True)
        elif blocked_filter == 'false':
            queryset = queryset.filter(is_blocked=False)
        
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(vendor__shop_name__icontains=search)
            )
        
        vendor_id = request.query_params.get('vendor_id', None)
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        serializer = AdminProductListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def detail(self, request, pk=None):
        product = self.get_object()
        serializer = AdminProductDetailSerializer(product)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        product = self.get_object()
        
        serializer = BlockProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product.is_blocked = True
        product.blocked_reason = serializer.validated_data['reason']
        product.save()
        
        ProductApprovalLog.objects.create(
            product=product,
            admin_user=request.user,
            action='blocked',
            reason=serializer.validated_data['reason']
        )
        
        return Response({
            'message': 'Product blocked successfully',
            'product': AdminProductDetailSerializer(product).data
        })
    
    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        product = self.get_object()
        
        serializer = UnblockProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product.is_blocked = False
        product.blocked_reason = ''
        product.save()
        
        ProductApprovalLog.objects.create(
            product=product,
            admin_user=request.user,
            action='unblocked',
            reason=serializer.validated_data.get('reason', '')
        )
        
        return Response({
            'message': 'Product unblocked successfully',
            'product': AdminProductDetailSerializer(product).data
        })


class DashboardView(AdminLoginRequiredMixin, generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        total_vendors = VendorProfile.objects.count()
        pending_vendors = VendorProfile.objects.filter(approval_status='pending').count()
        approved_vendors = VendorProfile.objects.filter(approval_status='approved').count()
        blocked_vendors = VendorProfile.objects.filter(is_blocked=True).count()
        
        total_products = Product.objects.count()
        pending_products = Product.objects.filter(status='pending').count()
        approved_products = Product.objects.filter(status='approved').count()
        blocked_products = Product.objects.filter(is_blocked=True).count()
        
        return Response({
            'vendors': {
                'total': total_vendors,
                'pending': pending_vendors,
                'approved': approved_vendors,
                'blocked': blocked_vendors
            },
            'products': {
                'total': total_products,
                'pending': pending_products,
                'approved': approved_products,
                'blocked': blocked_products
            }
        })


class DeliveryAgentRequestViewSet(AdminLoginRequiredMixin, viewsets.ModelViewSet):
    """Manage delivery agent approval requests"""
    queryset = DeliveryProfile.objects.filter(approval_status='pending')
    serializer_class = AdminDeliveryAgentDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def list(self, request, *args, **kwargs):
        queryset = DeliveryProfile.objects.filter(approval_status='pending')
        
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(company_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        serializer = AdminDeliveryAgentDetailSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        agent = self.get_object()
        
        if agent.approval_status != 'pending':
            return Response({
                'error': 'Only pending agents can be approved'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ApproveDeliveryAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        agent.approval_status = 'approved'
        agent.save()
        
        DeliveryAgentApprovalLog.objects.create(
            delivery_agent=agent,
            admin_user=request.user,
            action='approved',
            reason=serializer.validated_data.get('reason', '')
        )
        
        return Response({
            'message': 'Delivery agent approved successfully',
            'agent': AdminDeliveryAgentDetailSerializer(agent).data
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        agent = self.get_object()
        
        if agent.approval_status != 'pending':
            return Response({
                'error': 'Only pending agents can be rejected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = RejectDeliveryAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        agent.approval_status = 'rejected'
        agent.rejection_reason = serializer.validated_data['reason']
        agent.save()
        
        DeliveryAgentApprovalLog.objects.create(
            delivery_agent=agent,
            admin_user=request.user,
            action='rejected',
            reason=serializer.validated_data['reason']
        )
        
        return Response({
            'message': 'Delivery agent rejected successfully',
            'agent': AdminDeliveryAgentDetailSerializer(agent).data
        })


class DeliveryAgentManagementViewSet(AdminLoginRequiredMixin, viewsets.ModelViewSet):
    """Manage approved delivery agents"""
    queryset = DeliveryProfile.objects.exclude(approval_status='pending')
    serializer_class = AdminDeliveryAgentListSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def list(self, request, *args, **kwargs):
        queryset = DeliveryProfile.objects.all()
        
        status_filter = request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(approval_status=status_filter)
        
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(company_name__icontains=search) |
                Q(email__icontains=search) |
                Q(username__icontains=search)
            )
        
        blocked_filter = request.query_params.get('blocked', None)
        if blocked_filter == 'true':
            queryset = queryset.filter(is_blocked=True)
        elif blocked_filter == 'false':
            queryset = queryset.filter(is_blocked=False)
        
        serializer = AdminDeliveryAgentListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def detail(self, request, pk=None):
        agent = self.get_object()
        serializer = AdminDeliveryAgentDetailSerializer(agent)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        agent = self.get_object()
        
        serializer = BlockDeliveryAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        agent.is_blocked = True
        agent.blocked_reason = serializer.validated_data['reason']
        agent.save()
        
        DeliveryAgentApprovalLog.objects.create(
            delivery_agent=agent,
            admin_user=request.user,
            action='blocked',
            reason=serializer.validated_data['reason']
        )
        
        return Response({
            'message': 'Delivery agent blocked successfully',
            'agent': AdminDeliveryAgentDetailSerializer(agent).data
        })
    
    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        agent = self.get_object()
        
        serializer = UnblockDeliveryAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        agent.is_blocked = False
        agent.blocked_reason = ''
        agent.save()
        
        DeliveryAgentApprovalLog.objects.create(
            delivery_agent=agent,
            admin_user=request.user,
            action='unblocked',
            reason=serializer.validated_data.get('reason', '')
        )
        
        return Response({
            'message': 'Delivery agent unblocked successfully',
            'agent': AdminDeliveryAgentDetailSerializer(agent).data
        })