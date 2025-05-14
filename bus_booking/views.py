from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, Http404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from django.http import JsonResponse
from .models import Trip, Booking, Loyalty, Bus, TicketSale
from .forms import CustomUserCreationForm, TripForm, BusUpdateForm
from .models import RoutePrice, Location
 
def is_customer(user): return user.role == 'CUSTOMER'
def is_admin_or_super(user): return user.role == 'ADMIN' or user.is_superuser

def process_card_payment(): return True
def process_mpesa_payment(): return True

 
def index(request):
    form = CustomUserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.role = 'CUSTOMER'
        user.save()
        messages.success(request, "Registration successful! Please log in.")
        return redirect('login')
    return render(request, 'bus_booking/index.html', {'form': form})

 
def login_view(request):
    form = AuthenticationForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('admin_dashboard' if user.role == 'ADMIN' or user.is_superuser else 'customer_dashboard')
    return render(request, 'bus_booking/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('index')

 
@login_required
@user_passes_test(is_customer)
def customer_dashboard(request):
    bookings = Booking.objects.filter(customer=request.user).order_by('-booking_date')
    trips = Trip.objects.filter(bus__is_available=True, departure_time__gt=timezone.now())
    total_trips = bookings.filter(status="BOOKED").count()
    return render(request, 'bus_booking/customer_dashboard.html', {
        'trips': trips,
        'bookings': bookings,
        'eligible_for_free_trip': total_trips >= 4,
    })

@login_required
@user_passes_test(is_customer)
def payment_page(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    if not trip.is_available(): raise Http404("Trip is no longer available")

    rows = trip.bus.total_seats // trip.bus.seats_per_row
    letters = list("ABCD")[:trip.bus.seats_per_row]
    all_seats = [f"{r+1}{letters[c]}" for r in range(rows) for c in range(len(letters))]
    taken = Booking.objects.filter(trip=trip, status__in=["BOOKED", "PAID", "FREE"]).values_list("seat_number", flat=True)
    available_seats = [s for s in all_seats if s not in taken]

    if request.method == "POST":
        selected_seat = request.POST.get("seat_number")
        method = request.POST.get("payment_method")
        payment_success = (method == "cash") or (method == "card" and process_card_payment()) or (method == "mpesa" and process_mpesa_payment())

        if payment_success:
            booking = Booking.objects.create(customer=request.user, trip=trip, seat_number=selected_seat)
            booking.calculate_loyalty_points()
            booking.set_free_trip()
            booking.status = "PAID"
            booking.save()
            TicketSale.objects.create(bus=trip.bus, trip=trip, amount=trip.price)
            loyalty, _ = Loyalty.objects.get_or_create(customer=request.user)
            loyalty.points += booking.loyalty_points
            loyalty.save()
            messages.success(request, f"Payment successful with {method}. Booking confirmed as PAID!")
            return redirect('customer_dashboard')
        messages.error(request, "Payment failed. Please try again.")
    return render(request, 'bus_booking/payment_page.html', {'trip': trip, 'available_seats': available_seats})

 
@login_required
@user_passes_test(is_customer)
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, customer=request.user)
    if booking.status in ["BOOKED", "PAID", "RESCHEDULED"]:
        booking.status = "CANCELED"
        booking.save()
        messages.success(request, "Your booking has been successfully canceled.")
    else:
        messages.error(request, "You can only cancel a booked, paid or rescheduled trip.")
    return redirect('customer_dashboard')

@login_required
@user_passes_test(is_customer)
def reschedule_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, customer=request.user)
    if booking.status not in ["BOOKED", "PAID", "RESCHEDULED"]:
        messages.error(request, "You can only reschedule a booked, paid or rescheduled trip.")
        return redirect('customer_dashboard')

    if request.method == "POST":
        new_trip = get_object_or_404(Trip, id=request.POST.get('new_trip'))
        if new_trip.is_available():
            booking.trip = new_trip
            booking.status = "RESCHEDULED"
            booking.save()
            messages.success(request, "Your booking has been successfully rescheduled.")
            return redirect('customer_dashboard')
        messages.error(request, "The selected trip is not available.")

    available_trips = Trip.objects.filter(bus__is_available=True, departure_time__gt=timezone.now())
    return render(request, 'bus_booking/reschedule_booking.html', {'booking': booking, 'available_trips': available_trips})

 
