from django.shortcuts import render

# Create your views here.
from decimal import Decimal

import razorpay

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from courses.models import Course

from .models import Orders, Payments, Enrollment


razorpay_client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
)


def get_course_price(course):
    """
    Get the actual price from the database.

    For a paid course:
    discounted_price is used when it is greater than zero.
    Otherwise the normal price is used.
    """

    if course.discounted_price and course.discounted_price > 0:
        return Decimal(course.discounted_price)

    return Decimal(course.price)


@login_required(login_url="/accounts/login/")
@require_POST
def enroll_free_course(request, course_id):

    course = get_object_or_404(
        Course,
        course_id=course_id,
        status="PUBLISHED"
    )

    # Make sure this endpoint cannot be used
    # for paid courses.
    if course.course_type != "FREE":
        return JsonResponse(
            {
                "success": False,
                "message": "This is a paid course."
            },
            status=400
        )

    # Check whether the student is already enrolled.
    existing_enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course
    ).first()

    if existing_enrollment:

        return JsonResponse(
            {
                "success": True,
                "already_enrolled": True,
                "message": "You are already enrolled in this course."
            }
        )

    enrollment = Enrollment.objects.create(
        student=request.user,
        course=course,
        order=None,
        enrollment_type="FREE",
        status="ACTIVE",
        completion_percentage=Decimal("0.00")
    )

    return JsonResponse(
        {
            "success": True,
            "already_enrolled": False,
            "message": "Successfully enrolled in the course.",
            "enrollment_id": enrollment.enrollment_id
        }
    )


@login_required(login_url="/accounts/login/")
@require_POST
def create_razorpay_order(request, course_id):

    course = get_object_or_404(
        Course,
        course_id=course_id,
        status="PUBLISHED"
    )

    # This endpoint is only for paid courses.
    if course.course_type != "PAID":

        return JsonResponse(
            {
                "success": False,
                "message": "This course is free. No payment is required."
            },
            status=400
        )

    # Check whether already enrolled.
    existing_enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course,
        status__in=["ACTIVE", "COMPLETED"]
    ).first()

    if existing_enrollment:

        return JsonResponse(
            {
                "success": False,
                "already_enrolled": True,
                "message": "You are already enrolled in this course."
            },
            status=400
        )

    amount = get_course_price(course)

    if amount <= 0:

        return JsonResponse(
            {
                "success": False,
                "message": "Invalid course price."
            },
            status=400
        )

    # Razorpay expects amount in the smallest currency unit.
    # Example:
    #
    # ₹799 = 79900 paise
    #
    amount_in_paise = int(amount * 100)

    receipt = (
        f"course_{course.course_id}_"
        f"user_{request.user.user_id}_"
        f"{int(timezone.now().timestamp())}"
    )

    try:

        razorpay_order = razorpay_client.order.create(
            {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": receipt,
                "payment_capture": 1
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": "Unable to create Razorpay order.",
                "error": str(e)
            },
            status=500
        )

    local_order = Orders.objects.create(

        student=request.user,

        course=course,

        amount=amount,

        currency="INR",

        order_status="PENDING",

        gateway_order_id=razorpay_order["id"]
    )

    return JsonResponse(
        {
            "success": True,

            "order_id": local_order.order_id,

            "razorpay_order_id": razorpay_order["id"],

            "amount": amount_in_paise,

            "currency": "INR",

            "key_id": settings.RAZORPAY_KEY_ID,

            "course_title": course.title,

            "student_name": (
                f"{request.user.first_name} "
                f"{request.user.last_name or ''}"
            ).strip(),

            "student_email": request.user.email,

            "student_phone": request.user.phone or "",
        }
    )


