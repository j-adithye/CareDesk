from django.contrib.auth.models import AbstractUser,UserManager
from django.db import models


class Role(models.Model):
    roleid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.title


class StaffManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        role, _ = Role.objects.get_or_create(title="Admin")

        extra_fields["roleid"] = role
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return super().create_superuser(
            username=username,
            email=email,
            password=password,
            **extra_fields
        )


class Staff(AbstractUser):
    first_name = None
    last_name = None

    roleid = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="staff"
    )

    full_name = models.CharField(max_length=100)
    dob = models.DateField()
    phone = models.CharField(max_length=15)
    gender = models.CharField(
        max_length=10,
        choices=[
            ("Male", "Male"),
            ("Female", "Female"),
            ("Other", "Other"),
        ],)
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
        return self.full_name

class Weekday(models.Model):
    name = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name


class DoctorDetails(models.Model):
    doctor = models.OneToOneField(
        Staff, on_delete=models.CASCADE, primary_key=True, related_name="doctor_details"
    )
    weekdays = models.ManyToManyField(Weekday, related_name="doctors")
    start_time = models.TimeField()
    end_time = models.TimeField()
    consultation_fees = models.DecimalField(max_digits=8, decimal_places=2)
    specialization = models.CharField(max_length=100)

    def __str__(self):
        return f"Dr. {self.doctor.full_name}"


class Patient(models.Model):
    full_name = models.CharField(max_length=100)
    dob = models.DateField()
    gender = models.CharField(max_length=10)
    blood_group = models.CharField(max_length=5, blank=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name


class Appointment(models.Model):
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
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, primary_key=True, related_name="prescription"
    )
    symptoms = models.TextField()
    diagnosis = models.TextField()
    notes = models.TextField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)


class Test(models.Model):
    test_name = models.CharField(max_length=100)
    stock_left = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.test_name


class Medicine(models.Model):
    name = models.CharField(max_length=100)
    generic_name = models.CharField(max_length=100, blank=True)
    company_name = models.CharField(max_length=100, blank=True)
    strength = models.CharField(max_length=100, blank=True)    #250mg,500mg etc
    category = models.CharField(max_length=100)   # tablet or syrup etc
    stock_left = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PrescriptionMedicine(models.Model):
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="medicines"
    )
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity_alloted = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)


class PrescriptionTest(models.Model):
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="tests"
    )
    test = models.ForeignKey(Test, on_delete=models.PROTECT)
    quantity_alloted = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)


class Billing(models.Model):
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
    # standalone settings table, keep one row
    tax = models.DecimalField(max_digits=5, decimal_places=2)


class ActivityLog(models.Model):
    time = models.DateTimeField(auto_now_add=True)
    staff = models.ForeignKey(
        Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs"
    )
    message = models.TextField()