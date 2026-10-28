from django.db import transaction                   # tools for all-or-nothing database work
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
                                                    # NotFound -> 404, PermissionDenied -> 403, ValidationError -> 400

from adminmodule.models import ActivityLog, Appointment, Patient   # shared models we read and write


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