@login_required(login_url="/accounts/login/")
@require_POST
def verify_razorpay_payment(request):

    razorpay_payment_id = request.POST.get(
        "razorpay_payment_id"
    )

    razorpay_order_id = request.POST.get(
        "razorpay_order_id"
    )

    razorpay_signature = request.POST.get(
        "razorpay_signature"
    )

    local_order_id = request.POST.get(
        "local_order_id"
    )

    if not all(
        [
            razorpay_payment_id,
            razorpay_order_id,
            razorpay_signature,
            local_order_id,
        ]
    ):

        return JsonResponse(
            {
                "success": False,
                "message": "Incomplete payment information."
            },
            status=400
        )

    try:

        local_order = Orders.objects.get(
            order_id=local_order_id,
            student=request.user
        )

    except Orders.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": "Order not found."
            },
            status=404
        )

    # ------------------------------------------------
    # IMPORTANT SECURITY CHECK
    # ------------------------------------------------

    # The Razorpay order received from frontend
    # must match the Razorpay order stored in our DB.

    if local_order.gateway_order_id != razorpay_order_id:

        return JsonResponse(
            {
                "success": False,
                "message": "Invalid Razorpay order."
            },
            status=400
        )

    # Do not allow a previously processed order
    # to be processed again.

    if local_order.order_status == "PAID":

        return JsonResponse(
            {
                "success": True,
                "message": "Payment was already processed."
            }
        )

    # ------------------------------------------------
    # VERIFY RAZORPAY SIGNATURE
    # ------------------------------------------------

    try:

        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )

    except razorpay.errors.SignatureVerificationError:

        local_order.order_status = "FAILED"
        local_order.save(
            update_fields=[
                "order_status",
                "updated_at"
            ]
        )

        Payments.objects.create(

            order=local_order,

            student=request.user,

            amount=local_order.amount,

            payment_method=None,

            gateway_payment_id=razorpay_payment_id,

            gateway_signature=razorpay_signature,

            payment_status="FAILED",

            UTR=""
        )

        return JsonResponse(
            {
                "success": False,
                "message": "Payment signature verification failed."
            },
            status=400
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": "Payment verification failed.",
                "error": str(e)
            },
            status=500
        )

    # ------------------------------------------------
    # FETCH PAYMENT FROM RAZORPAY
    # ------------------------------------------------

    try:

        razorpay_payment = razorpay_client.payment.fetch(
            razorpay_payment_id
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": "Unable to verify payment status.",
                "error": str(e)
            },
            status=500
        )

    # Verify that the payment belongs to the same
    # Razorpay order.

    if razorpay_payment.get("order_id") != razorpay_order_id:

        return JsonResponse(
            {
                "success": False,
                "message": "Payment does not belong to this order."
            },
            status=400
        )

    # ------------------------------------------------
    # VERIFY PAYMENT AMOUNT
    # ------------------------------------------------

    expected_amount = int(
        local_order.amount * Decimal("100")
    )

    received_amount = int(
        razorpay_payment.get("amount", 0)
    )

    if received_amount != expected_amount:

        local_order.order_status = "FAILED"

        local_order.save(
            update_fields=[
                "order_status",
                "updated_at"
            ]
        )

        return JsonResponse(
            {
                "success": False,
                "message": "Payment amount mismatch."
            },
            status=400
        )

    # ------------------------------------------------
    # CHECK PAYMENT STATUS
    # ------------------------------------------------

    payment_status = razorpay_payment.get(
        "status"
    )

    # The course should only be granted after
    # a successful/captured payment.

    if payment_status != "captured":

        local_order.order_status = "FAILED"

        local_order.save(
            update_fields=[
                "order_status",
                "updated_at"
            ]
        )

        Payments.objects.create(

            order=local_order,

            student=request.user,

            amount=local_order.amount,

            payment_method=razorpay_payment.get(
                "method"
            ),

            gateway_payment_id=razorpay_payment_id,

            gateway_signature=razorpay_signature,

            payment_status="FAILED",

            UTR=razorpay_payment.get(
                "vpa",
                ""
            ) or ""
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Payment is not captured yet. "
                    "Enrollment was not created."
                )
            },
            status=400
        )

    # ------------------------------------------------
    # SAVE SUCCESSFUL PAYMENT
    # AND CREATE ENROLLMENT
    # ------------------------------------------------

    try:

        with transaction.atomic():

            # Create successful payment record.

            payment = Payments.objects.create(

                order=local_order,

                student=request.user,

                amount=local_order.amount,

                payment_method=razorpay_payment.get(
                    "method"
                ),

                gateway_payment_id=razorpay_payment_id,

                gateway_signature=razorpay_signature,

                payment_status="SUCCESS",

                UTR=razorpay_payment.get(
                    "vpa",
                    ""
                ) or "",

                paid_at=timezone.now()
            )

            # Update order.

            local_order.order_status = "PAID"

            local_order.save(
                update_fields=[
                    "order_status",
                    "updated_at"
                ]
            )

            # Check again for an existing enrollment.

            enrollment = Enrollment.objects.filter(
                student=request.user,
                course=local_order.course
            ).first()

            if enrollment is None:

                enrollment = Enrollment.objects.create(

                    student=request.user,

                    course=local_order.course,

                    order=local_order,

                    enrollment_type="PAID",

                    status="ACTIVE",

                    completion_percentage=Decimal(
                        "0.00"
                    )
                )

            else:

                # If enrollment already exists,
                # connect it to this successful order.

                enrollment.order = local_order

                enrollment.enrollment_type = "PAID"

                enrollment.status = "ACTIVE"

                enrollment.save(
                    update_fields=[
                        "order",
                        "enrollment_type",
                        "status"
                    ]
                )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Payment was verified, "
                    "but enrollment could not be created."
                ),
                "error": str(e)
            },
            status=500
        )

    return JsonResponse(
        {
            "success": True,

            "message": (
                "Payment successful. "
                "You are now enrolled in the course."
            ),

            "payment_id": payment.payment_id,

            "enrollment_id": enrollment.enrollment_id,

            "course_id": local_order.course.course_id
        }
    )