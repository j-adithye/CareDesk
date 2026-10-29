from django.db import transaction
from django.utils import timezone # tools for all-or-nothing database work
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError       # NotFound -> 404, PermissionDenied -> 403, ValidationError -> 400
from decimal import Decimal, ROUND_HALF_UP  # Provides precise monetary calculations and standard rounding.
from adminmodule.models import Billing, Prescription, PrescriptionMedicine, PrescriptionTest, Fee  # Imports the existing billing-related models.
from adminmodule.models import (
    ActivityLog,
    Appointment,
    Patient,
    DoctorDetails,
)  # shared models we read and write


def _require_receptionist(user):                    # leading _ means "helper, only used in this file"
    role = getattr(user, "roleid", None)            # get the role, or None if the user has none
    if not user.is_authenticated or role is None or role.title != "Receptionist":
        raise PermissionDenied("Not allowed. Required role: Receptionist.")   # second role check (NFR-SEC-04)


def _log(staff, action, details):
    ActivityLog.objects.create(staff=staff, message=f"{action} {details}")
    # Adds one row to the log table: who did it + a message like "PATIENT_ADD id=100001 name=..."
    # The time column fills itself automatically


def _locked_patient(patient_id):
    try:
        return Patient.objects.select_for_update().get(pk=patient_id)
        # select_for_update() locks this row until the transaction ends,
        # so nobody else can change the same patient at the same moment
    except Patient.DoesNotExist:                    # no patient with that id
        raise NotFound("Patient not found.")        # the API answers 404


def register_patient(user, *, full_name, dob, gender, blood_group, phone, address):
    # The * means everything after it MUST be passed by name, so values can't get mixed up
    _require_receptionist(user)                     # rule 1: only a receptionist
    with transaction.atomic():                      # rule 2: all or nothing; any error undoes the DB changes
        if Patient.objects.filter(full_name__iexact=full_name, phone=phone).exists():
            # iexact = same name ignoring upper/lower case; exists() = True if at least one match
            raise ValidationError({"detail": "Patient already exists."})   # FR-PAT-03

        patient = Patient.objects.create(           # save a new row in the database
            full_name=full_name, dob=dob, gender=gender,
            blood_group=blood_group, phone=phone, address=address,
        )
        _log(user, "PATIENT_ADD", f"id={patient.pk} name={patient.full_name}")
        # pk = primary key = the registration number. Logged only after the save succeeded
    return patient                                  # give the new patient back to the view


def edit_patient(user, patient_id, **data):         # **data collects extra named values into a dict
    _require_receptionist(user)
    with transaction.atomic():
        patient = _locked_patient(patient_id)       # find the patient and lock the row

        if "phone" in data and Patient.objects.filter(
            full_name__iexact=patient.full_name, phone=data["phone"]
        ).exclude(pk=patient.pk).exists():
            # If the phone is changing: does ANOTHER patient have the same name + this phone?
            # exclude(pk=...) removes the patient themselves from the check
            raise ValidationError({"detail": "Patient already exists."})

        for field, value in data.items():           # e.g. field="phone", value="9876500000"
            setattr(patient, field, value)          # set patient.phone = value (by field name)
        patient.save(update_fields=list(data))      # save ONLY the changed columns (list(data) = the keys)
        _log(user, "PATIENT_EDIT", f"id={patient.pk} fields={','.join(data)}")
    return patient


def disable_patient(user, patient_id):
    _require_receptionist(user)
    with transaction.atomic():
        patient = _locked_patient(patient_id)

        if not patient.is_active:                   # already disabled earlier
            raise ValidationError({"detail": "This patient is already disabled."})

        if Appointment.objects.filter(patient=patient, prescription__isnull=True).exists():
            # An appointment with NO prescription is "waiting for consultation".
            # prescription__isnull=True means: no Prescription row points to this appointment
            raise ValidationError({"detail": "This patient has appointments waiting for consultation."})

        patient.is_active = False                   # soft delete: hide the patient, don't erase the row
        patient.save(update_fields=["is_active"])   # save only this one column
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

        if appointment_date < date.today():
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

        if appointment_date == date.today():
            now = datetime.now().time()
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

