from django.contrib import admin
from .models import Pipeline, Lead, Activity


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'probability', 'is_won', 'is_lost')
    ordering = ('order',)


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fields = ('activity_type', 'title', 'due_date', 'is_done', 'assigned_to')
    readonly_fields = ('id',)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'contact_name', 'company', 'pipeline',
        'priority', 'expected_revenue', 'probability',
        'assigned_to', 'is_won', 'is_lost', 'created_at',
    )
    list_filter = ('pipeline', 'priority', 'assigned_to')
    search_fields = ('name', 'contact_name', 'company', 'contact_email')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'won_at', 'lost_at', 'created_at', 'updated_at', 'created_by')
    inlines = [ActivityInline]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'activity_type', 'lead', 'assigned_to', 'due_date', 'is_done', 'created_at')
    list_filter = ('activity_type', 'is_done')
    search_fields = ('title', 'lead__name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'done_at', 'created_at', 'created_by')