@login_required
@user_passes_test(is_admin_or_super)
def admin_dashboard(request):
    def calculate_profit(period):
        today = timezone.now().date()
        if period == 'weekly': start = today - timedelta(days=7)
        elif period == 'monthly': start = today.replace(day=1)
        elif period == 'yearly': start = today.replace(month=1, day=1)
        else: start = today
        return (TicketSale.objects.filter(date__date__gte=start)
                .values('bus__bus','trip__origin','trip__destination')
                .annotate(total_profit=Sum('amount'))
                .order_by('-total_profit'))

    return render(request, 'bus_booking/admin_dashboard.html', {
        'bookings': Booking.objects.all(),
        'buses': Trip.objects.all(),
        'daily_profits': calculate_profit('daily'),
        'weekly_profits': calculate_profit('weekly'),
        'monthly_profits': calculate_profit('monthly'),
        'yearly_profits': calculate_profit('yearly'),
    })

@login_required
@user_passes_test(is_admin_or_super)
def update_bus(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    form = BusUpdateForm(request.POST or None, instance=bus)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Bus information updated successfully!")
        return redirect('admin_dashboard')
    return render(request, 'bus_booking/update_bus.html', {'form': form, 'bus': bus})

 
@login_required
@user_passes_test(is_customer)
def download_receipt(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    try:
        logo = RLImage('static/logo/logo.jpeg', width=100, height=100)
        elements += [logo, Spacer(1,12)]
    except: pass

    elements.append(Paragraph("QuickTransit Receipt", styles['Title']))
    elements.append(Spacer(1,12))
    data = [["Field","Value"],["Customer",booking.customer.username],
            ["Trip",str(booking.trip)],["Seat",booking.seat_number],
            ["Status",booking.status],["Date",booking.booking_date.strftime("%Y-%m-%d %H:%M:%S")],
            ["Points",booking.loyalty_points]]
    table = Table(data, colWidths=[150,300])
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'LEFT'),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ]))
    elements += [table, Spacer(1,12), Paragraph("Thank you!",styles['Normal'])]
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{booking.id}.pdf"'
    return response

@login_required
@user_passes_test(is_admin_or_super)
def generate_receipt(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    content = (f"Receipt for Booking\n"
               f"Customer: {booking.customer.username}\n"
               f"Trip: {booking.trip}\n"
               f"Seat: {booking.seat_number}\n"
               f"Status: {booking.status}\n"
               f"Date: {booking.booking_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
               f"Points: {booking.loyalty_points}\n")
    return HttpResponse(content, content_type="text/plain")

@login_required
@user_passes_test(is_admin_or_super)
def create_trip(request):
    form = TripForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('admin_dashboard')
    return render(request, 'bus_booking/create_trip.html', {'form': form})


def register_customer(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'CUSTOMER'
            user.save()
            messages.success(request, "Registration successful! Please log in.")
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'bus_booking/register_customer.html', {'form': form})
 
 

def get_trip_price(request):
    origin_id = request.GET.get('origin_id')
    destination_id = request.GET.get('destination_id')

    if origin_id and destination_id:
        try:
            price = RoutePrice.objects.get(origin_id=origin_id, destination_id=destination_id).price
            return JsonResponse({'price': price})
        except RoutePrice.DoesNotExist:
            return JsonResponse({'error': 'Price not found'}, status=404)

    return JsonResponse({'error': 'Invalid input'}, status=400)
