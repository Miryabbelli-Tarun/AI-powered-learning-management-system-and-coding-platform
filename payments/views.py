from decimal import Decimal

import razorpay

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from courses.models import Course, Cart

from .models import (
    Orders,
    OrderItem,
    Payments,
    Enrollment,
)


# ============================================================
# RAZORPAY CLIENT
# ============================================================

razorpay_client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET,
    )
)


# ============================================================
# GET COURSE PRICE
# ============================================================

def get_course_price(course):

    if (
        course.discounted_price
        and course.discounted_price > 0
    ):
        return course.discounted_price

    return course.price


# ============================================================
# FREE COURSE DIRECT ENROLLMENT
# ============================================================

@login_required
@require_POST
def enroll_free_course(request, course_id):

    course = get_object_or_404(
        Course,
        course_id=course_id,
        status="PUBLISHED",
        course_type="FREE",
    )

    existing_enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course,
    ).first()

    if existing_enrollment:

        if existing_enrollment.status in [
            "ACTIVE",
            "COMPLETED",
        ]:

            return JsonResponse({
                "success": False,
                "message": "You are already enrolled in this course.",
            })

    Enrollment.objects.create(
        student=request.user,
        course=course,
        order=None,
        enrollment_type="FREE",
        status="ACTIVE",
        completion_percentage=Decimal("0.00"),
    )

    # Remove from cart if present
    Cart.objects.filter(
        user=request.user,
        course=course,
    ).delete()

    return JsonResponse({
        "success": True,
        "message": "You have been enrolled successfully.",
        "course_id": course.course_id,
    })


# ============================================================
# CREATE RAZORPAY ORDER
#
# Supports BOTH:
#
# 1. Single course
#    POST course_id=10
#
# 2. Entire cart
#    POST without course_id
#
# ============================================================

