from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.models import User
from apps.billing.models import Bill
from apps.orders.models import Order
from apps.tables.models import Table
from config.api import OrderSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def update_order_status(request, pk):
    if request.user.role != User.Role.ADMIN:
        return Response({'detail': 'Only admins can update order status.'}, status=status.HTTP_403_FORBIDDEN)

    order = get_object_or_404(
        Order.objects.select_related('table', 'created_by').prefetch_related('rounds__items__menu_item'),
        id=pk,
        business_id=request.user.business_id,
    )

    new_status = request.data.get('status')
    allowed = {
        Order.Status.OPEN,
        Order.Status.BILL_REQUESTED,
        Order.Status.COMPLETED,
        Order.Status.CANCELLED,
    }
    if new_status not in allowed:
        return Response({'detail': 'Invalid order status.'}, status=status.HTTP_400_BAD_REQUEST)

    if order.status in (Order.Status.COMPLETED, Order.Status.CANCELLED) and new_status != order.status:
        return Response({'detail': 'Closed orders cannot be reopened.'}, status=status.HTTP_400_BAD_REQUEST)

    order.status = new_status
    if new_status in (Order.Status.COMPLETED, Order.Status.CANCELLED):
        order.closed_at = order.closed_at or timezone.now()
        order.table.status = Table.Status.AVAILABLE

        # A cancelled order's bill must no longer remain ISSUED.
        # Use the existing VOID bill status so no schema migration is required.
        if new_status == Order.Status.CANCELLED:
            Bill.objects.filter(order=order).exclude(status=Bill.Status.PAID).update(status=Bill.Status.VOID)

    elif new_status == Order.Status.BILL_REQUESTED:
        order.table.status = Table.Status.BILL_REQUESTED
    else:
        order.table.status = Table.Status.OCCUPIED

    order.table.save(update_fields=['status'])
    order.save(update_fields=['status', 'closed_at', 'updated_at'])

    return Response(OrderSerializer(order).data)
