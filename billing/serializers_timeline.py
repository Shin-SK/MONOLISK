# billing/serializers_timeline.py（または serializers.py の末尾に追記）
from rest_framework import serializers
from django.utils import timezone
from .models import BillCustomer, BillCustomerNomination, Bill, Customer, Cast


class BillCustomerSerializer(serializers.ModelSerializer):
    """顧客滞在情報（arrived_at / left_at）"""
    
    # 追加フィールド：customer_id, customer_name, display_name
    customer_id = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BillCustomer
        fields = ['id', 'bill', 'customer', 'customer_id', 'customer_name', 'display_name', 'arrived_at', 'left_at']
        read_only_fields = ['id', 'customer_id', 'customer_name', 'display_name']

    def get_customer_id(self, obj):
        """customer_id を安全に取得（FK の *_id は None-safe）"""
        return obj.customer_id
    
    def get_customer_name(self, obj):
        """顧客名を取得（display_name property を使用）"""
        if obj.customer:
            return obj.customer.display_name
        return "Guest"
    
    def get_display_name(self, obj):
        """表示名を取得（customer_name と同じ）"""
        return self.get_customer_name(obj)

    def create(self, validated_data):
        """
        BillCustomer作成時、arrived_atが未指定なら自動で現在時刻を設定（自動IN）
        """
        if 'arrived_at' not in validated_data or validated_data['arrived_at'] is None:
            validated_data['arrived_at'] = timezone.now()
        
        return super().create(validated_data)

    def validate(self, attrs):
        """
        バリデーション：
        1. arrived_at と left_at が両方入る場合、left_at >= arrived_at を強制
        2. left_at だけ先に入れるのは禁止
        3. customer を差し替える際、同じ bill に同じ customer が既に存在していないか確認
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
        
        # customer を差し替える際の重複チェック（PATCH で customer フィールドが来た場合）
        customer = attrs.get('customer')
        if customer is not None:
            bill = attrs.get('bill')
            # create時は bill が来ていないので、self.instance で billCustomer を確認
            if not bill and self.instance:
                bill = self.instance.bill
            
            if bill and customer:
                # 同じ bill, customer の組み合わせが既に存在するか確認
                # 自分自身は除外（update の場合）
                existing = BillCustomer.objects.filter(
                    bill=bill,
                    customer=customer
                )
                if self.instance:
                    # update 時は自分を除外
                    existing = existing.exclude(id=self.instance.id)
                
                if existing.exists():
                    raise serializers.ValidationError(
                        {'customer': 'この顧客は既にこの伝票に参加しています。'}
                    )
        
        return attrs


class BillCustomerNominationSerializer(serializers.ModelSerializer):
    """本指名紐づけ（bill × customer × cast）"""
    
    class Meta:
        model = BillCustomerNomination
        fields = ['id', 'bill', 'customer', 'cast', 'started_at', 'ended_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'started_at', 'ended_at', 'created_at', 'updated_at']

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
