from rest_framework import serializers
from adminmodule.models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Appointment
        fields = '__all__'
        
        
