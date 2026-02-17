from rest_framework import serializers
from django.db.models import Sum, Avg
from .models import (
    VendorProfile, Product, ProductImage, VendorSalesAnalytics,
    VendorCommission, VendorPayment, VendorOrderSummary,
    ProductVariant, InventoryAlert, ProductBundle, BundleProduct,
    BulkProductUpload, SellerPerformanceRating, VendorWallet, VendorPayout
)
from user.models import Order, OrderItem
from decimal import Decimal


# ===============================================
#          PRODUCT IMAGE SERIALIZER
# ===============================================

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


# ===============================================
#            PRODUCT SERIALIZER
# ===============================================

class ProductListSerializer(serializers.ModelSerializer):
    """Product listing serializer"""
    images = ProductImageSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.shop_name', read_only=True)
    available_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'quantity', 'available_quantity',
            'category', 'status', 'is_blocked', 'vendor_name',
            'average_rating', 'total_reviews', 'images', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'average_rating', 'total_reviews']
    
    def get_available_quantity(self, obj):
        return obj.get_available_quantity()


class ProductDetailSerializer(serializers.ModelSerializer):
    """Product detail serializer with full information"""
    images = ProductImageSerializer(many=True, read_only=True)
    vendor = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'vendor', 'name', 'description', 'category',
            'price', 'quantity', 'available_quantity', 'status',
            'is_blocked', 'blocked_reason', 'total_sold',
            'average_rating', 'total_reviews', 'views_count',
            'images', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'average_rating',
            'total_reviews', 'views_count', 'total_sold'
        ]
    
    def get_vendor(self, obj):
        return {
            'id': obj.vendor.id,
            'shop_name': obj.vendor.shop_name,
            'average_rating': float(obj.vendor.average_rating),
            'total_reviews': obj.vendor.total_reviews,
        }
    
    def get_available_quantity(self, obj):
        return obj.get_available_quantity()


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Product creation and update serializer"""
    images = ProductImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'category', 'price',
            'quantity', 'status', 'images'
        ]
        read_only_fields = ['id']


# ===============================================
#        VENDOR SALES ANALYTICS SERIALIZER
# ===============================================

class VendorSalesAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorSalesAnalytics
        fields = [
            'id', 'period_type', 'date', 'total_orders',
            'total_items_sold', 'total_revenue', 'average_order_value',
            'unique_customers', 'returning_customers', 'completed_orders',
            'cancelled_orders', 'returned_orders', 'top_selling_product',
            'category_performance'
        ]
        read_only_fields = [
            'id', 'total_orders', 'total_items_sold', 'total_revenue',
            'average_order_value', 'unique_customers', 'returning_customers',
            'completed_orders', 'cancelled_orders', 'returned_orders',
            'top_selling_product', 'category_performance'
        ]


# ===============================================
#         VENDOR COMMISSION SERIALIZER
# ===============================================

class VendorCommissionSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.id', read_only=True)
    commission_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = VendorCommission
        fields = [
            'id', 'order_id', 'commission_rate', 'order_amount',
            'commission_amount', 'commission_percentage', 'status',
            'created_at', 'approved_at', 'paid_at', 'notes'
        ]
        read_only_fields = [
            'id', 'created_at', 'approved_at', 'paid_at'
        ]
    
    def get_commission_percentage(self, obj):
        if obj.order_amount > 0:
            return float((obj.commission_amount / obj.order_amount) * 100)
        return 0


# ===============================================
#         VENDOR PAYMENT SERIALIZER
# ===============================================

class VendorPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorPayment
        fields = [
            'id', 'payment_method', 'amount', 'from_date', 'to_date',
            'total_commissions', 'status', 'transaction_id', 'utr_number',
            'notes', 'failed_reason', 'created_at', 'processed_at',
            'completed_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'processed_at', 'completed_at'
        ]


# ===============================================
#       VENDOR ORDER SUMMARY SERIALIZER
# ===============================================

class VendorOrderSummarySerializer(serializers.ModelSerializer):
    pending_commission_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = VendorOrderSummary
        fields = [
            'id', 'total_orders', 'pending_orders', 'processing_orders',
            'shipped_orders', 'delivered_orders', 'cancelled_orders',
            'returned_orders', 'total_customers', 'repeat_customers',
            'total_revenue', 'total_commission_paid', 'pending_commission',
            'pending_commission_amount', 'average_rating', 'total_reviews'
        ]
        read_only_fields = [
            'id', 'total_orders', 'pending_orders', 'processing_orders',
            'shipped_orders', 'delivered_orders', 'cancelled_orders',
            'returned_orders', 'total_customers', 'repeat_customers',
            'total_revenue', 'total_commission_paid', 'pending_commission',
            'average_rating', 'total_reviews'
        ]
    
    def get_pending_commission_amount(self, obj):
        return str(obj.pending_commission)


# ===============================================
#         VENDOR PROFILE SERIALIZER
# ===============================================

class VendorProfileListSerializer(serializers.ModelSerializer):
    """Vendor profile listing serializer"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = VendorProfile
        fields = [
            'id', 'shop_name', 'shop_description', 'user_name', 'user_email',
            'business_type', 'approval_status', 'is_blocked', 'total_products',
            'total_orders', 'total_revenue', 'average_rating', 'total_reviews',
            'created_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'total_products', 'total_orders',
            'total_revenue', 'average_rating', 'total_reviews'
        ]


