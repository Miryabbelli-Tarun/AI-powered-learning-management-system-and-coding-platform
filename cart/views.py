

# Create your views here.
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from courses.models import Course, Cart
from payments.models import Enrollment


def get_course_price(course):

    if (
        course.discounted_price
        and course.discounted_price > 0
    ):
        return course.discounted_price

    return course.price


@login_required
def cart_page(request):

    cart_items = list(
        Cart.objects.filter(
            user=request.user
        ).select_related(
            "course",
            "course__category",
            "course__instructor"
        ).order_by("-added_at")
    )

    subtotal = Decimal("0.00")

    paid_count = 0
    free_count = 0

    for item in cart_items:

        item.actual_price = get_course_price(
            item.course
        )

        if item.course.course_type == "PAID":

            subtotal += item.actual_price
            paid_count += 1

        else:

            free_count += 1

    context = {

        "cart_items": cart_items,

        "cart_count": len(cart_items),

        "paid_count": paid_count,

        "free_count": free_count,

        "subtotal": subtotal,

        "total": subtotal,
    }

    return render(
        request,
        "cart/cart.html",
        context
    )


@login_required
@require_POST
def add_to_cart(request, course_id):

    course = get_object_or_404(
        Course,
        course_id=course_id,
        status="PUBLISHED"
    )

    already_enrolled = Enrollment.objects.filter(
        student=request.user,
        course=course,
        status__in=[
            "ACTIVE",
            "COMPLETED"
        ]
    ).exists()

    if already_enrolled:

        messages.info(
            request,
            "You are already enrolled in this course."
        )

        return redirect(
            request.META.get(
                "HTTP_REFERER",
                "all_courses"
            )
        )

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        course=course
    )

    if created:

        messages.success(
            request,
            f'"{course.title}" was added to your cart.'
        )

    else:

        messages.info(
            request,
            "This course is already in your cart."
        )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "all_courses"
        )
    )


@login_required
@require_POST
def remove_from_cart(request, course_id):

    cart_item = Cart.objects.filter(
        user=request.user,
        course_id=course_id
    ).first()

    if cart_item:

        course_title = cart_item.course.title

        cart_item.delete()

        messages.success(
            request,
            f'"{course_title}" was removed from your cart.'
        )

    return redirect("cart_page")


@login_required
@require_POST
def clear_cart(request):

    Cart.objects.filter(
        user=request.user
    ).delete()

    messages.success(
        request,
        "Your cart has been cleared."
    )

    return redirect("cart_page")


@login_required
@require_POST
def enroll_free_from_cart(request, course_id):

    course = get_object_or_404(
        Course,
        course_id=course_id,
        status="PUBLISHED",
        course_type="FREE"
    )

    cart_item = Cart.objects.filter(
        user=request.user,
        course=course
    ).first()

    if not cart_item:

        messages.error(
            request,
            "This course is not in your cart."
        )

        return redirect("cart_page")

    existing_enrollment = Enrollment.objects.filter(
        student=request.user,
        course=course
    ).first()

    if existing_enrollment:

        if existing_enrollment.status in [
            "ACTIVE",
            "COMPLETED"
        ]:

            cart_item.delete()

            messages.info(
                request,
                "You are already enrolled in this course."
            )

            return redirect("cart_page")

    Enrollment.objects.create(
        student=request.user,
        course=course,
        order=None,
        enrollment_type="FREE",
        status="ACTIVE",
        completion_percentage=Decimal("0.00")
    )

    cart_item.delete()

    messages.success(
        request,
        f'You are now enrolled in "{course.title}".'
    )

    return redirect("cart_page")