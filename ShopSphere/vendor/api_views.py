from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q, Sum, Avg, Count, F
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    VendorProfile, Product, ProductImage, VendorSalesAnalytics,
    VendorCommission, VendorPayment, VendorOrderSummary
)
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductCreateUpdateSerializer,
    VendorProfileListSerializer, VendorProfileDetailSerializer, VendorProfileCreateSerializer,
    VendorSalesAnalyticsSerializer, VendorCommissionSerializer, VendorPaymentSerializer,
    VendorOrderSummarySerializer, VendorDashboardSerializer
)
from user.models import Order, OrderItem, AuthUser

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100



# ===============================================
#           VENDOR DASHBOARD VIEW
# ===============================================

class VendorDashboardView(generics.RetrieveAPIView):
    """Get comprehensive vendor dashboard with stats and recent data"""
    permission_classes = [IsAuthenticated]
    serializer_class = VendorDashboardSerializer
    
    def get_object(self):
        try:
            return VendorProfile.objects.get(user=self.request.user)
        except VendorProfile.DoesNotExist:
            raise Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def retrieve(self, request, *args, **kwargs):
        try:
            vendor = self.get_object()
            
            # Check if vendor is approved
            if vendor.approval_status != 'approved':
                return Response({
                    'error': 'Vendor account not approved',
                    'status': vendor.approval_status,
                    'rejection_reason': vendor.rejection_reason
                }, status=status.HTTP_403_FORBIDDEN)
            
            if vendor.is_blocked:
                return Response({
                    'error': 'Vendor account is blocked',
                    'reason': vendor.blocked_reason
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = self.get_serializer(vendor)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#           VENDOR PROFILE VIEWSET
# ===============================================

class VendorProfileViewSet(viewsets.ViewSet):
    """Vendor profile management"""
    permission_classes = [IsAuthenticated]
    
    def get_vendor(self, request):
        """Get current vendor profile"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            serializer = VendorProfileDetailSerializer(vendor)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def update_profile(self, request):
        """Update vendor profile"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            
            # Only allow updating certain fields
            allowed_fields = ['shop_description', 'address', 'shipping_fee', 'service_cities']
            for field in allowed_fields:
                if field in request.data:
                    setattr(vendor, field, request.data[field])
            
            vendor.save()
            serializer = VendorProfileDetailSerializer(vendor)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#          PRODUCT MANAGEMENT VIEWSET
# ===============================================

class ProductViewSet(viewsets.ModelViewSet):
    """Complete CRUD operations for vendor products"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """Get only products belonging to current vendor"""
        try:
            vendor = VendorProfile.objects.get(user=self.request.user)
            return Product.objects.filter(vendor=vendor).order_by('-created_at')
        except VendorProfile.DoesNotExist:
            return Product.objects.none()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        elif self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Create new product"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            
            if vendor.is_blocked:
                return Response({'error': 'Vendor account is blocked'}, status=status.HTTP_403_FORBIDDEN)
            
            if vendor.approval_status != 'approved':
                return Response({'error': 'Vendor not approved'}, status=status.HTTP_403_FORBIDDEN)
            
            images = request.FILES.getlist('images')
            if len(images) < 4:
                return Response({
                    'error': 'Minimum 4 product images required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            product = Product.objects.create(
                vendor=vendor,
                **serializer.validated_data
            )
            
            for image in images:
                ProductImage.objects.create(product=product, image=image)
            
            vendor.total_products = Product.objects.filter(vendor=vendor).count()
            vendor.save()
            
            return Response(
                ProductDetailSerializer(product).data,
                status=status.HTTP_201_CREATED
            )
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Update product"""
        try:
            product = self.get_object()
            
            if product.vendor.user != request.user:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = self.get_serializer(product, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            # Handle image updates
            images = request.FILES.getlist('images')
            if images:
                if len(images) < 4:
                    return Response({'error': 'Minimum 4 images required'}, status=status.HTTP_400_BAD_REQUEST)
                
                product.images.all().delete()
                for image in images:
                    ProductImage.objects.create(product=product, image=image)
            
            return Response(
                ProductDetailSerializer(product).data,
                status=status.HTTP_200_OK
            )
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        """Delete product"""
        try:
            product = self.get_object()
            
            if product.vendor.user != request.user:
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
            product.delete()
            
            vendor = VendorProfile.objects.get(user=request.user)
            vendor.total_products = Product.objects.filter(vendor=vendor).count()
            vendor.save()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active products"""
        queryset = self.get_queryset().filter(status='active', is_blocked=False)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search products by name or category"""
        search_term = request.query_params.get('q', '')
        queryset = self.get_queryset()
        
        if search_term:
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term) |
                Q(category__icontains=search_term)
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ===============================================
#         VENDOR ORDERS VIEWSET
# ===============================================

class VendorOrdersViewSet(viewsets.ViewSet):
    """Manage vendor's orders and order items"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def list(self, request):
        """Get all orders for vendor's products"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            order_items = OrderItem.objects.filter(vendor=vendor).select_related('order').order_by('-order__created_at')
            
            # Filter by status
            status_filter = request.query_params.get('status')
            if status_filter:
                order_items = order_items.filter(vendor_status=status_filter)
            
            # Filter by date range
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            if from_date:
                order_items = order_items.filter(order__created_at__gte=from_date)
            if to_date:
                order_items = order_items.filter(order__created_at__lte=to_date)
            
            result = []
            for item in order_items:
                result.append({
                    'id': item.id,
                    'order_id': item.order.id,
                    'product': item.product.name,
                    'quantity': item.quantity,
                    'price': str(item.product_price),
                    'total': str(item.subtotal),
                    'vendor_status': item.vendor_status,
                    'order_status': item.order.status,
                    'customer': item.order.customer.get_full_name(),
                    'customer_email': item.order.customer.email,
                    'created_at': item.order.created_at,
                })
            
            return Response(result, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update order item status"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            order_item = OrderItem.objects.get(id=pk, vendor=vendor)
            
            new_status = request.data.get('status')
            if new_status not in dict(OrderItem.VENDOR_STATUS_CHOICES):
                return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
            
            order_item.vendor_status = new_status
            order_item.save()
            
            return Response({
                'message': 'Status updated successfully',
                'vendor_status': order_item.vendor_status
            }, status=status.HTTP_200_OK)
        except (VendorProfile.DoesNotExist, OrderItem.DoesNotExist):
            return Response({'error': 'Order item not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#      VENDOR SALES ANALYTICS VIEWSET
# ===============================================

class VendorSalesAnalyticsViewSet(viewsets.ViewSet):
    """Sales analytics and reporting for vendors"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get sales analytics for vendor"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            
            # Get period type from query params
            period = request.query_params.get('period', 'daily')
            days = int(request.query_params.get('days', 30))
            
            analytics = VendorSalesAnalytics.objects.filter(
                vendor=vendor,
                period_type=period,
                date__gte=timezone.now().date() - timedelta(days=days)
            ).order_by('-date')
            
            serializer = VendorSalesAnalyticsSerializer(analytics, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get sales summary for last 30 days"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            
            # Calculate from order items
            recent_orders = OrderItem.objects.filter(
                vendor=vendor,
                order__status__in=['delivered', 'completed'],
                order__created_at__gte=timezone.now() - timedelta(days=30)
            )
            
            total_revenue = recent_orders.aggregate(Sum('subtotal'))['subtotal__sum'] or Decimal('0.00')
            total_items = recent_orders.aggregate(Sum('quantity'))['quantity__sum'] or 0
            total_orders = recent_orders.values('order').distinct().count()
            
            return Response({
                'period': 'Last 30 Days',
                'total_revenue': str(total_revenue),
                'total_items_sold': total_items,
                'total_orders': total_orders,
                'average_order_value': str(total_revenue / total_orders if total_orders > 0 else 0),
            }, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#      VENDOR COMMISSION VIEWSET
# ===============================================

class VendorCommissionViewSet(viewsets.ViewSet):
    """Commission management for vendors"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def list(self, request):
        """Get all commissions for vendor"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            
            status_filter = request.query_params.get('status')
            queryset = VendorCommission.objects.filter(vendor=vendor).order_by('-created_at')
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            serializer = VendorCommissionSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get commission summary"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            
            total_pending = VendorCommission.objects.filter(
                vendor=vendor, status='pending'
            ).aggregate(Sum('commission_amount'))['commission_amount__sum'] or Decimal('0.00')
            
            total_approved = VendorCommission.objects.filter(
                vendor=vendor, status='approved'
            ).aggregate(Sum('commission_amount'))['commission_amount__sum'] or Decimal('0.00')
            
            total_paid = VendorCommission.objects.filter(
                vendor=vendor, status='paid'
            ).aggregate(Sum('commission_amount'))['commission_amount__sum'] or Decimal('0.00')
            
            return Response({
                'pending': str(total_pending),
                'approved': str(total_approved),
                'paid': str(total_paid),
                'total': str(total_pending + total_approved + total_paid),
            }, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#       VENDOR PAYMENT VIEWSET
# ===============================================

class VendorPaymentViewSet(viewsets.ViewSet):
    """Payment/payout management for vendors"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def list(self, request):
        """Get all payment records for vendor"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            queryset = VendorPayment.objects.filter(vendor=vendor).order_by('-created_at')
            
            serializer = VendorPaymentSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending payments"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            pending_amount = VendorPayment.objects.filter(
                vendor=vendor,
                status__in=['pending', 'processing']
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            
            return Response({
                'pending_amount': str(pending_amount)
            }, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#    VENDOR ORDER SUMMARY VIEWSET
# ===============================================

class VendorOrderSummaryViewSet(viewsets.ViewSet):
    """Order and performance summary for vendors"""
    permission_classes = [IsAuthenticated]
    
    def retrieve(self, request):
        """Get order summary for vendor"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            summary, created = VendorOrderSummary.objects.get_or_create(vendor=vendor)
            
            # Refresh metrics
            summary.refresh_metrics()
            
            serializer = VendorOrderSummarySerializer(summary)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
