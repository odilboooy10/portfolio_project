from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.crm.models import Lead, Pipeline


class LeadListView(LoginRequiredMixin, ListView):
    model = Lead
    template_name = 'crm/lead_list.html'
    context_object_name = 'leads'
    paginate_by = 25

    def get_queryset(self):
        qs = Lead.objects.select_related('pipeline', 'assigned_to', 'customer')
        q = self.request.GET.get('q', '').strip()
        pipeline_id = self.request.GET.get('pipeline')
        priority = self.request.GET.get('priority')
        state = self.request.GET.get('state')

        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(company__icontains=q) | qs.filter(contact_name__icontains=q)
        if pipeline_id:
            qs = qs.filter(pipeline_id=pipeline_id)
        if priority:
            qs = qs.filter(priority=priority)
        if state == 'won':
            qs = qs.exclude(won_at=None)
        elif state == 'lost':
            qs = qs.exclude(lost_at=None)
        elif state == 'active':
            qs = qs.filter(won_at=None, lost_at=None)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pipelines'] = Pipeline.objects.all()
        ctx['priorities'] = Lead.Priority.choices
        ctx['q'] = self.request.GET.get('q', '')
        ctx['current_pipeline'] = self.request.GET.get('pipeline', '')
        ctx['current_priority'] = self.request.GET.get('priority', '')
        ctx['current_state'] = self.request.GET.get('state', '')
        return ctx


class KanbanView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/kanban.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pipelines = Pipeline.objects.prefetch_related(
            'leads__assigned_to'
        ).all()
        ctx['pipelines'] = pipelines
        ctx['total_leads'] = Lead.objects.count()
        return ctx


class LeadDetailView(LoginRequiredMixin, DetailView):
    model = Lead
    template_name = 'crm/lead_detail.html'
    context_object_name = 'lead'

    def get_queryset(self):
        return Lead.objects.select_related(
            'pipeline', 'assigned_to', 'customer', 'created_by'
        ).prefetch_related('activities__assigned_to', 'activities__created_by')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pipelines'] = Pipeline.objects.all()
        ctx['activity_types'] = [
            ('call', 'Phone Call', 'bi-telephone'),
            ('email', 'Email', 'bi-envelope'),
            ('meeting', 'Meeting', 'bi-calendar-event'),
            ('task', 'Task', 'bi-check2-square'),
            ('note', 'Note', 'bi-sticky'),
            ('demo', 'Demo', 'bi-display'),
        ]
        return ctx


class LeadWinView(LoginRequiredMixin, View):
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        if not lead.is_won and not lead.is_lost:
            lead.won_at = timezone.now()
            lead.lost_at = None
            lead.lost_reason = ''
            lead.save(update_fields=['won_at', 'lost_at', 'lost_reason'])
            messages.success(request, f'"{lead.name}" marked as Won.')
        return redirect('crm:lead-detail', pk=pk)


class LeadLoseView(LoginRequiredMixin, View):
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        if not lead.is_won and not lead.is_lost:
            lead.lost_at = timezone.now()
            lead.lost_reason = request.POST.get('reason', '')
            lead.won_at = None
            lead.save(update_fields=['lost_at', 'lost_reason', 'won_at'])
            messages.warning(request, f'"{lead.name}" marked as Lost.')
        return redirect('crm:lead-detail', pk=pk)


class LeadMoveStageView(LoginRequiredMixin, View):
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        pipeline_id = request.POST.get('pipeline_id')
        if pipeline_id:
            pipeline = get_object_or_404(Pipeline, pk=pipeline_id)
            lead.pipeline = pipeline
            lead.save(update_fields=['pipeline'])
        return redirect('crm:lead-detail', pk=pk)
