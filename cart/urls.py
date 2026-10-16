from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.cart_page,
        name="cart_page"
    ),

    path(
        "add/<int:course_id>/",
        views.add_to_cart,
        name="add_to_cart"
    ),

    path(
        "remove/<int:course_id>/",
        views.remove_from_cart,
        name="remove_from_cart"
    ),

    path(
        "clear/",
        views.clear_cart,
        name="clear_cart"
    ),

    path(
        "enroll-free/<int:course_id>/",
        views.enroll_free_from_cart,
        name="enroll_free_from_cart"
    ),
]