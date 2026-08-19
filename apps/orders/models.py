from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPEN = 'OPEN', 'Open'
        BILL_REQUESTED = 'BILL_REQUESTED', 'Bill Requested'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE, related_name='orders')
    table = models.ForeignKey('tables.Table', on_delete=models.PROTECT, related_name='orders')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OrderRound(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='rounds')
    number = models.PositiveIntegerField()
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['order', 'number'], name='unique_round_per_order')
        ]
        ordering = ['number']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    round = models.ForeignKey(OrderRound, on_delete=models.PROTECT, related_name='items')
    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def line_total(self):
        return self.quantity * self.unit_price
