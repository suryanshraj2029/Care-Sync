
from django.conf import settings
from django.db import models


class DoctorAvailability(models.Model):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availabilities",
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.PositiveIntegerField(default=15)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["date", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="availability_end_after_start",
            ),
            models.CheckConstraint(
                condition=models.Q(slot_duration__gt=0),
                name="availability_slot_duration_positive",
            ),
        ]

    def __str__(self):
        return f"{self.doctor} - {self.date} ({self.start_time}-{self.end_time})"


class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        CONFIRMED = "CONFIRMED", "Confirmed"
        ARRIVED = "ARRIVED", "Arrived"
        IN_CONSULTATION = "IN_CONSULTATION", "In consultation"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No-show"

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patient_appointments",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="doctor_appointments",
    )
    availability = models.ForeignKey(
        DoctorAvailability,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    appointment_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.BOOKED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["appointment_date", "start_time"]
        indexes = [
            models.Index(fields=["doctor", "appointment_date", "status"]),
            models.Index(fields=["patient", "appointment_date"]),
        ]

    def __str__(self):
        return (
            f"{self.patient} with {self.doctor} "
            f"on {self.appointment_date} at {self.start_time}"
        )

