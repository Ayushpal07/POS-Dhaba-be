from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from config.api import (
    BusinessViewSet, UserViewSet, CategoryViewSet, MenuItemViewSet,
    TableViewSet, OrderViewSet, BillViewSet, PaymentViewSet, login, me,
)
from apps.orders.status import update_order_status

router = DefaultRouter()
router.register('businesses', BusinessViewSet, basename='business')
router.register('users', UserViewSet, basename='user')
router.register('categories', CategoryViewSet, basename='category')
router.register('menu-items', MenuItemViewSet, basename='menu-item')
router.register('tables', TableViewSet, basename='table')
router.register('orders', OrderViewSet, basename='order')
router.register('bills', BillViewSet, basename='bill')
router.register('payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', login, name='login'),
    path('api/auth/me/', me, name='me'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/orders/<int:pk>/status/', update_order_status, name='order-status'),
    path('api/', include(router.urls)),
]
