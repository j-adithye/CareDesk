from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

# Shared clinic domain models used across the project.
# These models store staff, patient, appointment, pharmacy, billing, and audit-trail data.


class Role(models.Model):
    """Represents one staff role such as Admin, Doctor, or Pharmacist."""

    roleid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=10, unique=True)

    def __str__(self):
        """Return the readable role label."""
        return self.title


class StaffManager(UserManager):
    """Custom manager that assigns a default role and auth flags for staff creation."""

    def create_superuser(self, username, email=None, **extra_fields):
        """Create a superuser and associate it with the default admin role."""
        role, _ = Role.objects.get_or_create(title="Admin")

        extra_fields["roleid"] = role
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return super().create_superuser(
            username=username,
            email=email,
            **extra_fields
        )


class Staff(AbstractUser):
    """Main system user model for authentication and employee records."""

    first_name = None
    last_name = None

    roleid = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="staff"
    )

    full_name = models.CharField(max_length=30)
    dob = models.DateField()
    phone = models.CharField(max_length=10)
    gender = models.CharField(
        max_length=10,
        choices=[
            ("Male", "Male"),
            ("Female", "Female"),
            ("Other", "Other"),
        ],
    )
    address = models.TextField()
    doj = models.DateField()
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    REQUIRED_FIELDS = [
        "email",
        "full_name",
        "dob",
        "phone",
        "gender",
        "address",
        "doj",
        "salary",
    ]

    objects = StaffManager()

    def __str__(self):
        """Return the staff member's full name in admin and logs."""
        return self.full_name


class Weekday(models.Model):
    """List of weekdays on which a doctor is available."""

    name = models.CharField(max_length=10, unique=True)

    def __str__(self):
        """Return the weekday label."""
        return self.name


class DoctorDetails(models.Model):
    """Doctor-specific schedule and pricing information linked to a staff record."""

    doctor = models.OneToOneField(
        Staff, on_delete=models.CASCADE, primary_key=True, related_name="doctor_details"
    )
    weekdays = models.ManyToManyField(Weekday, related_name="doctors")
    start_time = models.TimeField()
    end_time = models.TimeField()
    consultation_fees = models.DecimalField(max_digits=8, decimal_places=2)
    specialization = models.CharField(max_length=40)

    def __str__(self):
        """Return a readable doctor name with title prefix."""
        return f"Dr. {self.doctor.full_name}"


class Patient(models.Model):
    """Patient profile information collected during registration."""

    full_name = models.CharField(max_length=40)
    dob = models.DateField()
    gender = models.CharField(max_length=10)
    blood_group = models.CharField(max_length=5, blank=True)
    phone = models.CharField(max_length=10)
    address = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        """Return the patient name for admin and API display."""
        return self.full_name


class Appointment(models.Model):
    """A booked consultation slot with a doctor and patient."""

    doctor = models.ForeignKey(
        DoctorDetails, on_delete=models.PROTECT, related_name="appointments"
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.PROTECT, related_name="appointments"
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)


class Prescription(models.Model):
    """Clinical record connected to a single appointment."""

    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, primary_key=True, related_name="prescription"
    )
    symptoms = models.TextField()
    diagnosis = models.TextField()
    notes = models.TextField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)


class Test(models.Model):
    """Lab test catalog item available for prescription and result entry."""

    test_name = models.CharField(max_length=40)
    stock_left = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        """Return the test name for display."""
        return self.test_name


class Medicine(models.Model):
    """Medicine catalog used by pharmacy workflows and prescriptions."""

    name = models.CharField(max_length=40)
    generic_name = models.CharField(max_length=40, blank=True)
    company_name = models.CharField(max_length=40, blank=True)
    strength = models.CharField(max_length=40, blank=True)    # 250mg, 500mg etc.
    category = models.CharField(max_length=40)   # tablet or syrup etc.
    stock_left = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        """Return the medicine name."""
        return self.name


class PrescriptionMedicine(models.Model):
    """One medicine item attached to a prescription order."""

    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="medicines"
    )
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity_alloted = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)


class PrescriptionTest(models.Model):
    """One lab test entry attached to a prescription."""

    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="tests"
    )
    test = models.ForeignKey(Test, on_delete=models.PROTECT)
    quantity_alloted = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)


class Billing(models.Model):
    """Generated billing information linked to a completed prescription."""

    prescription = models.OneToOneField(
        Prescription, on_delete=models.PROTECT, primary_key=True, related_name="billing"
    )
    created_by = models.ForeignKey(
        Staff, on_delete=models.PROTECT, related_name="bills_created"
    )
    consultation_fees = models.DecimalField(max_digits=8, decimal_places=2)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2)
    taxes = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)
    created_on = models.DateTimeField(auto_now_add=True)
    paid_on = models.DateTimeField(null=True, blank=True)


class Fee(models.Model):
    """System configuration row for tax and related billing settings."""

    # Standalone settings table; keep only one row for billing configuration.
    tax = models.DecimalField(max_digits=5, decimal_places=2)


class ActivityLog(models.Model):
    """Audit trail for key operator actions recorded across the system."""

    time = models.DateTimeField(auto_now_add=True)
    staff = models.ForeignKey(
        Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs"
    )
    message = models.TextField()
