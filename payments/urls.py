from django.urls import path

from . import views


urlpatterns = [

    path(
        "enroll-free/<int:course_id>/",
        views.enroll_free_course,
        name="enroll_free_course"
    ),

    path(
        "create-order/",
        views.create_razorpay_order,
        name="create_razorpay_order"
    ),

    path(
        "verify-payment/",
        views.verify_razorpay_payment,
        name="verify_razorpay_payment"
    ),
]