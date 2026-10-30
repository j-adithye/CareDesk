# The pharmacist module has no tables of its own.
# Medicine, PrescriptionMedicine, ActivityLog, Role and Staff are shared models
# that already live in adminmodule/models.py. Keeping a second Medicine model here
# would create a separate table that the doctor module never writes to.
