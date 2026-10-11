
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

from users.models import User
from .models import Appointment, DoctorAvailability


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(
        source="doctor.username",
        read_only=True,
    )

    class Meta:
        model = DoctorAvailability
        fields = [
            "id",
            "doctor",
            "doctor_name",
            "date",
            "start_time",
            "end_time",
            "slot_duration",
            "is_available",
        ]
        read_only_fields = ["id", "doctor_name"]

    def validate(self, attrs):
        request = self.context.get("request")

        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "You must be logged in to manage availability."
            )

        user = request.user
        instance = self.instance

        allowed_roles = {
            User.Role.DOCTOR,
            User.Role.RECEPTIONIST,
            User.Role.ADMIN,
        }

        if user.role not in allowed_roles:
            raise serializers.ValidationError(
                "You are not allowed to manage doctor availability."
            )

        # Get the doctor from the submitted data or existing record.
        doctor = attrs.get(
            "doctor",
            instance.doctor if instance else None,
        )

        # Doctors can create and update only their own availability.
        if user.role == User.Role.DOCTOR:
            if instance and instance.doctor_id != user.id:
                raise serializers.ValidationError(
                    "You cannot modify another doctor's availability."
                )

            if doctor is not None and doctor.id != user.id:
                raise serializers.ValidationError({
                    "doctor": "You can manage only your own availability."
                })

            attrs["doctor"] = user
            doctor = user

        if doctor is None:
            raise serializers.ValidationError({
                "doctor": "Select a doctor."
            })

        if doctor.role != User.Role.DOCTOR or not doctor.is_active:
            raise serializers.ValidationError({
                "doctor": "Select a valid, active doctor."
            })

        # Support partial updates using existing field values.
        date = attrs.get(
            "date", instance.date if instance else None
        )
        start_time = attrs.get(
            "start_time", instance.start_time if instance else None
        )
        end_time = attrs.get(
            "end_time", instance.end_time if instance else None
        )
        slot_duration = attrs.get(
            "slot_duration",
            instance.slot_duration if instance else 15,
        )

        if date is not None and date < timezone.localdate():
            raise serializers.ValidationError({
                "date": "Availability cannot be set for a past date."
            })

        if (
            start_time is not None
            and end_time is not None
            and end_time <= start_time
        ):
            raise serializers.ValidationError({
                "end_time": "End time must be later than start time."
            })

        if slot_duration <= 0:
            raise serializers.ValidationError({
                "slot_duration": "Slot duration must be greater than zero."
            })

        # Prevent overlapping availability for the same doctor.
        if date and start_time and end_time:
            overlapping = DoctorAvailability.objects.filter(
                doctor=doctor,
                date=date,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )

            if instance:
                overlapping = overlapping.exclude(pk=instance.pk)

            if overlapping.exists():
                raise serializers.ValidationError({
                    "start_time": (
                        "This time overlaps with another availability period."
                    )
                })

        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source="patient.username",
        read_only=True,
    )

    doctor_name = serializers.CharField(
        source="doctor.username",
        read_only=True,
    )

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_name",
            "doctor",
            "doctor_name",
            "availability",
            "appointment_date",
            "start_time",
            "end_time",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "patient_name",
            "doctor_name",
            "end_time",
            "status",
            "created_at",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        allowed_roles = {
            User.Role.PATIENT,
            User.Role.RECEPTIONIST,
            User.Role.ADMIN,
        }

        if user.role not in allowed_roles:
            raise serializers.ValidationError(
                "You are not allowed to create appointments."
            )

        availability = attrs["availability"]
        doctor = attrs["doctor"]
        appointment_date = attrs["appointment_date"]
        start_time = attrs["start_time"]

        if doctor.role != User.Role.DOCTOR or not doctor.is_active:
            raise serializers.ValidationError({
                "doctor": "Select a valid, active doctor."
            })

        if availability.doctor_id != doctor.id:
            raise serializers.ValidationError({
                "availability": "This availability belongs to another doctor."
            })

        if not availability.is_available:
            raise serializers.ValidationError({
                "availability": "This availability is closed."
            })

        if availability.date != appointment_date:
            raise serializers.ValidationError({
                "appointment_date": (
                    "The date does not match the doctor's availability."
                )
            })

        if appointment_date < timezone.localdate():
            raise serializers.ValidationError({
                "appointment_date": "Past appointments cannot be booked."
            })

        slot_minutes = availability.slot_duration

        if slot_minutes <= 0:
            raise serializers.ValidationError({
                "availability": "The slot duration must be positive."
            })

        start = datetime.combine(appointment_date, start_time)
        window_start = datetime.combine(
            availability.date, availability.start_time
        )
        window_end = datetime.combine(
            availability.date, availability.end_time
        )
        end = start + timedelta(minutes=slot_minutes)

        if start < window_start or end > window_end:
            raise serializers.ValidationError({
                "start_time": "The appointment is outside working hours."
            })

        elapsed_minutes = int(
            (start - window_start).total_seconds() // 60
        )

        if elapsed_minutes % slot_minutes != 0:
            raise serializers.ValidationError({
                "start_time": "Choose a valid appointment slot."
            })

        if appointment_date == timezone.localdate():
            current_time = timezone.localtime().time().replace(tzinfo=None)

            if start_time <= current_time:
                raise serializers.ValidationError({
                    "start_time": "Choose a future appointment time."
                })

        patient = user

        if user.role in {
            User.Role.RECEPTIONIST,
            User.Role.ADMIN,
        }:
            patient_id = self.initial_data.get("patient")

            if not patient_id:
                raise serializers.ValidationError({
                    "patient": "Select a patient for this booking."
                })

            try:
                patient = User.objects.get(
                    pk=patient_id,
                    role=User.Role.PATIENT,
                    is_active=True,
                )
            except (User.DoesNotExist, ValueError, TypeError):
                raise serializers.ValidationError({
                    "patient": "Select a valid, active patient."
                })

        if not patient.is_active:
            raise serializers.ValidationError({
                "patient": "This patient account is inactive."
            })

        excluded_statuses = [
            Appointment.Status.CANCELLED,
            Appointment.Status.NO_SHOW,
        ]

        doctor_conflicts = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
        ).exclude(
            status__in=excluded_statuses
        ).filter(
            start_time__lt=end.time(),
            end_time__gt=start_time,
        )

        if doctor_conflicts.exists():
            raise serializers.ValidationError({
                "start_time": (
                    "This doctor's appointment slot is already booked."
                )
            })

        patient_conflicts = Appointment.objects.filter(
            patient=patient,
            appointment_date=appointment_date,
        ).exclude(
            status__in=excluded_statuses
        ).filter(
            start_time__lt=end.time(),
            end_time__gt=start_time,
        )

        if patient_conflicts.exists():
            raise serializers.ValidationError({
                "start_time": (
                    "You already have an appointment during this time."
                )
            })

        attrs["patient"] = patient
        attrs["end_time"] = end.time()

        return attrs
