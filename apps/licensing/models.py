from django.db import models


class License(models.Model):
    business = models.OneToOneField('businesses.Business', on_delete=models.CASCADE, related_name='license')
    key = models.CharField(max_length=64, unique=True)
    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def valid(self):
        from django.utils import timezone
        now = timezone.now()
        return self.is_active and self.starts_at <= now <= self.expires_at
