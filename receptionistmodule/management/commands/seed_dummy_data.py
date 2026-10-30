from datetime import date, time
from decimal import Decimal
from django.core.management.base import BaseCommand
from adminmodule.models import Role, Staff, Weekday, DoctorDetails, Fee


def make_staff(username, role, full_name, phone):
    if Staff.objects.filter(username=username).exists():
        return Staff.objects.get(username=username)
    return Staff.objects.create_user(
        username=username, password="Test@1234",
        email=f"{username}@caredesk.com", roleid=role,
        full_name=full_name, dob=date(1990, 1, 1), phone=phone,
        gender="Female", address="Kochi", doj=date(2024, 1, 1),
        salary=Decimal("30000"),
    )


class Command(BaseCommand):
    help = "Create dummy roles, staff, doctors and fee settings for testing"

    def handle(self, *args, **options):
        roles = {t: Role.objects.get_or_create(title=t)[0]
                for t in ["Administrator", "Doctor", "Receptionist", "Pharmacist", "Lab Technician"]}

        days = {d: Weekday.objects.get_or_create(name=d)[0] for d in
                ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"]}

        make_staff("reception1", roles["Receptionist"], "Anu Receptionist", "9000000001")

        doctors = [
            ("doc_arun", "Arun Kumar", "9000000002", "Cardiology", "500",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], time(9), time(13)),
            ("doc_meera", "Meera Nair", "9000000003", "General Medicine", "300",
            ["Monday", "Wednesday", "Friday"], time(10), time(16)),
        ]
        for uname, name, phone, spec, fee, wd, start, end in doctors:
            staff = make_staff(uname, roles["Doctor"], name, phone)
            details, _ = DoctorDetails.objects.get_or_create(
                doctor=staff,
                defaults=dict(start_time=start, end_time=end,
                            consultation_fees=Decimal(fee), specialization=spec))
            details.weekdays.set([days[d] for d in wd])

        if not Fee.objects.exists():
            Fee.objects.create(discounts=Decimal("10.00"), tax=Decimal("5.00"))

        self.stdout.write(self.style.SUCCESS("Dummy data ready. Password for all: Test@1234"))