from django.db import models


class Table(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        OCCUPIED = 'OCCUPIED', 'Occupied'
        BILL_REQUESTED = 'BILL_REQUESTED', 'Bill Requested'

    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE, related_name='tables')
    number = models.PositiveIntegerField()
    name = models.CharField(max_length=100, blank=True)
    capacity = models.PositiveIntegerField(default=4)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['business', 'number'], name='unique_table_number_per_business')
        ]
        ordering = ['number']
