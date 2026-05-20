import pytest
from decimal import Decimal
from django.utils import timezone
from factories import LeadFactory, PipelineFactory, ActivityFactory, CustomerFactory
from apps.crm.models import Lead, Activity


@pytest.mark.django_db
class TestLeadModel:
    def test_weighted_revenue(self):
        lead = LeadFactory(expected_revenue=Decimal('10000'), probability=Decimal('30'))
        assert lead.weighted_revenue == Decimal('3000')

    def test_is_won_false_initially(self):
        lead = LeadFactory()
        assert lead.is_won is False
        assert lead.is_lost is False


@pytest.mark.django_db
class TestLeadAPI:
    def test_create_lead(self, auth_client):
        pipeline = PipelineFactory()
        response = auth_client.post('/api/v1/crm/leads/', {
            'name': 'Big Deal',
            'contact_name': 'Jane Smith',
            'contact_email': 'jane@example.com',
            'pipeline': str(pipeline.id),
            'priority': 'high',
            'expected_revenue': '10000.00',
            'probability': '60.00',
        })
        assert response.status_code == 201
        assert response.data['name'] == 'Big Deal'

    def test_list_leads(self, auth_client):
        LeadFactory.create_batch(4)
        response = auth_client.get('/api/v1/crm/leads/')
        assert response.status_code == 200
        assert len(response.data['results']) == 4

    def test_filter_leads_by_state_open(self, auth_client):
        open_lead = LeadFactory()
        won_lead = LeadFactory()
        won_lead.won_at = timezone.now()
        won_lead.save()
        response = auth_client.get('/api/v1/crm/leads/?state=open')
        assert response.status_code == 200
        ids = [l['id'] for l in response.data['results']]
        assert str(open_lead.id) in ids
        assert str(won_lead.id) not in ids


@pytest.mark.django_db
class TestLeadStateActions:
    def test_mark_lead_won(self, auth_client):
        lead = LeadFactory()
        response = auth_client.post(f'/api/v1/crm/leads/{lead.id}/won/')
        assert response.status_code == 200
        lead.refresh_from_db()
        assert lead.won_at is not None
        assert lead.probability == Decimal('100')

    def test_mark_lead_lost_with_reason(self, auth_client):
        lead = LeadFactory()
        response = auth_client.post(f'/api/v1/crm/leads/{lead.id}/lost/', {'reason': 'Too expensive'})
        assert response.status_code == 200
        lead.refresh_from_db()
        assert lead.lost_at is not None
        assert lead.lost_reason == 'Too expensive'
        assert lead.probability == Decimal('0')

    def test_cannot_mark_won_lead_as_lost(self, auth_client):
        from django.utils import timezone
        lead = LeadFactory(won_at=timezone.now())
        response = auth_client.post(f'/api/v1/crm/leads/{lead.id}/lost/')
        assert response.status_code == 400

    def test_move_lead_to_pipeline_stage(self, auth_client):
        lead = LeadFactory()
        new_stage = PipelineFactory(probability=Decimal('75'))
        response = auth_client.post(f'/api/v1/crm/leads/{lead.id}/move/', {
            'pipeline': str(new_stage.id),
        })
        assert response.status_code == 200
        lead.refresh_from_db()
        assert str(lead.pipeline_id) == str(new_stage.id)
        assert lead.probability == Decimal('75')

    def test_convert_won_lead_to_customer(self, auth_client):
        from django.utils import timezone
        lead = LeadFactory(
            won_at=timezone.now(),
            contact_email='convert@example.com',
            contact_name='Convert Me',
        )
        response = auth_client.post(f'/api/v1/crm/leads/{lead.id}/convert/')
        assert response.status_code == 201
        assert response.data['created'] is True
        lead.refresh_from_db()
        assert lead.customer is not None

    def test_cannot_convert_open_lead(self, auth_client):
        lead = LeadFactory()
        response = auth_client.post(f'/api/v1/crm/leads/{lead.id}/convert/')
        assert response.status_code == 400


@pytest.mark.django_db
class TestActivityAPI:
    def test_mark_activity_done(self, auth_client):
        activity = ActivityFactory()
        response = auth_client.post(f'/api/v1/crm/activities/{activity.id}/done/')
        assert response.status_code == 200
        activity.refresh_from_db()
        assert activity.is_done is True
        assert activity.done_at is not None

    def test_cannot_mark_done_twice(self, auth_client):
        from django.utils import timezone
        activity = ActivityFactory(is_done=True, done_at=timezone.now())
        response = auth_client.post(f'/api/v1/crm/activities/{activity.id}/done/')
        assert response.status_code == 400
