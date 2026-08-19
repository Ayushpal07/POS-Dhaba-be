from decimal import Decimal
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.licensing.models import License
from apps.menu.models import Category, MenuItem
from apps.tables.models import Table
from apps.orders.models import Order, OrderRound, OrderItem
from apps.billing.models import Bill
from apps.payments.models import Payment


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.method in SAFE_METHODS or request.user.role == User.Role.ADMIN
        ))


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class UserSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source='business.name', read_only=True)
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'role', 'business', 'business_name', 'is_active')
        read_only_fields = ('business',)


class LicenseSerializer(serializers.ModelSerializer):
    valid = serializers.BooleanField(read_only=True)
    class Meta:
        model = License
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ('business',)


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    class Meta:
        model = MenuItem
        fields = '__all__' + ''
        read_only_fields = ('business',)


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = '__all__'
        read_only_fields = ('business', 'status')


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    class Meta:
        model = OrderItem
        fields = ('id', 'round', 'menu_item', 'menu_item_name', 'quantity', 'unit_price', 'notes', 'line_total')
        read_only_fields = ('round', 'unit_price')


class OrderRoundSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = OrderRound
        fields = ('id', 'number', 'sent_at', 'created_at', 'items')


class OrderSerializer(serializers.ModelSerializer):
    rounds = OrderRoundSerializer(many=True, read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    table_number = serializers.IntegerField(source='table.number', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    class Meta:
        model = Order
        fields = ('id', 'table', 'table_number', 'status', 'notes', 'opened_at', 'closed_at', 'created_at', 'updated_at', 'created_by_name', 'rounds', 'items')
        read_only_fields = ('business', 'created_by', 'status', 'opened_at', 'closed_at')


class BillSerializer(serializers.ModelSerializer):
    table_number = serializers.IntegerField(source='order.table.number', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)
    class Meta:
        model = Bill
        fields = '__all__' + ''


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


class TenantViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrReadOnly,)
    business_field = 'business'

    def get_queryset(self):
        qs = self.queryset
        if getattr(self.request.user, 'business_id', None):
            return qs.filter(**{self.business_field: self.request.user.business_id})
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


class CategoryViewSet(TenantViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class MenuItemViewSet(TenantViewSet):
    queryset = MenuItem.objects.select_related('category').all()
    serializer_class = MenuItemSerializer


class TableViewSet(TenantViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer


class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        return self.queryset.filter(id=self.request.user.business_id) if self.request.user.business_id else self.queryset.none()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(business_id=self.request.user.business_id)

    def _admin_only(self, request):
        return request.user.role == User.Role.ADMIN

    def create(self, request, *args, **kwargs):
        if not self._admin_only(request):
            return Response({'detail': 'Only admins can manage users.'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        password = data.pop('password', None)
        if not password:
            return Response({'detail': 'password is required.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(business=request.user.business)
        user.set_password(password)
        user.save(update_fields=['password'])
        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not self._admin_only(request):
            return Response({'detail': 'Only admins can manage users.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not self._admin_only(request):
            return Response({'detail': 'Only admins can manage users.'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self._admin_only(request):
            return Response({'detail': 'Only admins can manage users.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('table', 'created_by').prefetch_related('rounds__items__menu_item')
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(business_id=self.request.user.business_id)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        business = request.user.business
        table = Table.objects.filter(id=request.data.get('table'), business=business).first()
        if not table:
            return Response({'detail': 'Table not found.'}, status=status.HTTP_404_NOT_FOUND)
        if table.status != Table.Status.AVAILABLE:
            return Response({'detail': 'Table is not available.'}, status=status.HTTP_400_BAD_REQUEST)
        items = request.data.get('items', [])
        if not items:
            return Response({'detail': 'At least one item is required.'}, status=status.HTTP_400_BAD_REQUEST)
        order = Order.objects.create(business=business, table=table, created_by=request.user, status=Order.Status.OPEN, opened_at=timezone.now(), notes=request.data.get('notes', ''))
        round_obj = OrderRound.objects.create(order=order, number=1, sent_at=timezone.now())
        self._add_items(order, round_obj, items, business)
        table.status = Table.Status.OCCUPIED
        table.save(update_fields=['status'])
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    def _add_items(self, order, round_obj, items, business):
        for data in items:
            menu_item = MenuItem.objects.filter(id=data.get('menu_item'), business=business, is_available=True).first()
            if not menu_item:
                raise serializers.ValidationError({'items': f"Menu item {data.get('menu_item')} is unavailable."})
            OrderItem.objects.create(order=order, round=round_obj, menu_item=menu_item, quantity=max(1, int(data.get('quantity', 1))), unit_price=menu_item.price, notes=data.get('notes', ''))

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def add_round(self, request, pk=None):
        order = self.get_object()
        if order.status not in (Order.Status.OPEN, Order.Status.DRAFT):
            return Response({'detail': 'Order cannot accept another round.'}, status=status.HTTP_400_BAD_REQUEST)
        items = request.data.get('items', [])
        if not items:
            return Response({'detail': 'At least one item is required.'}, status=status.HTTP_400_BAD_REQUEST)
        number = order.rounds.count() + 1
        round_obj = OrderRound.objects.create(order=order, number=number, sent_at=timezone.now())
        self._add_items(order, round_obj, items, request.user.business)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def request_bill(self, request, pk=None):
        order = self.get_object()
        if order.status not in (Order.Status.OPEN, Order.Status.BILL_REQUESTED):
            return Response({'detail': 'Order is not open.'}, status=status.HTTP_400_BAD_REQUEST)
        subtotal = sum((item.line_total for item in order.items.all()), Decimal('0.00'))
        tax = Decimal(str(request.data.get('tax', '0')))
        discount = Decimal(str(request.data.get('discount', '0')))
        total = subtotal + tax - discount
        bill, _ = Bill.objects.get_or_create(order=order, defaults={'subtotal': subtotal, 'tax': tax, 'discount': discount, 'total': total, 'status': Bill.Status.ISSUED, 'issued_at': timezone.now()})
        if bill.status == Bill.Status.DRAFT:
            bill.subtotal, bill.tax, bill.discount, bill.total, bill.status, bill.issued_at = subtotal, tax, discount, total, Bill.Status.ISSUED, timezone.now()
            bill.save()
        order.status = Order.Status.BILL_REQUESTED
        order.table.status = Table.Status.BILL_REQUESTED
        order.table.save(update_fields=['status'])
        order.save(update_fields=['status', 'updated_at'])
        return Response(BillSerializer(bill).data)


class BillViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Bill.objects.select_related('order__table')
    serializer_class = BillSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(order__business_id=self.request.user.business_id)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('bill__order__table')
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(bill__order__business_id=self.request.user.business_id)

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.ADMIN:
            return Response({'detail': 'Only admins can complete payments.'}, status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            bill = Bill.objects.filter(id=request.data.get('bill'), order__business_id=request.user.business_id).first()
            if not bill:
                return Response({'detail': 'Bill not found.'}, status=status.HTTP_404_NOT_FOUND)
            amount = Decimal(str(request.data.get('amount', bill.total)))
            if amount != bill.total:
                return Response({'detail': 'Payment amount must equal bill total.'}, status=status.HTTP_400_BAD_REQUEST)
            if bill.status == Bill.Status.PAID:
                return Response({'detail': 'Bill is already paid.'}, status=status.HTTP_400_BAD_REQUEST)
            payment = Payment.objects.create(bill=bill, amount=amount, method=request.data.get('method'), status=Payment.Status.COMPLETED, reference=request.data.get('reference', ''), paid_at=timezone.now())
            bill.status = Bill.Status.PAID
            bill.save(update_fields=['status', 'updated_at'])
            order = bill.order
            order.status, order.closed_at = Order.Status.COMPLETED, timezone.now()
            order.save(update_fields=['status', 'closed_at', 'updated_at'])
            order.table.status = Table.Status.AVAILABLE
            order.table.save(update_fields=['status'])
            return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    user = authenticate(username=request.data.get('username'), password=request.data.get('password'))
    if not user or not user.is_active:
        return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
    refresh = RefreshToken.for_user(user)
    return Response({'access': str(refresh.access_token), 'refresh': str(refresh), 'user': UserSerializer(user).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)
