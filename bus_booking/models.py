from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.validators import RegexValidator

class User(AbstractUser):
    class Roles(models.TextChoices):
        SUPERUSER = "SUPERUSER", _("Superuser")
        ADMIN = "ADMIN", _("Admin")
        CUSTOMER = "CUSTOMER", _("Customer")

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.CUSTOMER,
    )

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Roles.SUPERUSER
        elif self.is_staff:
            self.role = self.Roles.ADMIN
        super().save(*args, **kwargs)


class Bus(models.Model):
    bus = models.CharField(max_length=255)
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    departure_time = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_seats = models.PositiveIntegerField(default=50)
    seats_per_row = models.PositiveIntegerField(default=4)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.bus} ({self.origin} -> {self.destination})"

    def is_departure_soon(self):
        return self.departure_time <= (timezone.now() + timedelta(days=1))


class Trip(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    departure_time = models.DateTimeField()
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.origin} to {self.destination} at {self.departure_time}"

    def is_available(self):
        return self.bus.is_available and self.active and self.departure_time > timezone.now()


seat_validator = RegexValidator(r'^\d{1,2}[A-Z]$', "Seat must be like '1A', '12B', etc.")


class Booking(models.Model):
    STATUS_CHOICES = [
        ("BOOKED", "Booked"),
        ("CANCELED", "Canceled"),
        ("RESCHEDULED", "Rescheduled"),
        ("FREE", "Free"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "CUSTOMER"}
    )
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    booking_date = models.DateTimeField(auto_now_add=True)
    seat_number = models.CharField(
        max_length=3,
        validators=[seat_validator],
        verbose_name="Seat Number"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="BOOKED")
    loyalty_points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.customer.username} - {self.trip} (Seat {self.seat_number})"

    def save(self, *args, **kwargs):
        if not self.pk:   
            self.calculate_loyalty_points()
            self.set_free_trip()
        super().save(*args, **kwargs)

    def calculate_loyalty_points(self):
        self.loyalty_points = 5 if self.status == "BOOKED" else 0

    def set_free_trip(self):
        total_booked = Booking.objects.filter(customer=self.customer, status="BOOKED").count()
        free_trips = Booking.objects.filter(customer=self.customer, status="FREE").count()
        if (total_booked // 4) > free_trips:
            self.status = "FREE"
            self.loyalty_points = 0

    def generate_receipt(self):
        return {
            "customer": self.customer.username,
            "trip": str(self.trip),
            "status": self.status,
            "seat_number": self.seat_number,
            "loyalty_points": self.loyalty_points,
            "price": 0 if self.status == "FREE" else self.trip.price,
            "booking_date": self.booking_date,
        }


class Loyalty(models.Model):
    customer = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    free_trip_eligible = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.customer.username} Loyalty"

    def add_points(self, amount):
        """
        Add loyalty points and check for free trip eligibility.
        """
        self.points += amount
         
        if self.points >= 100:
            self.free_trip_eligible = True
            self.points -= 100
        self.save()

    def redeem_free_trip(self):
        """
        Consume the free trip eligibility for the next booking.
        """
        if self.free_trip_eligible:
            self.free_trip_eligible = False
            self.save()
            return True
        return False


class BusInventory(models.Model):
    STATUS_CHOICES = [
        ("NEW", "New"),
        ("REPAIRED", "Repaired"),
        ("NOT_SERVICED", "Not Serviced"),
    ]
    bus = models.OneToOneField(Bus, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NEW")
    purchase_date = models.DateField()

    def __str__(self):
        return f"{self.bus} - {self.status}"


class TicketSale(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale for {self.bus} on {self.date.strftime('%Y-%m-%d')}"


class Location(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class RoutePrice(models.Model):
    origin = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='origin_routes')
    destination = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='destination_routes')
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('origin', 'destination')

    def __str__(self):
        return f"{self.origin} to {self.destination}: {self.price}"
