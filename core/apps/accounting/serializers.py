from rest_framework import serializers
from .models import Account, Journal, JournalEntry, JournalEntryLine, Payment


class AccountSerializer(serializers.ModelSerializer):
    account_type_display = serializers.ReadOnlyField(source='get_account_type_display')
    parent_name = serializers.ReadOnlyField(source='parent.name')

    class Meta:
        model = Account
        fields = (
            'id', 'code', 'name', 'account_type', 'account_type_display',
            'parent', 'parent_name', 'description', 'is_active', 'created_at',
        )
        read_only_fields = ('id', 'created_at')


class JournalSerializer(serializers.ModelSerializer):
    journal_type_display = serializers.ReadOnlyField(source='get_journal_type_display')
    default_account_name = serializers.ReadOnlyField(source='default_account.name')

    class Meta:
        model = Journal
        fields = (
            'id', 'name', 'code', 'journal_type', 'journal_type_display',
            'default_account', 'default_account_name', 'is_active',
        )
        read_only_fields = ('id',)


class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_name = serializers.ReadOnlyField(source='account.name')
    account_code = serializers.ReadOnlyField(source='account.code')

    class Meta:
        model = JournalEntryLine
        fields = ('id', 'account', 'account_code', 'account_name', 'description', 'debit', 'credit')
        read_only_fields = ('id',)


class JournalEntryListSerializer(serializers.ModelSerializer):
    journal_name = serializers.ReadOnlyField(source='journal.name')
    total_debit = serializers.ReadOnlyField()
    is_balanced = serializers.ReadOnlyField()

    class Meta:
        model = JournalEntry
        fields = (
            'id', 'reference', 'journal', 'journal_name',
            'status', 'date', 'total_debit', 'is_balanced', 'created_at',
        )
        read_only_fields = ('id', 'reference', 'created_at')


class JournalEntryDetailSerializer(serializers.ModelSerializer):
    journal_name = serializers.ReadOnlyField(source='journal.name')
    lines = JournalEntryLineSerializer(many=True)
    total_debit = serializers.ReadOnlyField()
    total_credit = serializers.ReadOnlyField()
    is_balanced = serializers.ReadOnlyField()
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = JournalEntry
        fields = (
            'id', 'reference', 'journal', 'journal_name', 'status', 'date', 'note',
            'invoice', 'purchase_order',
            'lines', 'total_debit', 'total_credit', 'is_balanced',
            'created_by', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'reference', 'status', 'created_at', 'updated_at')

    def validate(self, data):
        lines = data.get('lines', [])
        if not lines:
            raise serializers.ValidationError({'lines': 'At least one line is required.'})
        total_debit = sum(line.get('debit', 0) for line in lines)
        total_credit = sum(line.get('credit', 0) for line in lines)
        if total_debit != total_credit:
            raise serializers.ValidationError(
                {'lines': f'Entry must balance. Debit {total_debit} ≠ Credit {total_credit}.'}
            )
        return data

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        entry = JournalEntry.objects.create(**validated_data)
        for line in lines_data:
            JournalEntryLine.objects.create(entry=entry, **line)
        return entry

    def update(self, instance, validated_data):
        if instance.status == JournalEntry.Status.POSTED:
            raise serializers.ValidationError('Posted entries cannot be edited.')
        lines_data = validated_data.pop('lines', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line in lines_data:
                JournalEntryLine.objects.create(entry=instance, **line)
        return instance


class PaymentSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    journal_name = serializers.ReadOnlyField(source='journal.name')
    invoice_reference = serializers.ReadOnlyField(source='invoice.reference')
    purchase_order_reference = serializers.ReadOnlyField(source='purchase_order.reference')

    class Meta:
        model = Payment
        fields = (
            'id', 'reference', 'payment_type', 'payment_method', 'amount', 'date',
            'journal', 'journal_name',
            'invoice', 'invoice_reference',
            'purchase_order', 'purchase_order_reference',
            'note', 'created_by', 'created_at',
        )
        read_only_fields = ('id', 'reference', 'created_at')
