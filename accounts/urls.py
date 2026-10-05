from django.urls import path

from accounts import views

urlpatterns = [
    path('login/',views.login_view,name='login'),
    path('register/',views.register_view,name='register'),
    path('logout/',views.logout_view,name='logout'),
    path('verify-otp/',views.verify_otp_view,name='verify_otp'),
]

