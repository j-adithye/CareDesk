from rest_framework import serializers
from .models import Staff
from datetime import date
import re

class StaffSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Staff
        exclude = ['groups', 'user_permissions']
        
    def validate_full_name(self, value):
        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Name must contain at least 2 characters."
            )

        if not re.fullmatch(r"[A-Za-z ]+", value):
            raise serializers.ValidationError(
                "Name can contain only alphabets and spaces."
            )

        return value
        
    def validate_phone(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError(
                "Phone number must contain exactly 10 digits."
            )
        return value

    def validate_gender(self, value):
        allowed_genders = ["Male", "Female", "Other"]

        if value not in allowed_genders:
            raise serializers.ValidationError(
                "Gender must be Male, Female, or Other."
            )
        return value

    def validate_dob(self, value):
        if value > date.today():
            raise serializers.ValidationError(
                "Date of birth cannot be in the future."
            )
        return value

    def validate_doj(self, value):
        if value > date.today():
            raise serializers.ValidationError(
                "Date of joining cannot be in the future."
            )
        return value

    def validate_salary(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Salary cannot be negative."
            )
        return value

    def validate(self, attrs):
        dob = attrs.get("dob")
        doj = attrs.get("doj")

        # For partial updates, use the existing values if not supplied.
        if self.instance:
            dob = dob or self.instance.dob
            doj = doj or self.instance.doj

        if dob and doj:
            if doj < dob:
                raise serializers.ValidationError({
                    "doj": "Date of joining cannot be before date of birth."
                })

            # Calculate age on the joining date.
            age = doj.year - dob.year - (
                (doj.month, doj.day) < (dob.month, dob.day)
            )

            if not 18 <= age <= 65:
                raise serializers.ValidationError({
                    "dob": "Staff must be between 18 and 65 years old on the date of joining."
                })

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        staff = Staff(**validated_data)
        staff.set_password(password)
        staff.save()
        return staff

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance
