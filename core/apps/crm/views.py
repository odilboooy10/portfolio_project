from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Pipeline, Lead, Activity
from .serializers import (
    PipelineSerializer,
    LeadListSerializer, LeadDetailSerializer,
    ActivitySerializer,
)


class IsManagerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_manager


class PipelineViewSet(viewsets.ModelViewSet):
    queryset = Pipeline.objects.prefetch_related('leads')
    serializer_class = PipelineSerializer
    permission_classes = [IsManagerOrReadOnly]


class LeadViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'contact_name', 'company', 'contact_email']
    ordering_fields = ['created_at', 'expected_revenue', 'probability', 'expected_close_date']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Lead.objects.select_related(
            'pipeline', 'assigned_to', 'customer', 'created_by'
        ).prefetch_related('activities')

        pipeline_id = self.request.query_params.get('pipeline')
        assigned_to = self.request.query_params.get('assigned_to')
        priority = self.request.query_params.get('priority')
        state = self.request.query_params.get('state')  # open | won | lost

        if pipeline_id:
            qs = qs.filter(pipeline_id=pipeline_id)
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)
        if priority:
            qs = qs.filter(priority=priority)
        if state == 'won':
            qs = qs.filter(won_at__isnull=False)
        elif state == 'lost':
            qs = qs.filter(lost_at__isnull=False)
        elif state == 'open':
            qs = qs.filter(won_at__isnull=True, lost_at__isnull=True)

        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return LeadListSerializer
        return LeadDetailSerializer

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Move lead to a different pipeline stage."""
        lead = self.get_object()
        pipeline_id = request.data.get('pipeline')
        if not pipeline_id:
            return Response({'detail': 'pipeline is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pipeline = Pipeline.objects.get(pk=pipeline_id)
        except Pipeline.DoesNotExist:
            return Response({'detail': 'Pipeline stage not found.'}, status=status.HTTP_404_NOT_FOUND)

        lead.pipeline = pipeline
        # Auto-set probability from pipeline default if not overridden
        lead.probability = pipeline.probability
        lead.save()
        return Response(LeadDetailSerializer(lead, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def won(self, request, pk=None):
        """Mark lead as won and optionally convert to a Sales customer."""
        lead = self.get_object()
        if lead.is_won:
            return Response({'detail': 'Lead is already won.'}, status=status.HTTP_400_BAD_REQUEST)
        if lead.is_lost:
            return Response({'detail': 'Cannot mark a lost lead as won.'}, status=status.HTTP_400_BAD_REQUEST)

        # Move to the won pipeline stage if one exists
        won_stage = Pipeline.objects.filter(is_won=True).first()
        if won_stage:
            lead.pipeline = won_stage

        lead.won_at = timezone.now()
        lead.probability = 100
        lead.save()

        return Response(LeadDetailSerializer(lead, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def lost(self, request, pk=None):
        """Mark lead as lost with an optional reason."""
        lead = self.get_object()
        if lead.is_lost:
            return Response({'detail': 'Lead is already lost.'}, status=status.HTTP_400_BAD_REQUEST)
        if lead.is_won:
            return Response({'detail': 'Cannot mark a won lead as lost.'}, status=status.HTTP_400_BAD_REQUEST)

        lost_stage = Pipeline.objects.filter(is_lost=True).first()
        if lost_stage:
            lead.pipeline = lost_stage

        lead.lost_at = timezone.now()
        lead.lost_reason = request.data.get('reason', '')
        lead.probability = 0
        lead.save()

        return Response(LeadDetailSerializer(lead, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        """Convert a won lead into a Sales Customer."""
        from apps.sales.models import Customer

        lead = self.get_object()
        if not lead.is_won:
            return Response(
                {'detail': 'Only won leads can be converted to customers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if lead.customer:
            return Response(
                {'detail': 'Lead is already linked to a customer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer, created = Customer.objects.get_or_create(
            email=lead.contact_email or f"lead-{lead.id}@placeholder.local",
            defaults={
                'name': lead.contact_name or lead.company or lead.name,
                'phone': lead.contact_phone,
                'company': lead.company,
            },
        )
        lead.customer = customer
        lead.save()

        return Response({
            'customer_id': str(customer.id),
            'customer_name': customer.name,
            'created': created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ActivityViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Activity.objects.select_related('lead', 'assigned_to', 'created_by')
        lead_id = self.request.query_params.get('lead')
        activity_type = self.request.query_params.get('type')
        is_done = self.request.query_params.get('done')
        assigned_to = self.request.query_params.get('assigned_to')

        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        if activity_type:
            qs = qs.filter(activity_type=activity_type)
        if is_done is not None:
            qs = qs.filter(is_done=is_done.lower() == 'true')
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)
        return qs

    def get_serializer_class(self):
        return ActivitySerializer

    @action(detail=True, methods=['post'])
    def done(self, request, pk=None):
        """Mark an activity as done."""
        activity = self.get_object()
        if activity.is_done:
            return Response({'detail': 'Activity is already done.'}, status=status.HTTP_400_BAD_REQUEST)
        activity.is_done = True
        activity.done_at = timezone.now()
        activity.save()
        return Response(ActivitySerializer(activity, context={'request': request}).data)
