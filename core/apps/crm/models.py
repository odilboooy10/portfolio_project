import uuid
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Pipeline(models.Model):
    """Kanban stage in the sales pipeline."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    probability = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Default win probability (%) for leads in this stage.',
    )
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Lead(models.Model):
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='Lead or opportunity title.')
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=255, blank=True)

    pipeline = models.ForeignKey(
        Pipeline, null=True, blank=True, on_delete=models.SET_NULL, related_name='leads'
    )
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    expected_revenue = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    probability = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    assigned_to = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_leads'
    )
    customer = models.ForeignKey(
        'sales.Customer', null=True, blank=True, on_delete=models.SET_NULL, related_name='leads'
    )

    description = models.TextField(blank=True)
    expected_close_date = models.DateField(null=True, blank=True)

    won_at = models.DateTimeField(null=True, blank=True)
    lost_at = models.DateTimeField(null=True, blank=True)
    lost_reason = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_leads'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.contact_name or self.company or 'No contact'})"

    @property
    def is_won(self):
        return self.won_at is not None

    @property
    def is_lost(self):
        return self.lost_at is not None

    @property
    def weighted_revenue(self):
        return self.expected_revenue * (self.probability / 100)


class Activity(models.Model):
    class ActivityType(models.TextChoices):
        CALL = 'call', 'Phone Call'
        EMAIL = 'email', 'Email'
        MEETING = 'meeting', 'Meeting'
        TASK = 'task', 'Task'
        NOTE = 'note', 'Note'
        DEMO = 'demo', 'Demo'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    title = models.CharField(max_length=255)
    note = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    is_done = models.BooleanField(default=False)
    done_at = models.DateTimeField(null=True, blank=True)

    assigned_to = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='crm_activities'
    )
    created_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_activities'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.activity_type}] {self.title} — {self.lead}"
