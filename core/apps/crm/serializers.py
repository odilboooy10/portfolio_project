from rest_framework import serializers
from .models import Pipeline, Lead, Activity

_MONEY = dict(max_digits=12, decimal_places=2, read_only=True)


class PipelineSerializer(serializers.ModelSerializer):
    lead_count = serializers.SerializerMethodField()

    class Meta:
        model = Pipeline
        fields = ('id', 'name', 'order', 'probability', 'is_won', 'is_lost', 'lead_count')
        read_only_fields = ('id',)

    def get_lead_count(self, obj) -> int:
        return obj.leads.count()


class ActivitySerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True, allow_null=True, default=None)

    class Meta:
        model = Activity
        fields = (
            'id', 'lead', 'activity_type', 'title', 'note',
            'due_date', 'is_done', 'done_at',
            'assigned_to', 'assigned_to_name',
            'created_by', 'created_at',
        )
        read_only_fields = ('id', 'done_at', 'created_at')


class LeadListSerializer(serializers.ModelSerializer):
    pipeline_name = serializers.ReadOnlyField(source='pipeline.name')
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True, allow_null=True, default=None)
    weighted_revenue = serializers.DecimalField(**_MONEY)
    is_won = serializers.BooleanField(read_only=True)
    is_lost = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lead
        fields = (
            'id', 'name', 'contact_name', 'company', 'pipeline', 'pipeline_name',
            'priority', 'expected_revenue', 'probability', 'weighted_revenue',
            'assigned_to', 'assigned_to_name', 'expected_close_date',
            'is_won', 'is_lost', 'created_at',
        )
        read_only_fields = ('id', 'created_at')


class LeadDetailSerializer(serializers.ModelSerializer):
    pipeline_name = serializers.ReadOnlyField(source='pipeline.name')
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True, allow_null=True, default=None)
    customer_name = serializers.ReadOnlyField(source='customer.name')
    activities = ActivitySerializer(many=True, read_only=True)
    weighted_revenue = serializers.DecimalField(**_MONEY)
    is_won = serializers.BooleanField(read_only=True)
    is_lost = serializers.BooleanField(read_only=True)
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Lead
        fields = (
            'id', 'name', 'contact_name', 'contact_email', 'contact_phone', 'company',
            'pipeline', 'pipeline_name', 'priority',
            'expected_revenue', 'probability', 'weighted_revenue',
            'assigned_to', 'assigned_to_name',
            'customer', 'customer_name',
            'description', 'expected_close_date',
            'is_won', 'is_lost', 'won_at', 'lost_at', 'lost_reason',
            'activities', 'created_by', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'won_at', 'lost_at', 'created_at', 'updated_at')
