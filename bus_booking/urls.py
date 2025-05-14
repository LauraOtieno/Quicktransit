from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('book-trip/<int:trip_id>/', views.payment_page, name='payment_page'),
    path('generate-receipt/<int:booking_id>/', views.generate_receipt, name='generate_receipt'),
    path('receipt/<int:booking_id>/', views.download_receipt, name='download_receipt'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('customer-dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('register/', views.register_customer, name='register_customer'),
    path('create-trip/', views.create_trip, name='create_trip'),
    path('booking/cancel/<int:pk>/', views.cancel_booking, name='cancel_booking'),
    path('booking/reschedule/<int:pk>/', views.reschedule_booking, name='reschedule_booking'),
    path('payment/<int:trip_id>/', views.payment_page, name='payment_page'),
    path('get-trip-price/', views.get_trip_price, name='get_trip_price'),
    
]
