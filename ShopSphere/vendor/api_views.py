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
from user.models import Order, OrderItem, AuthUser, OrderTracking
from deliveryAgent.models import DeliveryAgentProfile, DeliveryAssignment

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
            raise VendorProfile.DoesNotExist()
    
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
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found. Are you registered as a vendor?'}, status=status.HTTP_403_FORBIDDEN)
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
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """Register a new vendor"""
        serializer = VendorProfileCreateSerializer(data=request.data)
        if serializer.is_valid():
            vendor = serializer.save()
            return Response({
                'message': 'Registration successful. Please wait for admin approval.',
                'vendor_id': vendor.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
        """Get only products belonging to current vendor, or all if admin"""
        if self.request.user.role == 'admin':
            return Product.objects.all().order_by('-created_at')
            
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
            return Response({'error': 'Vendor profile not found. Please register as a vendor first.'}, status=status.HTTP_403_FORBIDDEN)
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
    
    @action(detail=True, methods=['post'])
    def toggle_block(self, request, pk=None):
        """Allow admin to block/unblock a product"""
        if getattr(request.user, 'role', '') != 'admin':
            return Response({'error': 'Only admins can block/unblock products'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            product = self.get_object()
            product.is_blocked = not product.is_blocked
            if product.is_blocked:
                product.blocked_reason = request.data.get('reason', 'Violation of terms')
            else:
                product.blocked_reason = None
            product.save()
            return Response({
                'id': product.id,
                'name': product.name,
                'is_blocked': product.is_blocked,
                'blocked_reason': product.blocked_reason
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
                    'order_number': item.order.order_number,
                    'product': item.product_name,
                    'quantity': item.quantity,
                    'price': str(item.product_price),
                    'total': str(item.subtotal),
                    'vendor_status': item.vendor_status,
                    'order_status': item.order.status,
                    'customer': item.order.user.username, 
                    'customer_email': item.order.user.email,
                    'delivery_address': item.order.delivery_address.full_address if item.order.delivery_address else "No Address",
                    'delivery_city': item.order.delivery_address.city if item.order.delivery_address else "",
                    'created_at': item.order.created_at,
                    'has_delivery_assignment': hasattr(item.order, 'delivery_assignment'),
                    'delivery_agent': item.order.delivery_assignment.agent.user.username if hasattr(item.order, 'delivery_assignment') else None
                })
            
            return Response(result, status=status.HTTP_200_OK)
        except VendorProfile.DoesNotExist:
            return Response({'error': 'Vendor profile not found'}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def find_delivery_agents(self, request, pk=None):
        """Find approved delivery agents near the order's city"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            order_item = OrderItem.objects.get(id=pk, vendor=vendor)
            order = order_item.order
            
            city = ""
            if order.delivery_address:
                city = order.delivery_address.city
            
            # Simple city-based filter for "nearness"
            agents = DeliveryAgentProfile.objects.filter(
                approval_status='approved',
                is_blocked=False,
                city__icontains=city
            ).select_related('user')
            
            data = []
            for a in agents:
                # Suggested fee: 50 for local (same city), 100+ for out-of-city
                # Since we filter by city, they are all "local" in a sense, 
                # but we can check if the phone number prefix or other area indicators match if available.
                # For now, 50 is the base for local delivery.
                suggested_fee = 50 if city.lower() == a.city.lower() else 75
                
                data.append({
                    'id': a.id,
                    'name': a.user.username,
                    'phone': a.phone_number,
                    'vehicle': a.vehicle_type,
                    'city': a.city,
                    'is_online': a.availability_status == 'online',
                    'suggested_fee': suggested_fee
                })
            return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def assign_delivery_agent(self, request, pk=None):
        """Assign a delivery agent to an order"""
        try:
            vendor = VendorProfile.objects.get(user=request.user)
            order_item = OrderItem.objects.get(id=pk, vendor=vendor)
            order = order_item.order
            
            agent_id = request.data.get('agent_id')
            delivery_fee = request.data.get('delivery_fee') # Vendor specifies payout
            
            if not agent_id or not delivery_fee:
                return Response({'error': 'agent_id and delivery_fee required'}, status=400)
                
            agent = DeliveryAgentProfile.objects.get(id=agent_id)
            
            # Create or update assignment
            assignment, created = DeliveryAssignment.objects.update_or_create(
                order=order,
                defaults={
                    'agent': agent,
                    'status': 'assigned',
                    'delivery_fee': Decimal(str(delivery_fee)),
                    'pickup_address': vendor.address,
                    'delivery_address': order.delivery_address.full_address if order.delivery_address else "No Address",
                    'delivery_city': order.delivery_address.city if order.delivery_address else "",
                    'estimated_delivery_date': timezone.now().date() + timedelta(days=2)
                }
            )
            
            order.status = 'confirmed'
            order.delivery_agent = agent
            order.delivery_fee = Decimal(str(delivery_fee))
            order.save()

            OrderTracking.objects.create(
                order=order,
                status='confirmed',
                notes=f"Delivery agent {agent.user.username} assigned by Vendor."
            )
            
            return Response({'message': 'Delivery agent assigned successfully', 'assignment_id': assignment.id})
        except Exception as e:
            return Response({'error': str(e)}, status=400)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update order item status (vendor: waiting→confirmed→shipped; admin: out_for_delivery→delivered)"""
        try:
            new_status = request.data.get('status')
            if new_status not in dict(OrderItem.VENDOR_STATUS_CHOICES):
                return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

            # Admin can update any order item
            if request.user.role == 'admin':
                order_item = OrderItem.objects.get(id=pk)
            else:
                vendor = VendorProfile.objects.get(user=request.user)
                order_item = OrderItem.objects.get(id=pk, vendor=vendor)

            order_item.vendor_status = new_status
            order_item.save()

            # Sync the main Order status based on the status of all items in the order
            order = order_item.order
            all_items = order.items.all()
            all_statuses = [item.vendor_status for item in all_items]
            
            old_order_status = order.status
            
            if all(s == 'delivered' for s in all_statuses):
                order.status = 'delivered'
            elif any(s == 'cancelled' for s in all_statuses) and all(s in ['cancelled', 'delivered'] for s in all_statuses):
                # If some are cancelled and others are delivered, it's effectively delivered/completed
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

            # Create tracking entry if order status changed
            if old_order_status != order.status:
                OrderTracking.objects.create(
                    order=order,
                    status=order.status,
                    notes=f"Order status updated to {order.get_status_display()} by {request.user.role if request.user.role == 'admin' else 'Vendor'}"
                )
            # Create item-specific tracking if status is confirmed or shipped
            elif new_status in ['confirmed', 'shipped']:
                OrderTracking.objects.create(
                    order=order,
                    status=new_status,
                    notes=f"Item {order_item.product_name} status updated to {new_status} by Vendor"
                )

            return Response({
                'message': 'Status updated successfully',
                'vendor_status': order_item.vendor_status,
                'order_status': order.status
            }, status=status.HTTP_200_OK)
        except (VendorProfile.DoesNotExist, OrderItem.DoesNotExist):
            return Response({'error': 'Order item not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def admin_assign_delivery(self, request, pk=None):
        """Admin assigns a delivery agent to an order item and sets out_for_delivery"""
        if request.user.role != 'admin':
            return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
        try:
            order_item = OrderItem.objects.get(id=pk)
            agent_id = request.data.get('agent_id')
            if not agent_id:
                return Response({'error': 'agent_id required'}, status=status.HTTP_400_BAD_REQUEST)

            agent = DeliveryAgentProfile.objects.get(id=agent_id)
            order = order_item.order
            order.delivery_agent = agent
            order.status = 'shipping'
            order.save()

            # Item status stays 'shipped' until agent accepts
            # order_item.vendor_status = 'out_for_delivery' 
            # order_item.save()

            OrderTracking.objects.create(
                order=order,
                status='shipping',
                notes=f"Delivery agent {agent.user.username} assigned by Admin. Awaiting agent acceptance."
            )

            return Response({
                'message': f'Delivery agent {agent.user.username} assigned. Status: Out for Delivery',
                'vendor_status': order_item.vendor_status,
                'order_status': order.status
            }, status=status.HTTP_200_OK)
        except (OrderItem.DoesNotExist, DeliveryAgentProfile.DoesNotExist) as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
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