class VendorProfileDetailSerializer(serializers.ModelSerializer):
    """Detailed vendor profile serializer"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    products_count = serializers.SerializerMethodField()
    pending_commission = serializers.SerializerMethodField()
    
    class Meta:
        model = VendorProfile
        fields = [
            'id', 'shop_name', 'shop_description', 'address', 'business_type',
            'user_email', 'user_phone', 'gst_number', 'pan_number', 'pan_name',
            'approval_status', 'rejection_reason', 'is_blocked', 'blocked_reason',
            'bank_holder_name', 'bank_account_number', 'bank_ifsc_code',
            'shipping_fee', 'total_products', 'total_orders', 'total_revenue',
            'average_rating', 'total_reviews', 'products_count',
            'pending_commission', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'approval_status',
            'is_blocked', 'total_products', 'total_orders',
            'total_revenue', 'average_rating', 'total_reviews'
        ]
    
    def get_products_count(self, obj):
        return obj.products.count()
    
    def get_pending_commission(self, obj):
        return str(obj.get_pending_commission())


class VendorProfileCreateSerializer(serializers.ModelSerializer):
    """Vendor registration/creation serializer"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = VendorProfile
        fields = [
            'shop_name', 'shop_description', 'address', 'business_type',
            'gst_number', 'pan_number', 'pan_name', 'bank_holder_name',
            'bank_account_number', 'bank_ifsc_code', 'shipping_fee',
            'password', 'password_confirm'
        ]
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        # Create user and vendor profile
        from user.models import AuthUser
        
        password = validated_data.pop('password')
        user = AuthUser.objects.create_user(
            username=validated_data['shop_name'].lower().replace(' ', '_'),
            role='vendor',
            **{'first_name': validated_data['shop_name']}
        )
        user.set_password(password)
        user.save()
        
        vendor = VendorProfile.objects.create(user=user, **validated_data)
        return vendor


# ===============================================
#     VENDOR DASHBOARD SERIALIZER
# ===============================================

class VendorDashboardSerializer(serializers.Serializer):
    """Comprehensive vendor dashboard data"""
    profile = VendorProfileDetailSerializer(read_only=True)
    order_summary = VendorOrderSummarySerializer(read_only=True)
    recent_orders = serializers.SerializerMethodField()
    recent_analytics = serializers.SerializerMethodField()
    pending_commissions = VendorCommissionSerializer(many=True, read_only=True)
    
    def get_recent_orders(self, obj):
        from user.models import OrderItem
        recent = OrderItem.objects.filter(vendor=obj).order_by('-order__created_at')[:10]
        return [{
            'id': item.order.id,
            'product': item.product.name,
            'quantity': item.quantity,
            'total_price': str(item.total_price),
            'vendor_status': item.vendor_status,
            'created_at': item.order.created_at
        } for item in recent]
    
    def get_recent_analytics(self, obj):
        recent = obj.sales_analytics.filter(period_type='daily').order_by('-date')[:7]
        return VendorSalesAnalyticsSerializer(recent, many=True).data

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating products"""
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'quantity', 'status']


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product list view"""
    vendor_name = serializers.CharField(source='vendor.shop_name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category', 'vendor_name', 'price', 'quantity',
            'status', 'is_blocked', 'created_at'
        ]