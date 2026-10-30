from datetime import date, time
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from adminmodule.models import (
    ActivityLog, Appointment, DoctorDetails, Medicine, Patient,
    Prescription, PrescriptionMedicine, Role, Staff,
)


def make_staff(username, role_title, **extra):
    role, _ = Role.objects.get_or_create(title=role_title)
    return Staff.objects.create_user(
        username=username, password="secret123", email=f"{username}@example.com",
        roleid=role, full_name=f"Test {username}", dob=date(1990, 1, 1), phone="9876543210",
        gender="F", address="Test address", doj=date(2020, 1, 1), salary=Decimal("1000.00"), **extra,
    )


class PharmacistApiTests(APITestCase):
    def setUp(self):
        self.pharmacist = make_staff("pharm01", "Pharmacist")
        self.client.force_authenticate(self.pharmacist)
        self.list_url = reverse("pharmacist-medicine-list")

    def new_medicine(self, name="Paracetamol", company="Acme", stock=0, price="12.50", active=True):
        return Medicine.objects.create(
            name=name, generic_name=name, company_name=company,
            stock_left=stock, unit_price=Decimal(price), is_active=active,
        )

    def new_line(self, medicine, qty=5, status="PENDING"):
        doctor = make_staff("doc001", "Doctor")
        details = DoctorDetails.objects.create(
            doctor=doctor, start_time=time(9), end_time=time(17),
            consultation_fees=Decimal("300.00"), specialization="General",
        )
        patient = Patient.objects.create(
            full_name="Pat Ient", dob=date(1985, 5, 5), gender="M", phone="9123456780", address="x",
        )
        appt = Appointment.objects.create(
            doctor=details, patient=patient, appointment_date=date(2026, 10, 28),
            appointment_time=time(10), reason="Fever",
        )
        rx = Prescription.objects.create(appointment=appt, symptoms="Fever", diagnosis="Flu")
        return PrescriptionMedicine.objects.create(
            prescription=rx, medicine=medicine, quantity_alloted=qty,
            unit_price=medicine.unit_price, total=medicine.unit_price * qty, status=status,
        )

    # ---- access control
    def test_anonymous_is_refused(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.list_url).status_code, (401, 403))

    def test_other_roles_are_refused(self):
        self.client.force_authenticate(make_staff("recep01", "Receptionist"))
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    # ---- add medicine
    def test_add_medicine_starts_with_zero_stock_and_logs(self):
        body = {"name": "Amoxicillin", "generic_name": "Amoxicillin", "company_name": "Acme", "unit_price": "8.00"}
        r = self.client.post(self.list_url, body, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["stock_left"], 0)
        self.assertTrue(ActivityLog.objects.filter(message__startswith="MEDICINE_ADD", staff=self.pharmacist).exists())

    def test_client_cannot_set_stock(self):
        body = {"name": "Amoxicillin", "generic_name": "A", "company_name": "Acme", "unit_price": "8.00", "stock_left": 99}
        r = self.client.post(self.list_url, body, format="json")
        self.assertEqual(r.data["stock_left"], 0)

    def test_add_medicine_validation(self):
        base = {"name": "Amoxicillin", "generic_name": "A", "company_name": "Acme", "unit_price": "8.00"}
        for change in ({"name": "ab"}, {"unit_price": "0"}, {"unit_price": "-1"},
                       {"generic_name": ""}, {"company_name": ""}):
            r = self.client.post(self.list_url, {**base, **change}, format="json")
            self.assertEqual(r.status_code, 400, change)

    def test_duplicate_name_and_company_rejected(self):
        self.new_medicine("Paracetamol", "Acme")
        body = {"name": "paracetamol", "generic_name": "P", "company_name": "ACME", "unit_price": "5.00"}
        self.assertEqual(self.client.post(self.list_url, body, format="json").status_code, 400)

    # ---- list / search / disable
    def test_list_search_by_name_and_code(self):
        a = self.new_medicine("Paracetamol")
        self.new_medicine("Ibuprofen")
        by_name = self.client.get(self.list_url, {"search": "para"}).data
        self.assertEqual([m["id"] for m in by_name], [a.pk])
        by_code = self.client.get(self.list_url, {"search": str(a.pk)}).data
        self.assertIn(a.pk, [m["id"] for m in by_code])

    def test_disable_is_soft_and_hidden_from_list(self):
        m = self.new_medicine()
        r = self.client.delete(reverse("pharmacist-medicine-detail", args=[m.pk]))
        self.assertEqual(r.status_code, 200)
        m.refresh_from_db()
        self.assertFalse(m.is_active)
        self.assertEqual(self.client.get(self.list_url).data, [])
        self.assertTrue(ActivityLog.objects.filter(message__startswith="MEDICINE_DISABLE").exists())

    def test_price_and_stock_cannot_be_edited(self):
        m = self.new_medicine()
        url = reverse("pharmacist-medicine-detail", args=[m.pk])
        self.assertEqual(self.client.patch(url, {"unit_price": "1.00"}, format="json").status_code, 405)
        self.assertEqual(self.client.put(url, {"stock_left": 50}, format="json").status_code, 405)

    # ---- add stock
    def test_add_stock(self):
        m = self.new_medicine(stock=3)
        url = reverse("pharmacist-medicine-add-stock", args=[m.pk])
        r = self.client.post(url, {"quantity": 7}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        m.refresh_from_db()
        self.assertEqual(m.stock_left, 10)
        self.assertTrue(ActivityLog.objects.filter(message__startswith="MEDICINE_STOCK_ADD").exists())

    def test_add_stock_rejects_bad_quantity_and_disabled_medicine(self):
        m = self.new_medicine()
        url = reverse("pharmacist-medicine-add-stock", args=[m.pk])
        for bad in (0, -5, 2.5, "abc", None):
            self.assertEqual(self.client.post(url, {"quantity": bad}, format="json").status_code, 400, bad)
        m.is_active = False
        m.save()
        self.assertEqual(self.client.post(url, {"quantity": 5}, format="json").status_code, 400)

    # ---- issue
    def test_pending_list_shows_patient_doctor_quantity_and_stock(self):
        m = self.new_medicine(stock=2)
        self.new_line(m, qty=5)
        row = self.client.get(reverse("pharmacist-line-list")).data[0]
        self.assertEqual(row["patient_name"], "Pat Ient")
        self.assertEqual(row["quantity_required"], 5)
        self.assertEqual(row["current_stock"], 2)

    def test_issue_reduces_stock_and_marks_issued(self):
        m = self.new_medicine(stock=10)
        line = self.new_line(m, qty=4)
        r = self.client.post(reverse("pharmacist-line-issue", args=[line.pk]))
        self.assertEqual(r.status_code, 200, r.data)
        m.refresh_from_db()
        line.refresh_from_db()
        self.assertEqual(m.stock_left, 6)
        self.assertEqual(line.status, "ISSUED")
        self.assertTrue(ActivityLog.objects.filter(message__startswith="MEDICINE_ISSUE").exists())

    def test_issue_with_too_little_stock_stays_pending(self):
        m = self.new_medicine(stock=2)
        line = self.new_line(m, qty=5)
        r = self.client.post(reverse("pharmacist-line-issue", args=[line.pk]))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["detail"], "Not enough stock. Add stock first.")
        m.refresh_from_db()
        line.refresh_from_db()
        self.assertEqual((m.stock_left, line.status), (2, "PENDING"))

    def test_line_is_never_issued_twice(self):
        m = self.new_medicine(stock=10)
        line = self.new_line(m, qty=4)
        url = reverse("pharmacist-line-issue", args=[line.pk])
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 400)
        m.refresh_from_db()
        self.assertEqual(m.stock_left, 6)

    def test_issue_unknown_line_is_404(self):
        self.assertEqual(self.client.post(reverse("pharmacist-line-issue", args=[99999])).status_code, 404)