@login_required
@require_POST
def create_razorpay_order(request):

    course_id = request.POST.get("course_id")

    # ========================================================
    # SINGLE COURSE CHECKOUT
    # ========================================================

    if course_id:

        course = get_object_or_404(
            Course,
            course_id=course_id,
            status="PUBLISHED",
            course_type="PAID",
        )

        # Check existing enrollment
        already_enrolled = Enrollment.objects.filter(
            student=request.user,
            course=course,
            status__in=[
                "ACTIVE",
                "COMPLETED",
            ],
        ).exists()

        if already_enrolled:

            return JsonResponse({
                "success": False,
                "message": "You are already enrolled in this course.",
            }, status=400)

        price = get_course_price(course)

        if not price or price <= 0:

            return JsonResponse({
                "success": False,
                "message": "Invalid course price.",
            }, status=400)

        valid_courses = [
            {
                "course": course,
                "price": price,
            }
        ]

        total_amount = price

    # ========================================================
    # CART CHECKOUT
    # ========================================================

    else:

        cart_items = list(
            Cart.objects.filter(
                user=request.user
            ).select_related(
                "course"
            )
        )

        if not cart_items:

            return JsonResponse({
                "success": False,
                "message": "Your cart is empty.",
            }, status=400)

        valid_courses = []

        total_amount = Decimal("0.00")

        for cart_item in cart_items:

            course = cart_item.course

            # Course must be published
            if course.status != "PUBLISHED":
                continue

            # Free courses don't need Razorpay
            if course.course_type != "PAID":
                continue

            # Already enrolled courses shouldn't be charged
            already_enrolled = Enrollment.objects.filter(
                student=request.user,
                course=course,
                status__in=[
                    "ACTIVE",
                    "COMPLETED",
                ],
            ).exists()

            if already_enrolled:
                continue

            price = get_course_price(course)

            if not price or price <= 0:
                continue

            valid_courses.append({
                "course": course,
                "price": price,
            })

            total_amount += price

        if not valid_courses:

            return JsonResponse({
                "success": False,
                "message": "There are no paid courses available for checkout.",
            }, status=400)

    # ========================================================
    # RAZORPAY AMOUNT
    # ========================================================

    razorpay_amount = int(
        total_amount * Decimal("100")
    )

    # ========================================================
    # CREATE RAZORPAY ORDER
    # ========================================================

    razorpay_order = razorpay_client.order.create({
        "amount": razorpay_amount,
        "currency": "INR",
        "payment_capture": 1,
    })

    # ========================================================
    # CREATE LOCAL ORDER
    # ========================================================

    # For single course we can keep course populated.
    #
    # For cart checkout we keep course NULL because
    # OrderItem contains all purchased courses.

    single_course = None

    if len(valid_courses) == 1:
        single_course = valid_courses[0]["course"]

    order = Orders.objects.create(
        student=request.user,
        course=single_course,
        amount=total_amount,
        currency="INR",
        order_status="PENDING",
        gateway_order_id=razorpay_order["id"],
    )

    # ========================================================
    # CREATE ORDER ITEMS
    # ========================================================

    for item in valid_courses:

        OrderItem.objects.create(
            order=order,
            course=item["course"],
            price=item["price"],
        )

    # ========================================================
    # CREATE PAYMENT RECORD
    # ========================================================

    Payments.objects.create(
        order=order,
        student=request.user,
        amount=total_amount,
        payment_status="CREATED",
        UTR="",
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return JsonResponse({

        "success": True,

        "key_id": settings.RAZORPAY_KEY_ID,

        "amount": razorpay_amount,

        "currency": "INR",

        "razorpay_order_id": razorpay_order["id"],

        "local_order_id": order.order_id,

        "student_name": (
            f"{request.user.first_name} "
            f"{request.user.last_name}"
        ).strip(),

        "student_email": request.user.email,

        "student_phone": request.user.phone or "",

        "course_count": len(valid_courses),

        "total_amount": str(total_amount),

    })

# ============================================================
# VERIFY RAZORPAY PAYMENT
# ============================================================

@login_required
@require_POST
def verify_razorpay_payment(request):

    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_signature = request.POST.get("razorpay_signature")
    local_order_id = request.POST.get("local_order_id")

    # ========================================================
    # DEBUG INFORMATION
    # ========================================================

    print("\n")
    print("=" * 70)
    print("RAZORPAY PAYMENT VERIFICATION STARTED")
    print("=" * 70)

    print("Razorpay Payment ID :", razorpay_payment_id)
    print("Razorpay Order ID   :", razorpay_order_id)
    print("Razorpay Signature  :", razorpay_signature)
    print("Local Order ID      :", local_order_id)
    print("User                :", request.user.email)

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    if not all([
        razorpay_payment_id,
        razorpay_order_id,
        razorpay_signature,
        local_order_id,
    ]):

        print("ERROR: Missing payment information")

        return JsonResponse({
            "success": False,
            "message": "Missing payment information.",
        }, status=400)

    # ========================================================
    # GET LOCAL ORDER
    # ========================================================

    try:

        order = Orders.objects.get(
            order_id=local_order_id,
            student=request.user,
        )

    except Orders.DoesNotExist:

        print("ERROR: Local order not found")

        return JsonResponse({
            "success": False,
            "message": "Local order was not found.",
        }, status=400)

    print("Local Order Found    :", order.order_id)
    print("Local Order Status   :", order.order_status)
    print("Local Order Amount   :", order.amount)
    print("Gateway Order ID     :", order.gateway_order_id)

    # ========================================================
    # CHECK ORDER ID
    # ========================================================

    if order.gateway_order_id != razorpay_order_id:

        print("ERROR: Razorpay order ID mismatch")
        print("Expected:", order.gateway_order_id)
        print("Received:", razorpay_order_id)

        return JsonResponse({
            "success": False,
            "message": "Razorpay order ID mismatch.",
        }, status=400)

    # ========================================================
    # IF ALREADY PAID
    # ========================================================

    if order.order_status == "PAID":

        existing_enrollments = Enrollment.objects.filter(
            student=request.user,
            order=order,
        ).select_related("course")

        print("Order already marked as PAID")

        return JsonResponse({
            "success": True,
            "message": "Payment was already completed.",
            "order_id": order.order_id,
            "payment_id": razorpay_payment_id,
            "course_count": existing_enrollments.count(),
            "courses": [
                enrollment.course.title
                for enrollment in existing_enrollments
            ],
        })

    # ========================================================
    # VERIFY SIGNATURE
    # ========================================================

    print("-" * 70)
    print("STEP 1: VERIFYING PAYMENT SIGNATURE")
    print("-" * 70)

    try:

        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })

        print("SIGNATURE VERIFICATION SUCCESS")

    except razorpay.errors.SignatureVerificationError as error:

        print("SIGNATURE VERIFICATION FAILED")
        print("Error:", str(error))

        return JsonResponse({
            "success": False,
            "message": (
                "Payment signature verification failed. "
                "Please check your Razorpay Key ID and Key Secret."
            ),
        }, status=400)

    except Exception as error:

        print("SIGNATURE VERIFICATION ERROR")
        print("Error type:", type(error).__name__)
        print("Error:", str(error))

        return JsonResponse({
            "success": False,
            "message": (
                f"Signature verification error: {str(error)}"
            ),
        }, status=400)

    # ========================================================
    # FETCH PAYMENT FROM RAZORPAY
    # ========================================================

    print("-" * 70)
    print("STEP 2: FETCHING PAYMENT FROM RAZORPAY")
    print("-" * 70)

    try:

        razorpay_payment = razorpay_client.payment.fetch(
            razorpay_payment_id
        )

        print("RAZORPAY PAYMENT FETCH SUCCESS")
        print("Payment ID :", razorpay_payment.get("id"))
        print("Order ID   :", razorpay_payment.get("order_id"))
        print("Amount     :", razorpay_payment.get("amount"))
        print("Status     :", razorpay_payment.get("status"))
        print("Method     :", razorpay_payment.get("method"))

    except Exception as error:

        print("RAZORPAY PAYMENT FETCH FAILED")
        print("Error type:", type(error).__name__)
        print("Error:", str(error))

        return JsonResponse({
            "success": False,
            "message": (
                f"Unable to fetch payment from Razorpay: {str(error)}"
            ),
        }, status=400)

    # ========================================================
    # VERIFY RAZORPAY ORDER ID
    # ========================================================

    print("-" * 70)
    print("STEP 3: VERIFYING ORDER ID")
    print("-" * 70)

    razorpay_payment_order_id = razorpay_payment.get("order_id")

    print("Expected Order ID :", razorpay_order_id)
    print("Received Order ID :", razorpay_payment_order_id)

    if razorpay_payment_order_id != razorpay_order_id:

        print("ORDER ID MISMATCH")

        return JsonResponse({
            "success": False,
            "message": (
                "Payment order mismatch. "
                "The payment does not belong to this order."
            ),
        }, status=400)

    print("ORDER ID VERIFICATION SUCCESS")

    # ========================================================
    # VERIFY AMOUNT
    # ========================================================

    print("-" * 70)
    print("STEP 4: VERIFYING PAYMENT AMOUNT")
    print("-" * 70)

    expected_amount = int(
        order.amount * Decimal("100")
    )

    received_amount = int(
        razorpay_payment.get("amount", 0)
    )

    print("Expected Amount :", expected_amount)
    print("Received Amount :", received_amount)

    if received_amount != expected_amount:

        print("AMOUNT MISMATCH")

        return JsonResponse({
            "success": False,
            "message": (
                f"Payment amount mismatch. "
                f"Expected ₹{order.amount}, "
                f"received ₹{Decimal(received_amount) / Decimal('100')}."
            ),
        }, status=400)

    print("AMOUNT VERIFICATION SUCCESS")

    # ========================================================
    # VERIFY PAYMENT STATUS
    # ========================================================

    print("-" * 70)
    print("STEP 5: VERIFYING PAYMENT STATUS")
    print("-" * 70)

    payment_status = razorpay_payment.get("status")

    print("Razorpay Payment Status:", payment_status)

    if payment_status != "captured":

        print("PAYMENT NOT CAPTURED")

        return JsonResponse({
            "success": False,
            "message": (
                f"Payment is not captured. "
                f"Razorpay status: {payment_status}"
            ),
        }, status=400)

    print("PAYMENT STATUS VERIFICATION SUCCESS")

    # ========================================================
    # EVERYTHING VERIFIED
    # NOW CREATE ENROLLMENT
    # ========================================================

    print("-" * 70)
    print("ALL RAZORPAY VERIFICATIONS SUCCESSFUL")
    print("CREATING ENROLLMENT")
    print("-" * 70)

    try:

        with transaction.atomic():

            # ------------------------------------------------
            # PAYMENT
            # ------------------------------------------------

            payment = Payments.objects.filter(
                order=order
            ).first()

            if payment is None:

                payment = Payments.objects.create(
                    order=order,
                    student=request.user,
                    amount=order.amount,
                    payment_method=razorpay_payment.get(
                        "method"
                    ),
                    gateway_payment_id=razorpay_payment_id,
                    gateway_signature=razorpay_signature,
                    payment_status="SUCCESS",
                    UTR="",
                    paid_at=timezone.now(),
                )

            else:

                payment.student = request.user
                payment.amount = order.amount

                payment.payment_method = (
                    razorpay_payment.get("method")
                )

                payment.gateway_payment_id = (
                    razorpay_payment_id
                )

                payment.gateway_signature = (
                    razorpay_signature
                )

                payment.payment_status = "SUCCESS"

                payment.paid_at = timezone.now()

                payment.save()

            # ------------------------------------------------
            # UPDATE ORDER
            # ------------------------------------------------

            order.order_status = "PAID"

            order.save(
                update_fields=[
                    "order_status",
                    "updated_at",
                ]
            )

            # ------------------------------------------------
            # GET ORDER ITEMS
            # ------------------------------------------------

            order_items = OrderItem.objects.filter(
                order=order
            ).select_related("course")

            if not order_items.exists():

                raise Exception(
                    "No OrderItem found for this payment."
                )

            enrolled_courses = []

            # ------------------------------------------------
            # CREATE ENROLLMENT
            # ------------------------------------------------

            for item in order_items:

                print(
                    "Creating enrollment for:",
                    item.course.title
                )

                enrollment, created = (
                    Enrollment.objects.update_or_create(
                        student=request.user,
                        course=item.course,
                        defaults={
                            "order": order,
                            "enrollment_type": "PAID",
                            "status": "ACTIVE",
                            "completion_percentage": Decimal(
                                "0.00"
                            ),
                        },
                    )
                )

                print(
                    "Enrollment ID:",
                    enrollment.enrollment_id
                )

                print(
                    "Enrollment Created:",
                    created
                )

                enrolled_courses.append(
                    item.course.title
                )

                # --------------------------------------------
                # REMOVE FROM CART
                # --------------------------------------------

                Cart.objects.filter(
                    user=request.user,
                    course=item.course,
                ).delete()

        print("-" * 70)
        print("PAYMENT + ENROLLMENT TRANSACTION SUCCESS")
        print("Courses:", enrolled_courses)
        print("-" * 70)

    except Exception as error:

        print("-" * 70)
        print("ENROLLMENT TRANSACTION FAILED")
        print("Error type:", type(error).__name__)
        print("Error:", str(error))
        print("-" * 70)

        return JsonResponse({
            "success": False,
            "message": (
                f"Payment verified, but enrollment failed: "
                f"{str(error)}"
            ),
        }, status=500)

    # ========================================================
    # FINAL SUCCESS RESPONSE
    # ========================================================

    return JsonResponse({

        "success": True,

        "message": (
            "Payment successful. "
            "You have been enrolled in all purchased courses."
        ),

        "order_id": order.order_id,

        "payment_id": razorpay_payment_id,

        "course_count": len(enrolled_courses),

        "courses": enrolled_courses,

    })