from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from decimal import Decimal, ROUND_HALF_UP
from adminmodule.models import Billing, Prescription, PrescriptionMedicine, PrescriptionTest, Fee
from adminmodule.models import ActivityLog, Appointment, Patient, DoctorDetails

# Receptionist business rules for registration, appointment booking, and billing.
# These service functions implement the authorization and validation rules before writes happen.


def _require_receptionist(user):
    """Ensure that the caller is an authenticated receptionist."""
    role = getattr(user, "roleid", None)
    if not user.is_authenticated or role is None or role.title != "Receptionist":
        raise PermissionDenied("Not allowed. Required role: Receptionist.")


def _log(staff, action, details):
    """Persist a readable activity log for receptionist actions."""
    ActivityLog.objects.create(staff=staff, message=f"{action} {details}")


def _locked_patient(patient_id):
    """Lock the patient record during updates so concurrent edits are prevented."""
    try:
        return Patient.objects.select_for_update().get(pk=patient_id)
    except Patient.DoesNotExist:
        raise NotFound("Patient not found.")


def register_patient(user, *, full_name, dob, gender, blood_group, phone, address):
    """Register a new patient and record the audit event on success."""
    _require_receptionist(user)
    with transaction.atomic():
        if Patient.objects.filter(full_name__iexact=full_name, phone=phone).exists():
            raise ValidationError({"detail": "Patient already exists."})

        patient = Patient.objects.create(
            full_name=full_name, dob=dob, gender=gender,
            blood_group=blood_group, phone=phone, address=address,
        )
        _log(user, "PATIENT_ADD", f"id={patient.pk} name={patient.full_name}")
    return patient


def edit_patient(user, patient_id, **data):
    """Update editable patient fields such as phone and address."""
    _require_receptionist(user)
    with transaction.atomic():
        patient = _locked_patient(patient_id)

        if "phone" in data and Patient.objects.filter(
            full_name__iexact=patient.full_name, phone=data["phone"]
        ).exclude(pk=patient.pk).exists():
            raise ValidationError({"detail": "Patient already exists."})

        for field, value in data.items():
            setattr(patient, field, value)
        patient.save(update_fields=list(data))
        _log(user, "PATIENT_EDIT", f"id={patient.pk} fields={','.join(data)}")
    return patient


def disable_patient(user, patient_id):
    """Soft-disable a patient only if there are no waiting appointments."""
    _require_receptionist(user)
    with transaction.atomic():
        patient = _locked_patient(patient_id)

        if not patient.is_active:
            raise ValidationError({"detail": "This patient is already disabled."})

        if Appointment.objects.filter(patient=patient, prescription__isnull=True).exists():
            raise ValidationError({"detail": "This patient has appointments waiting for consultation."})

        patient.is_active = False
        patient.save(update_fields=["is_active"])
        _log(user, "PATIENT_DISABLE", f"id={patient.pk} name={patient.full_name}")
    return patient


def book_appointment(user, *, patient_id, doctor_id, appointment_date,
                    appointment_time, reason):
    """Book an appointment and use its ID as the patient token."""

    _require_receptionist(user)

    with transaction.atomic():
        patient = _locked_patient(patient_id)

        if not patient.is_active:
            raise ValidationError(
                {"detail": "Cannot book an appointment for a disabled patient."}
            )

        try:
            doctor = (
                DoctorDetails.objects
                .select_for_update()
                .select_related("doctor")
                .get(pk=doctor_id, doctor__is_active=True)
            )
        except DoctorDetails.DoesNotExist:
            raise NotFound("Active doctor not found.")

        if appointment_date < timezone.localdate():
            raise ValidationError(
                {"appointment_date": "Appointment date cannot be in the past."}
            )

        weekday = appointment_date.strftime("%A")

        if not doctor.weekdays.filter(name__iexact=weekday).exists():
            raise ValidationError(
                {"appointment_date": "Doctor is not available on this weekday."}
            )

        if not (doctor.start_time <= appointment_time < doctor.end_time):
            raise ValidationError(
                {"appointment_time": "Time is outside the doctor's working hours."}
            )

        slot_minutes = (
            appointment_time.hour * 60 + appointment_time.minute
        )

        if slot_minutes % 15 != 0:
            raise ValidationError(
                {"appointment_time": "Appointments must use 15-minute slots."}
            )

        if appointment_date == timezone.localdate():
            now = timezone.localtime().time()
            if appointment_time <= now:
                raise ValidationError(
                    {"appointment_time": "Appointment time must be in the future."}
                )

        if Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
        ).exists():
            raise ValidationError(
                {"detail": "This doctor already has an appointment at that time."}
            )

        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
        )

        _log(
            user,
            "APPOINTMENT_ADD",
            f"id={appointment.pk} patient_id={patient.pk} doctor_id={doctor.pk}",
        )

    return appointment


def generate_consultation_bill(user, appointment_id):
    """Generate the consultation bill for an appointment after treatment and testing are complete."""
    _require_receptionist(user)

    with transaction.atomic():
        try:
            appointment = Appointment.objects.select_for_update().get(
                pk=appointment_id
            )
        except Appointment.DoesNotExist:
            raise NotFound("Appointment not found.")

        try:
            prescription = Prescription.objects.select_for_update().get(
                appointment=appointment
            )
        except Prescription.DoesNotExist:
            raise ValidationError(
                {"detail": "Cannot generate a bill before consultation."}
            )

        if Billing.objects.filter(prescription=prescription).exists():
            raise ValidationError(
                {"detail": "A bill already exists for this prescription."}
            )

        medicines = list(
            PrescriptionMedicine.objects.filter(prescription=prescription)
        )
        tests = list(
            PrescriptionTest.objects.filter(prescription=prescription)
        )

        if any(item.status.strip().upper() != "ISSUED" for item in medicines):
            raise ValidationError(
                {"detail": "All prescribed medicines must be issued before billing."}
            )

        if any(item.status.strip().upper() != "DONE" for item in tests):
            raise ValidationError(
                {"detail": "All prescribed tests must be completed before billing."}
            )

        doctor_fees = appointment.doctor.consultation_fees
        medicine_total = sum(
            (item.total for item in medicines),
            Decimal("0.00"),
        )
        test_total = sum(
            (item.total for item in tests),
            Decimal("0.00"),
        )
        subtotal = medicine_total + test_total

        fee_settings = Fee.objects.first()
        if fee_settings is None:
            raise ValidationError(
                {"detail": "Billing tax configuration has not been created."}
            )

        tax_rate = fee_settings.tax
        taxable_amount = doctor_fees + subtotal
        taxes = (
            taxable_amount * tax_rate / Decimal("100")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        grand_total = (taxable_amount + taxes).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        bill = Billing.objects.create(
            prescription=prescription,
            created_by=user,
            consultation_fees=doctor_fees,
            sub_total=subtotal,
            taxes=taxes,
            discount=Decimal("0.00"),
            grand_total=grand_total,
        )

        _log(
            user,
            "BILL_GENERATED",
            f"appointment_id={appointment.pk} total={grand_total}",
        )

    return bill
