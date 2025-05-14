from datetime import timedelta
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Sum
from django.utils import timezone
from django.template.response import TemplateResponse 
from django.contrib.auth.models import Group
from django.utils.dateparse import parse_date
from .models import (
    User,
    Booking,
    Trip,
    Bus,
    Loyalty,
    BusInventory,
    TicketSale,
)
from .models import Location, RoutePrice

@admin.register(User)
class CustomUserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('customer', 'trip', 'status', 'loyalty_points', 'booking_date')
    list_filter  = ('status',)

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display   = ('bus', 'origin', 'destination', 'departure_time', 'price', 'active')
    list_editable  = ('active',)
    list_filter    = ('active', 'origin', 'destination')
    search_fields  = ('origin', 'destination')

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display   = ('bus', 'origin', 'destination', 'departure_time', 'price', 'is_available')
    list_editable  = ('is_available',)
    list_filter    = ('is_available', 'origin', 'destination')
    search_fields  = ('bus', 'origin', 'destination')

@admin.register(Loyalty)
class LoyaltyAdmin(admin.ModelAdmin):
    list_display = ('customer', 'trips_booked', 'free_trip_eligible')

    def trips_booked(self, obj):
        return Booking.objects.filter(customer=obj.customer, status="BOOKED").count()
    trips_booked.short_description = 'Trips Booked'

@admin.register(BusInventory)
class BusInventoryAdmin(admin.ModelAdmin):
    list_display = ('bus', 'status', 'purchase_date')
    list_filter  = ('status',)

@admin.register(TicketSale)
class TicketSaleAdmin(admin.ModelAdmin):
    list_display = ('bus', 'trip', 'amount', 'date')
    list_filter = ('bus', 'trip', 'date')
    change_list_template = "admin/bus_booking/ticketsale/change_list.html"

    def changelist_view(self, request, extra_context=None):
        today = timezone.now().date()
        start_date_raw = request.GET.get("start_date")
        end_date_raw = request.GET.get("end_date")

        start_date = parse_date(start_date_raw) if start_date_raw else None
        end_date = parse_date(end_date_raw) if end_date_raw else None

        queryset = TicketSale.objects.all()
        if start_date:
            queryset = queryset.filter(date__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__date__lte=end_date)

        past_7_days = [today - timedelta(days=i) for i in range(7)]
        daily_revenue = []
        for date in reversed(past_7_days):
            revenue = TicketSale.objects.filter(date__date=date).aggregate(total=Sum('amount'))['total'] or 0
            daily_revenue.append({'date': date, 'revenue': revenue})

        week_start = today - timedelta(days=today.weekday())  
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        weekly_total = TicketSale.objects.filter(date__date__gte=week_start).aggregate(Sum('amount'))['amount__sum'] or 0
        monthly_total = TicketSale.objects.filter(date__date__gte=month_start).aggregate(Sum('amount'))['amount__sum'] or 0
        yearly_total = TicketSale.objects.filter(date__date__gte=year_start).aggregate(Sum('amount'))['amount__sum'] or 0

        extra_context = extra_context or {}
        extra_context['daily_revenue'] = daily_revenue
        extra_context['weekly_total'] = weekly_total
        extra_context['monthly_total'] = monthly_total
        extra_context['yearly_total'] = yearly_total

        return super().changelist_view(request, extra_context=extra_context)
 


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(RoutePrice)
class RoutePriceAdmin(admin.ModelAdmin):
    list_display = ('origin', 'destination', 'price')
    list_filter = ('origin', 'destination')
    search_fields = ('origin__name', 'destination__name')

admin.site.site_header = "Quick Transit Bus Booking System"
admin.site.site_title = "Bus Booking Admin Portal"
admin.site.index_title = "Welcome Our Valued User!"
admin.site.unregister(Group)
