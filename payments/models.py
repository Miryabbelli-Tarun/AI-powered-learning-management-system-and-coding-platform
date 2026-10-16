from django.db import models

# Create your models here.


from django.db import models
from django.contrib.auth import get_user_model

from courses.models import Course


User = get_user_model()


class Orders(models.Model):

    ORDER_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"),
    ]

    order_id = models.BigAutoField(primary_key=True)

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payment_orders"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="payment_orders",
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=10
    )

    order_status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES
    )

    gateway_order_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "orders"

    def __str__(self):
        return f"Order {self.order_id} - {self.student.email}"

class OrderItem(models.Model):

    order_item_id = models.BigAutoField(
        primary_key=True
    )

    order = models.ForeignKey(
        Orders,
        on_delete=models.CASCADE,
        related_name="items"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="order_items"
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "order_items"

    def __str__(self):
        return f"{self.order.order_id} - {self.course.title}"




class Payments(models.Model):

    PAYMENT_STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    payment_id = models.BigAutoField(primary_key=True)

    order = models.ForeignKey(
        Orders,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=30,
        null=True,
        blank=True
    )

    gateway_payment_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )

    gateway_signature = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES
    )

    # Kept NOT NULL according to your original design.
    # Empty string is used when the payment method does not provide a UTR.
    UTR = models.CharField(
        max_length=50,
        default=""
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "payments"

    def __str__(self):
        return f"Payment {self.payment_id}"


class Enrollment(models.Model):

    ENROLLMENT_TYPE_CHOICES = [
        ("FREE", "Free"),
        ("PAID", "Paid"),
    ]

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    enrollment_id = models.BigAutoField(
        primary_key=True
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    order = models.ForeignKey(
        Orders,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrollment"
    )

    enrollment_type = models.CharField(
        max_length=20,
        choices=ENROLLMENT_TYPE_CHOICES
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )

    enrolled_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00
    )

    last_accessed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = "enrollment"

    def __str__(self):
        return f"{self.student.email} - {self.course.title}"