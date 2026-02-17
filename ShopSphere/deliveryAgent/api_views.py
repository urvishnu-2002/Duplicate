from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    DeliveryAgentProfile, DeliveryAssignment, DeliveryTracking,
    DeliveryCommission, DeliveryPayment, DeliveryDailyStats, DeliveryFeedback
)
from .serializers import (
    DeliveryAgentProfileListSerializer, DeliveryAgentProfileDetailSerializer,
    DeliveryAgentProfileCreateSerializer, DeliveryAgentDashboardSerializer,
    DeliveryAssignmentListSerializer, DeliveryAssignmentDetailSerializer,
    DeliveryAssignmentCreateSerializer, DeliveryTrackingSerializer,
    DeliveryCommissionSerializer, DeliveryPaymentSerializer,
    DeliveryDailyStatsSerializer, DeliveryFeedbackSerializer
)
from user.models import Order

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ===============================================
#     DELIVERY AGENT PROFILE VIEWSET
# ===============================================

class DeliveryAgentProfileViewSet(viewsets.ViewSet):
    """Delivery agent profile management"""
    permission_classes = [IsAuthenticated]
    
    def get_agent(self, request):
        """Get current delivery agent profile"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            serializer = DeliveryAgentProfileDetailSerializer(agent)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Delivery agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def update_profile(self, request):
        """Update agent profile"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            
            allowed_fields = ['phone_number', 'address', 'city', 'state', 'postal_code',
                            'vehicle_type', 'vehicle_number', 'service_cities',
                            'preferred_delivery_radius', 'working_hours_start',
                            'working_hours_end']
            
            for field in allowed_fields:
                if field in request.data:
                    setattr(agent, field, request.data[field])
            
            agent.save()
            serializer = DeliveryAgentProfileDetailSerializer(agent)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def update_availability(self, request):
        """Update agent availability status"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            status_choice = request.data.get('status')
            
            if status_choice not in dict(DeliveryAgentProfile.AVAILABILITY_CHOICES):
                return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
            
            agent.availability_status = status_choice
            agent.last_online = timezone.now()
            agent.save()
            
            return Response({
                'message': 'Status updated',
                'status': agent.availability_status
            }, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#    DELIVERY ASSIGNMENT VIEWSET
# ===============================================

class DeliveryAssignmentViewSet(viewsets.ViewSet):
    """Delivery assignment management for agents"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def list(self, request):
        """Get all assigned deliveries for agent"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            
            status_filter = request.query_params.get('status')
            queryset = DeliveryAssignment.objects.filter(agent=agent).order_by('-assigned_at')
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            serializer = DeliveryAssignmentListSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, pk=None):
        """Get detailed delivery assignment"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            assignment = DeliveryAssignment.objects.get(id=pk, agent=agent)
            serializer = DeliveryAssignmentDetailSerializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except DeliveryAssignment.DoesNotExist:
            return Response({'error': 'Delivery assignment not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a delivery assignment"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            assignment = DeliveryAssignment.objects.get(id=pk, agent=agent)
            
            if assignment.status != 'assigned':
                return Response({'error': 'Only assigned deliveries can be accepted'}, status=status.HTTP_400_BAD_REQUEST)
            
            assignment.accept_delivery()
            serializer = DeliveryAssignmentDetailSerializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (DeliveryAgentProfile.DoesNotExist, DeliveryAssignment.DoesNotExist):
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start delivery (picked up from vendor)"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            assignment = DeliveryAssignment.objects.get(id=pk, agent=agent)
            
            if assignment.status != 'accepted':
                return Response({'error': 'Delivery must be accepted first'}, status=status.HTTP_400_BAD_REQUEST)
            
            assignment.start_delivery()
            serializer = DeliveryAssignmentDetailSerializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (DeliveryAgentProfile.DoesNotExist, DeliveryAssignment.DoesNotExist):
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def in_transit(self, request, pk=None):
        """Mark delivery as in transit"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            assignment = DeliveryAssignment.objects.get(id=pk, agent=agent)
            
            assignment.mark_in_transit()
            serializer = DeliveryAssignmentDetailSerializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (DeliveryAgentProfile.DoesNotExist, DeliveryAssignment.DoesNotExist):
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark delivery as completed"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            assignment = DeliveryAssignment.objects.get(id=pk, agent=agent)
            
            # Handle proof of delivery
            if 'signature_image' in request.FILES:
                assignment.signature_image = request.FILES['signature_image']
            if 'delivery_photo' in request.FILES:
                assignment.delivery_photo = request.FILES['delivery_photo']
            if 'otp_code' in request.data:
                assignment.otp_code = request.data['otp_code']
                assignment.otp_verified = True
            
            assignment.mark_delivered()
            
            agent.total_deliveries += 1
            agent.completed_deliveries += 1
            agent.save()
            
            serializer = DeliveryAssignmentDetailSerializer(assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (DeliveryAgentProfile.DoesNotExist, DeliveryAssignment.DoesNotExist):
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def failed(self, request, pk=None):
        """Mark delivery as failed"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            assignment = DeliveryAssignment.objects.get(id=pk, agent=agent)
            
            assignment.mark_failed()
            
            return Response({
                'message': 'Delivery marked as failed',
                'status': assignment.status,
                'attempts': assignment.attempts_count
            }, status=status.HTTP_200_OK)
        except (DeliveryAgentProfile.DoesNotExist, DeliveryAssignment.DoesNotExist):
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get currently active deliveries"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            active = DeliveryAssignment.objects.filter(
                agent=agent,
                status__in=['assigned', 'accepted', 'picked_up', 'in_transit']
            ).order_by('-assigned_at')
            
            serializer = DeliveryAssignmentListSerializer(active, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#      DELIVERY TRACKING VIEWSET
# ===============================================

class DeliveryTrackingViewSet(viewsets.ViewSet):
    """Real-time delivery tracking"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def update_location(self, request, pk=None):
        """Update current delivery location (real-time tracking)"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            assignment = DeliveryAssignment.objects.get(id=pk, agent=agent)
            
            # Create tracking record
            tracking = DeliveryTracking.objects.create(
                delivery_assignment=assignment,
                latitude=request.data.get('latitude'),
                longitude=request.data.get('longitude'),
                address=request.data.get('address', ''),
                status=request.data.get('status', 'In Transit'),
                speed=request.data.get('speed', None),
                notes=request.data.get('notes', '')
            )
            
            # Update assignment current location
            assignment.current_location = {
                'latitude': float(request.data.get('latitude', 0)),
                'longitude': float(request.data.get('longitude', 0)),
                'address': request.data.get('address', '')
            }
            assignment.save()
            
            serializer = DeliveryTrackingSerializer(tracking)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except (DeliveryAgentProfile.DoesNotExist, DeliveryAssignment.DoesNotExist):
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def get_tracking_history(self, request, pk=None):
        """Get tracking history for a delivery"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            assignment = DeliveryAssignment.objects.get(id=pk, agent=agent)
            
            tracking = DeliveryTracking.objects.filter(
                delivery_assignment=assignment
            ).order_by('-tracked_at')
            
            serializer = DeliveryTrackingSerializer(tracking, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (DeliveryAgentProfile.DoesNotExist, DeliveryAssignment.DoesNotExist):
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#    DELIVERY COMMISSION & EARNINGS VIEWSET
# ===============================================

class DeliveryEarningsViewSet(viewsets.ViewSet):
    """Commission and earnings tracking"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get all commissions/earnings"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            
            status_filter = request.query_params.get('status')
            queryset = DeliveryCommission.objects.filter(agent=agent).order_by('-created_at')
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            serializer = DeliveryCommissionSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get earnings summary"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            
            total_pending = DeliveryCommission.objects.filter(
                agent=agent, status='pending'
            ).aggregate(Sum('total_commission'))['total_commission__sum'] or Decimal('0.00')
            
            total_approved = DeliveryCommission.objects.filter(
                agent=agent, status='approved'
            ).aggregate(Sum('total_commission'))['total_commission__sum'] or Decimal('0.00')
            
            total_paid = DeliveryCommission.objects.filter(
                agent=agent, status='paid'
            ).aggregate(Sum('total_commission'))['total_commission__sum'] or Decimal('0.00')
            
            return Response({
                'pending': str(total_pending),
                'approved': str(total_approved),
                'paid': str(total_paid),
                'total': str(total_pending + total_approved + total_paid),
            }, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#      DELIVERY PAYMENT VIEWSET
# ===============================================

class DeliveryPaymentViewSet(viewsets.ViewSet):
    """Payment/payout management"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get all payment records"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            queryset = DeliveryPayment.objects.filter(agent=agent).order_by('-created_at')
            
            serializer = DeliveryPaymentSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending payout amount"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            pending_amount = DeliveryPayment.objects.filter(
                agent=agent,
                status__in=['pending', 'processing']
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            
            return Response({'pending_amount': str(pending_amount)}, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#     DELIVERY DAILY STATS VIEWSET
# ===============================================

class DeliveryDailyStatsViewSet(viewsets.ViewSet):
    """Daily statistics and performance tracking"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get daily stats for last 30 days"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            days = int(request.query_params.get('days', 30))
            
            stats = DeliveryDailyStats.objects.filter(
                agent=agent,
                date__gte=timezone.now().date() - timedelta(days=days)
            ).order_by('-date')
            
            serializer = DeliveryDailyStatsSerializer(stats, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's statistics"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            today = timezone.now().date()
            
            stats, created = DeliveryDailyStats.objects.get_or_create(
                agent=agent,
                date=today
            )
            
            serializer = DeliveryDailyStatsSerializer(stats)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#       DELIVERY FEEDBACK VIEWSET
# ===============================================

class DeliveryFeedbackViewSet(viewsets.ViewSet):
    """Customer feedback and ratings"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get all feedback for agent"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            feedback = DeliveryFeedback.objects.filter(agent=agent).order_by('-created_at')
            
            serializer = DeliveryFeedbackSerializer(feedback, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def rating_summary(self, request):
        """Get rating summary"""
        try:
            agent = DeliveryAgentProfile.objects.get(user=request.user)
            feedback = DeliveryFeedback.objects.filter(agent=agent)
            
            avg_rating = feedback.aggregate(Avg('overall_rating'))['overall_rating__avg'] or 0
            total_feedback = feedback.count()
            complaint_count = feedback.filter(is_complaint=True).count()
            
            return Response({
                'average_rating': float(avg_rating),
                'total_feedback': total_feedback,
                'complaint_count': complaint_count,
                'satisfaction_rate': float((total_feedback - complaint_count) / total_feedback * 100) if total_feedback > 0 else 0
            }, status=status.HTTP_200_OK)
        except DeliveryAgentProfile.DoesNotExist:
            return Response({'error': 'Agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===============================================
#     DELIVERY AGENT DASHBOARD VIEW
# ===============================================

class DeliveryAgentDashboardView(generics.RetrieveAPIView):
    """Comprehensive delivery agent dashboard"""
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAgentDashboardSerializer
    
    def get_object(self):
        try:
            return DeliveryAgentProfile.objects.get(user=self.request.user)
        except DeliveryAgentProfile.DoesNotExist:
            raise Response({'error': 'Delivery agent profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def retrieve(self, request, *args, **kwargs):
        try:
            agent = self.get_object()
            
            if agent.approval_status != 'approved':
                return Response({
                    'error': 'Agent account not approved',
                    'status': agent.approval_status
                }, status=status.HTTP_403_FORBIDDEN)
            
            if agent.is_blocked:
                return Response({
                    'error': 'Agent account is blocked',
                    'reason': agent.blocked_reason
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = self.get_serializer(agent)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)