# billing/serializers_timeline.py（または serializers.py の末尾に追記）
from rest_framework import serializers
from .models import BillCustomer, BillCustomerNomination, Bill, Customer, Cast


class BillCustomerSerializer(serializers.ModelSerializer):
    """顧客滞在情報（arrived_at / left_at）"""
    
    class Meta:
        model = BillCustomer
        fields = ['id', 'bill', 'customer', 'arrived_at', 'left_at']
        read_only_fields = ['id']

    def validate(self, attrs):
        """
        バリデーション：
        1. arrived_at と left_at が両方入る場合、left_at >= arrived_at を強制
        2. left_at だけ先に入れるのは禁止
        """
        arrived_at = attrs.get('arrived_at')
        left_at = attrs.get('left_at')
        
        # left_at だけが入ってきた場合（updateの場合も含む）
        if left_at is not None and arrived_at is None:
            # updateで既存のarrived_atを確認
            if self.instance:
                arrived_at = self.instance.arrived_at
            
            # それでもarrived_atがないなら400
            if arrived_at is None:
                raise serializers.ValidationError(
                    {'left_at': 'left_at を設定するには arrived_at が必須です。'}
                )
        
        # 両方入っている場合のチェック
        if arrived_at is not None and left_at is not None:
            if left_at < arrived_at:
                raise serializers.ValidationError(
                    {'left_at': 'left_at は arrived_at 以降である必要があります。'}
                )
        
        return attrs


class BillCustomerNominationSerializer(serializers.ModelSerializer):
    """本指名紐づけ（bill × customer × cast）"""
    
    class Meta:
        model = BillCustomerNomination
        fields = ['id', 'bill', 'customer', 'cast', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        """
        バリデーション：
        1. BillCustomer(bill, customer) が存在するか確認
        2. Cast と Bill.table.store が同じか確認（storeロック）
        3. unique constraint は Django側が処理（IntegrityError）
        """
        bill = attrs.get('bill')
        customer = attrs.get('customer')
        cast = attrs.get('cast')
        
        # BillCustomerが存在するか確認
        if bill and customer:
            if not BillCustomer.objects.filter(bill=bill, customer=customer).exists():
                raise serializers.ValidationError(
                    {'customer': 'この顧客はこのbillに参加していません。'}
                )
        
        # Cast と Bill.table.store が同じか確認
        if bill and cast:
            bill_store = bill.table.store if bill.table else None
            cast_store = cast.store
            
            if bill_store and cast_store != bill_store:
                raise serializers.ValidationError(
                    {'cast': '異なる店舗のキャストは指定できません。'}
                )
        
        return attrs
