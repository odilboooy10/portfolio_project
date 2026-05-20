import pytest
from decimal import Decimal
from factories import AccountFactory, JournalFactory
from apps.accounting.models import JournalEntry


@pytest.mark.django_db
class TestAccountAPI:
    def test_create_account(self, auth_client):
        response = auth_client.post('/api/v1/accounting/accounts/', {
            'code': '1001',
            'name': 'Cash',
            'account_type': 'asset',
        })
        assert response.status_code == 201
        assert response.data['code'] == '1001'

    def test_list_accounts(self, auth_client):
        AccountFactory.create_batch(3)
        response = auth_client.get('/api/v1/accounting/accounts/')
        assert response.status_code == 200
        assert len(response.data['results']) == 3

    def test_filter_accounts_by_type(self, auth_client):
        AccountFactory(account_type='asset')
        AccountFactory(account_type='revenue')
        response = auth_client.get('/api/v1/accounting/accounts/?type=asset')
        assert response.status_code == 200
        assert all(a['account_type'] == 'asset' for a in response.data['results'])


@pytest.mark.django_db
class TestJournalEntryFlow:
    def _create_balanced_entry(self, auth_client):
        journal = JournalFactory()
        debit_account = AccountFactory(code='1100', account_type='asset')
        credit_account = AccountFactory(code='4000', account_type='revenue')
        response = auth_client.post('/api/v1/accounting/entries/', {
            'journal': str(journal.id),
            'date': '2026-05-20',
            'note': 'Test entry',
            'lines': [
                {'account': str(debit_account.id), 'debit': '500.00', 'credit': '0.00'},
                {'account': str(credit_account.id), 'debit': '0.00', 'credit': '500.00'},
            ],
        }, format='json')
        assert response.status_code == 201
        return response.data['id']

    def test_create_balanced_entry(self, auth_client):
        entry_id = self._create_balanced_entry(auth_client)
        entry = JournalEntry.objects.get(id=entry_id)
        assert entry.is_balanced is True
        assert entry.status == 'draft'
        assert entry.reference.startswith('JE-')

    def test_unbalanced_entry_is_rejected(self, auth_client):
        journal = JournalFactory()
        debit_account = AccountFactory(code='1200', account_type='asset')
        credit_account = AccountFactory(code='4100', account_type='revenue')
        response = auth_client.post('/api/v1/accounting/entries/', {
            'journal': str(journal.id),
            'date': '2026-05-20',
            'lines': [
                {'account': str(debit_account.id), 'debit': '500.00', 'credit': '0.00'},
                {'account': str(credit_account.id), 'debit': '0.00', 'credit': '300.00'},
            ],
        }, format='json')
        assert response.status_code == 400

    def test_post_entry(self, auth_client):
        entry_id = self._create_balanced_entry(auth_client)
        response = auth_client.post(f'/api/v1/accounting/entries/{entry_id}/post_entry/')
        assert response.status_code == 200
        assert response.data['status'] == 'posted'

    def test_posted_entry_cannot_be_edited(self, auth_client):
        entry_id = self._create_balanced_entry(auth_client)
        auth_client.post(f'/api/v1/accounting/entries/{entry_id}/post_entry/')
        journal = JournalFactory()
        response = auth_client.patch(f'/api/v1/accounting/entries/{entry_id}/', {
            'note': 'trying to edit',
        }, format='json')
        entry = JournalEntry.objects.get(id=entry_id)
        assert entry.note != 'trying to edit'

    def test_reverse_posted_entry(self, auth_client):
        entry_id = self._create_balanced_entry(auth_client)
        auth_client.post(f'/api/v1/accounting/entries/{entry_id}/post_entry/')
        response = auth_client.post(f'/api/v1/accounting/entries/{entry_id}/reverse/', {
            'date': '2026-05-20',
        })
        assert response.status_code == 201
        reversal = JournalEntry.objects.get(id=response.data['id'])
        original = JournalEntry.objects.get(id=entry_id)
        for orig_line in original.lines.all():
            rev_line = reversal.lines.get(account=orig_line.account)
            assert orig_line.debit == rev_line.credit
            assert orig_line.credit == rev_line.debit

    def test_cancel_draft_entry(self, auth_client):
        entry_id = self._create_balanced_entry(auth_client)
        response = auth_client.post(f'/api/v1/accounting/entries/{entry_id}/cancel/')
        assert response.status_code == 200
        assert response.data['status'] == 'cancelled'

    def test_cannot_cancel_posted_entry(self, auth_client):
        entry_id = self._create_balanced_entry(auth_client)
        auth_client.post(f'/api/v1/accounting/entries/{entry_id}/post_entry/')
        response = auth_client.post(f'/api/v1/accounting/entries/{entry_id}/cancel/')
        assert response.status_code == 400


@pytest.mark.django_db
class TestPaymentAPI:
    def test_create_payment(self, auth_client):
        journal = JournalFactory(journal_type='bank')
        response = auth_client.post('/api/v1/accounting/payments/', {
            'payment_type': 'inbound',
            'payment_method': 'bank',
            'amount': '1500.00',
            'date': '2026-05-20',
            'journal': str(journal.id),
        })
        assert response.status_code == 201
        assert response.data['reference'].startswith('PAY-')
        assert response.data['amount'] == '1500.00'
