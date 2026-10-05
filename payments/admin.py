from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Orders, Payments, Enrollment


@admin.register(Orders)
class OrdersAdmin(admin.ModelAdmin):

    list_display = (
        "order_id",
        "student",
        "course",
        "amount",
        "currency",
        "order_status",
        "gateway_order_id",
        "created_at",
    )

    list_filter = (
        "order_status",
        "currency",
    )

    search_fields = (
        "gateway_order_id",
        "student__email",
        "course__title",
    )


@admin.register(Payments)
class PaymentsAdmin(admin.ModelAdmin):

    list_display = (
        "payment_id",
        "order",
        "student",
        "amount",
        "payment_method",
        "gateway_payment_id",
        "payment_status",
        "paid_at",
    )

    list_filter = (
        "payment_status",
        "payment_method",
    )

    search_fields = (
        "gateway_payment_id",
        "student__email",
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):

    list_display = (
        "enrollment_id",
        "student",
        "course",
        "enrollment_type",
        "status",
        "completion_percentage",
        "enrolled_at",
    )

    list_filter = (
        "enrollment_type",
        "status",
    )

    search_fields = (
        "student__email",
        "course__title",
    )