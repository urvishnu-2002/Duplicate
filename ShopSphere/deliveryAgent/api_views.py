import sys
import random
from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (
    DeliveryAgentProfile, DeliveryAssignment, DeliveryTracking,
    DeliveryCommission, DeliveryPayment, DeliveryDailyStats, DeliveryFeedback
)
from .serializers import (
    DeliveryAgentProfileListSerializer, DeliveryAgentProfileDetailSerializer,
    DeliveryAgentProfileCreateSerializer, DeliveryAssignmentListSerializer,
    DeliveryAssignmentDetailSerializer, DeliveryTrackingSerializer,
    DeliveryCommissionSerializer, DeliveryPaymentSerializer,
    DeliveryDailyStatsSerializer, DeliveryFeedbackSerializer,
    DeliveryAgentDashboardSerializer
)


class DeliveryAgentProfileViewSet(viewsets.ViewSet):
    """Delivery agent profile management"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """Register a new delivery agent"""
        serializer = DeliveryAgentProfileCreateSerializer(
            data=request.data,
            context={'email': request.data.get('email')}
        )
        if serializer.is_valid():
            agent = serializer.save()
            return Response({
                'message': 'Registration successful. Please wait for admin approval.',
                'agent_id': agent.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def get_agent(self, request):
        """Get current delivery agent profile"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            serializer = DeliveryAgentProfileDetailSerializer(agent)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response(
                {'error': 'Delivery agent profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class DeliveryAssignmentViewSet(viewsets.ModelViewSet):
    """Manage delivery assignments"""
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        try:
            agent = DeliveryAgentProfile.objects.get(user=self.request.user)
            queryset = DeliveryAssignment.objects.filter(agent=agent).order_by('-assigned_at')
            
            status_filter = self.request.query_params.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
                
            return queryset
        except DeliveryAgentProfile.DoesNotExist:
            return DeliveryAssignment.objects.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return DeliveryAssignmentListSerializer
        return DeliveryAssignmentDetailSerializer

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept an assigned delivery"""
        assignment = self.get_object()
        if assignment.status == 'assigned':
            assignment.accept_delivery()
            return Response({'message': 'Order accepted', 'status': assignment.status})
        return Response(
            {'error': f'Cannot accept order in status: {assignment.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Confirm pickup from vendor"""
        assignment = self.get_object()
        if assignment.status == 'accepted':
            assignment.start_delivery()
            return Response({'message': 'Pickup confirmed', 'status': assignment.status})
        return Response(
            {'error': 'Must accept order first'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def in_transit(self, request, pk=None):
        """Mark delivery as in transit to customer"""
        assignment = self.get_object()
        if assignment.status in ['accepted', 'picked_up']:
            assignment.mark_in_transit()
            return Response({'message': 'Marked as in transit', 'status': assignment.status})
        return Response(
            {'error': f'Cannot mark in transit from status: {assignment.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def send_otp(self, request, pk=None):
        """
        Generate a 6-digit OTP and email it to the customer.
        The customer shares this OTP with the delivery agent to confirm receipt.
        """
        assignment = self.get_object()

        # Generate a 6-digit OTP
        otp = str(random.randint(100000, 999999))

        # Save OTP to the assignment model
        assignment.otp_code = otp
        assignment.save(update_fields=['otp_code'])

        # Get customer email from the linked order
        customer_email = None
        customer_name = 'Customer'
        order_number = 'N/A'
        try:
            order = assignment.order
            customer_email = order.user.email
            customer_name = order.user.get_full_name() or order.user.username
            order_number = getattr(order, 'order_number', str(order.id))
        except Exception as e:
            print(f"[DELIVERY OTP] Error getting customer info: {e}")

        if not customer_email:
            return Response(
                {'error': 'Could not find customer email for this order'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Always print OTP to terminal for testing/debugging
        otp_msg = (
            f"\n{'='*50}\n"
            f"[DELIVERY OTP]\n"
            f"Assignment ID : {assignment.id}\n"
            f"Assignment Status: {assignment.status}\n"
            f"Order         : {order_number}\n"
            f"Customer Email: {customer_email}\n"
            f"OTP CODE      : {otp}\n"
            f"{'='*50}\n"
        )
        sys.stdout.write(otp_msg)
        sys.stdout.flush()

        # Send OTP email to customer
        try:
            send_mail(
                subject='ShopSphere Delivery OTP - Confirm Your Delivery',
                message=(
                    f'Hello {customer_name},\n\n'
                    f'Your delivery agent is at your location for Order #{order_number}.\n\n'
                    f'Please share this OTP with the delivery agent to confirm receipt:\n\n'
                    f'  OTP: {otp}\n\n'
                    f'Do NOT share this OTP with anyone other than the delivery agent at your door.\n\n'
                    f'- ShopSphere Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer_email],
                fail_silently=False,
            )
            return Response({
                'success': True,
                'message': f'OTP sent to customer email ({customer_email})',
                'otp_for_testing': otp,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            error_msg = str(e)
            sys.stdout.write(f"[DELIVERY OTP] Email failed: {error_msg}\n")
            sys.stdout.flush()
            return Response({
                'success': True,
                'message': 'Email failed. You can still proceed.',
                'warning': error_msg,
                'otp_for_testing': otp,
            }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def verify_otp(self, request, pk=None):
        """
        Verify OTP submitted by the agent (given by the customer).
        If correct, marks the delivery as complete.
        """
        assignment = self.get_object()
        submitted_otp = str(request.data.get('otp', '')).strip()

        if not submitted_otp:
            return Response({'error': 'OTP is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not assignment.otp_code:
            return Response(
                {'error': 'No OTP generated for this delivery. Please use "Send OTP" first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if submitted_otp == str(assignment.otp_code):
            # Mark OTP as verified and clear it
            assignment.otp_verified = True
            assignment.otp_code = ''
            assignment.save(update_fields=['otp_verified', 'otp_code'])

            # Mark delivery as completed
            assignment.mark_delivered()

            return Response({
                'success': True,
                'message': 'OTP verified. Delivery marked as complete!',
                'status': assignment.status
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Invalid OTP. Please check and try again.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def deliver(self, request, pk=None):
        """Mark delivery as complete without OTP (backward compatibility)"""
        assignment = self.get_object()
        assignment.mark_delivered()
        return Response({'message': 'Order delivered successfully', 'status': assignment.status})

    @action(detail=True, methods=['post'])
    def failed(self, request, pk=None):
        """Mark delivery as failed"""
        assignment = self.get_object()
        assignment.mark_failed()
        return Response({'message': 'Delivery marked as failed', 'status': assignment.status})

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get delivery history for the current agent"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            history = DeliveryAssignment.objects.filter(
                agent=agent,
                status__in=['delivered', 'failed', 'cancelled']
            ).order_by('-completed_at')
            
            serializer = DeliveryAssignmentListSerializer(history, many=True)
            return Response(serializer.data)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=404)


class DeliveryTrackingViewSet(viewsets.ModelViewSet):
    """Manage delivery tracking"""
    permission_classes = [IsAuthenticated]
    pagination_class = None
    serializer_class = DeliveryTrackingSerializer

    def get_queryset(self):
        return DeliveryTracking.objects.filter(delivery_assignment__agent__user=self.request.user)


class DeliveryEarningsViewSet(viewsets.ReadOnlyModelViewSet):
    """View delivery earnings/commissions"""
    permission_classes = [IsAuthenticated]
    pagination_class = None
    serializer_class = DeliveryCommissionSerializer

    def get_queryset(self):
        return DeliveryCommission.objects.filter(agent__user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get earnings summary for a given time period"""
        try:
            from user.models import UserWallet
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            wallet, created = UserWallet.objects.get_or_create(user=request.user)
            filter_type = request.query_params.get('filter', 'monthly')
            today = timezone.now().date()
            
            queryset = DeliveryCommission.objects.filter(agent=agent, status__in=['approved', 'paid'])
            
            if filter_type == 'today':
                queryset = queryset.filter(created_at__date=today)
            elif filter_type == 'monthly':
                queryset = queryset.filter(created_at__month=today.month, created_at__year=today.year)
            elif filter_type == 'yearly':
                queryset = queryset.filter(created_at__year=today.year)
            
            summary_data = queryset.aggregate(
                sum_total=Sum('total_commission'),
                base_earnings=Sum('base_fee'),
                bonus_earnings=Sum('distance_bonus'),
                paid=Sum('total_commission', filter=models.Q(status='paid')),
                pending=Sum('total_commission', filter=models.Q(status='pending')),
                approved=Sum('total_commission', filter=models.Q(status='approved'))
            )
            
            # Fill Nones with 0
            for key in summary_data:
                if summary_data[key] is None:
                    summary_data[key] = "0.00"
                else:
                    summary_data[key] = str(summary_data[key])
            
            # Add actual wallet balance
            summary_data['total'] = str(wallet.balance)
            summary_data['available_balance'] = str(wallet.balance)
            
            return Response(summary_data)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=404)


class DeliveryPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """View delivery payments"""
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryPaymentSerializer

    def get_queryset(self):
        return DeliveryPayment.objects.filter(agent__user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        """Request a withdrawal from earnings"""
        try:
            from user.models import UserWallet
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            wallet, created = UserWallet.objects.get_or_create(user=request.user)
            
            amount = request.data.get('amount')
            if not amount:
                return Response({'error': 'Amount is required'}, status=400)
            
            try:
                amount = Decimal(str(amount))
            except:
                return Response({'error': 'Invalid amount format'}, status=400)
            
            if amount < 100:
                return Response({'error': 'Minimum withdrawal amount is ₹100'}, status=400)
            
            if wallet.balance < amount:
                return Response({'error': 'Insufficient balance'}, status=400)
            
            # Create a payment record
            payment = DeliveryPayment.objects.create(
                agent=agent,
                amount=amount,
                from_date=timezone.now().date(), # Simplified
                to_date=timezone.now().date(),
                status='pending',
                notes=f"Withdrawal request via {request.data.get('method', 'bank_transfer')}"
            )
            
            # Deduct from wallet
            wallet.deduct_balance(amount, f"Withdrawal request #{payment.id}")
            
            return Response({
                'success': True,
                'message': 'Withdrawal request submitted successfully',
                'amount': str(amount)
            })
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=404)


class DeliveryDailyStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """View delivery daily statistics"""
    permission_classes = [IsAuthenticated]
    pagination_class = None
    serializer_class = DeliveryDailyStatsSerializer

    def get_queryset(self):
        return DeliveryDailyStats.objects.filter(agent__user=self.request.user).order_by('-date')


class DeliveryFeedbackViewSet(viewsets.ReadOnlyModelViewSet):
    """View delivery feedback"""
    permission_classes = [IsAuthenticated]
    pagination_class = None
    serializer_class = DeliveryFeedbackSerializer

    def get_queryset(self):
        return DeliveryFeedback.objects.filter(agent__user=self.request.user).order_by('-created_at')


class DeliveryAgentDashboardView(generics.RetrieveAPIView):
    """Get comprehensive delivery agent dashboard"""
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAgentDashboardSerializer

    def get_object(self):
        return get_object_or_404(DeliveryAgentProfile, user=self.request.user)
