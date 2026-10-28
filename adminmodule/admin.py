from django.contrib import admin
from .models import Staff, Role, DoctorDetails

# Register your models here.
admin.site.register(Staff)
admin.site.register(Role)


@admin.register(DoctorDetails)
class DoctorDetailsAdmin(admin.ModelAdmin):

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "doctor":
            kwargs["queryset"] = Staff.objects.filter(
                roleid__title__iexact="Doctor"
            )

        return super().formfield_for_foreignkey(
            db_field, request, **kwargs
        )