from rest_framework import serializers
from .models import (AuthUser, Cart, CartItem, Order, OrderItem, Address, 
                     UserWallet, WalletTransaction, OrderReturn, Refund, 
                     TwoFactorAuth, Notification, Dispute, Coupon, CouponUsage)
from vendor.models import Product, ProductImage


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthUser
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = AuthUser.objects.create_user(**validated_data)
        return user


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'uploaded_at']


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'category', 'price', 
            'quantity', 'images', 'status', 'is_blocked', 'created_at'
        ]


class AddressSerializer(serializers.ModelSerializer):
    # Map frontend 'address' to model 'address_line1'
    address = serializers.CharField(source='address_line1')
    email = serializers.EmailField(required=False, allow_blank=True)
    
    class Meta:
        model = Address
        fields = ['id', 'name', 'phone', 'email', 'address', 'city', 'state', 'pincode', 'country', 'is_default']
        read_only_fields = ['id']

    def create(self, validated_data):
        # User is passed in save() from the view
        return Address.objects.create(**validated_data)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'user', 'payment_method', 'payment_status', 'total_amount', 
                  'status', 'delivery_address', 'created_at', 'items']


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price']

    def get_total_price(self, obj):
        return obj.get_total()


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_cart_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_cart_price']

    def get_total_cart_price(self, obj):
        return obj.get_total()


# ===============================================
#          WALLET & PAYMENT SERIALIZERS
# ===============================================

class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = '__all__'


class UserWalletSerializer(serializers.ModelSerializer):
    transactions = WalletTransactionSerializer(many=True, read_only=True)
    
    class Meta:
        model = UserWallet
        fields = ['id', 'balance', 'total_credited', 'total_debited', 'transactions', 'created_at']


# ===============================================
#          RETURN & REFUND SERIALIZERS
# ===============================================

class OrderReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReturn
        fields = '__all__'


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = '__all__'


# ===============================================
#          TWO-FACTOR AUTH SERIALIZER
# ===============================================

class TwoFactorAuthSerializer(serializers.ModelSerializer):
    class Meta:
        model = TwoFactorAuth
        fields = ['is_enabled', 'method', 'otp_verified_at']
        extra_kwargs = {'secret_key': {'write_only': True}}


# ===============================================
#          NOTIFICATION SERIALIZER
# ===============================================

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'created_at', 'read_at']


# ===============================================
#          DISPUTE SERIALIZER
# ===============================================

class DisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = '__all__'


# ===============================================
#          COUPON SERIALIZERS
# ===============================================

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'coupon_type', 'discount_value', 'min_purchase_amount',
                  'valid_from', 'valid_till', 'is_active']


class CouponUsageSerializer(serializers.ModelSerializer):
    coupon = CouponSerializer(read_only=True)
    
    class Meta:
        model = CouponUsage
        fields = '__all__'