def book_appointment(user, *, patient_id, doctor_id, appointment_date, appointment_time, reason):
    # Defines the appointment-booking function and requires arguments to be passed by name.

    _require_receptionist(user)
    # Ensures that only an authenticated receptionist can book an appointment.

    with transaction.atomic():
        # Starts a database transaction so failed bookings are not partially saved.

        patient = _locked_patient(patient_id)
        # Retrieves and locks the patient record to prevent conflicting updates.

        if not patient.is_active:
            # Checks whether the patient has been disabled.

            raise ValidationError({"patient_id": "Cannot book an appointment for a disabled patient."})
            # Rejects appointments for disabled patients.

        try:
            # Starts handling the case where the requested doctor does not exist or is inactive.

            doctor = DoctorDetails.objects.select_for_update().select_related("doctor").get(
                pk=doctor_id,
                doctor__is_active=True,
            )
            # Retrieves and locks the doctor's details and checks that the linked staff account is active.

        except DoctorDetails.DoesNotExist:
            # Handles an invalid doctor ID or an inactive doctor.

            raise NotFound("Active doctor not found.")
            # Returns a not-found error instead of creating an appointment.

        if appointment_date < timezone.localdate():
            # Checks whether the requested appointment date is before today's date.

            raise ValidationError({"appointment_date": "Appointment date cannot be in the past."})
            # Rejects appointments scheduled for a past date.

        weekday_name = appointment_date.strftime("%A")
        # Converts the appointment date into a weekday name, such as Monday.

        if not doctor.weekdays.filter(name__iexact=weekday_name).exists():
            # Checks whether the doctor works on the requested weekday.

            raise ValidationError({"appointment_date": "Doctor is not available on this weekday."})
            # Rejects appointments on the doctor's non-working days.

        if not (doctor.start_time <= appointment_time < doctor.end_time):
            # Checks whether the requested time falls within the doctor's working hours.

            raise ValidationError({"appointment_time": "Appointment time is outside working hours."})
            # Rejects appointments outside the doctor's working hours.

        total_minutes = appointment_time.hour * 60 + appointment_time.minute
        # Converts the requested time into minutes after midnight.

        if total_minutes % 15 != 0:
            # Checks whether the requested time aligns with a 15-minute clock interval.

            raise ValidationError({"appointment_time": "Appointment time must align with a 15-minute interval."})
            # Rejects times such as 10:07 or 10:22.

        current_time = timezone.localtime().time()
        # Retrieves the current local time using Django's configured timezone.

        if appointment_date == timezone.localdate() and appointment_time <= current_time:
            # Checks whether today's requested appointment time has already passed.

            raise ValidationError({"appointment_time": "Appointment time must be in the future."})
            # Rejects appointments scheduled for an earlier time today.

        if Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
        ).exists():
            # Checks whether this doctor already has an appointment at the requested date and time.

            raise ValidationError({"detail": "Doctor already has an appointment at this time."})
            # Prevents booking an occupied appointment slot.

        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
        )
        # Creates the appointment using the existing database model.

        _log(
            user,
            "APPOINTMENT_ADD",
            f"id={appointment.pk} patient_id={patient.pk} doctor_id={doctor.pk}",
        )
        # Records the successful booking in the activity log.

    return appointment
    # Returns the saved appointment; its existing primary key is the patient token.


def generate_consultation_bill(user, appointment_id):
    # Defines the function that generates a bill for an appointment.

    _require_receptionist(user)
    # Ensures that only an authenticated receptionist can generate a bill.

    with transaction.atomic():
        # Ensures that the billing operation succeeds completely or is rolled back.

        try:
            appointment = Appointment.objects.select_for_update().get(
                pk=appointment_id
            )
            # Retrieves and locks the appointment being billed.

        except Appointment.DoesNotExist:
            # Handles an appointment ID that does not exist.

            raise NotFound("Appointment not found.")
            # Returns a not-found error.

        try:
            prescription = Prescription.objects.select_for_update().get(
                appointment=appointment
            )
            # Retrieves the prescription associated with this appointment.

        except Prescription.DoesNotExist:
            # Handles appointments that have not yet been consulted.

            raise ValidationError(
                {"detail": "Cannot generate a bill before consultation."}
            )
            # Prevents billing without a prescription.

        if Billing.objects.filter(prescription=prescription).exists():
            # Checks whether a bill already exists for this prescription.

            raise ValidationError(
                {"detail": "A bill already exists for this prescription."}
            )
            # Prevents creating a duplicate bill.

        medicines = list(
            PrescriptionMedicine.objects.filter(prescription=prescription)
        )
        # Retrieves all medicine lines associated with the prescription.

        tests = list(
            PrescriptionTest.objects.filter(prescription=prescription)
        )
        # Retrieves all test lines associated with the prescription.

        if any(item.status.strip().upper() != "ISSUED" for item in medicines):
            # Checks whether every prescribed medicine has been issued.

            raise ValidationError(
                {"detail": "All prescribed medicines must be issued before billing."}
            )
            # Stops billing if any medicine has not been issued.

        if any(item.status.strip().upper() != "DONE" for item in tests):
            # Checks whether every prescribed test has been completed.

            raise ValidationError(
                {"detail": "All prescribed tests must be completed before billing."}
            )
            # Stops billing if any test has not been completed.

        doctor_fees = appointment.doctor.consultation_fees
        # Retrieves the consultation fee configured for the appointment's doctor.

        medicine_total = sum(
            (item.total for item in medicines),
            Decimal("0.00"),
        )
        # Adds the totals of all issued medicines without using floating-point arithmetic.

        test_total = sum(
            (item.total for item in tests),
            Decimal("0.00"),
        )
        # Adds the totals of all completed tests.

        subtotal = medicine_total + test_total
        # Calculates the subtotal of medicines and tests.

        fee_settings = Fee.objects.first()
        # Retrieves the existing tax configuration.

        if fee_settings is None:
            # Checks whether the tax configuration exists.

            raise ValidationError(
                {"detail": "Billing tax configuration has not been created."}
            )
            # Prevents generating a bill with an undefined tax rate.

        tax_rate = fee_settings.tax
        # Retrieves the configured tax percentage.

        taxable_amount = doctor_fees + subtotal
        # Calculates the amount on which tax will be applied.

        taxes = (
            taxable_amount * tax_rate / Decimal("100")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        # Calculates tax and rounds it to two decimal places.

        grand_total = (taxable_amount + taxes).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        # Calculates the final amount payable without deducting any discount.

        bill = Billing.objects.create(
            prescription=prescription,
            created_by=user,
            consultation_fees=doctor_fees,
            sub_total=subtotal,
            taxes=taxes,
            discount=Decimal("0.00"),
            grand_total=grand_total,
        )
        # Creates one bill using the existing Billing model and sets discount to zero.

        _log(
            user,
            "BILL_GENERATED",
            f"appointment_id={appointment.pk} total={grand_total}",
        )
        # Records the bill-generation action in the activity log.

    return bill
    # Returns the saved bill to the caller.