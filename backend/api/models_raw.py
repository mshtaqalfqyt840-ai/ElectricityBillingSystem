# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Buildings(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(unique=True, max_length=1)

    class Meta:
        managed = False
        db_table = 'buildings'


class Rooms(models.Model):
    room_number = models.IntegerField()
    building = models.ForeignKey(Buildings, models.DO_NOTHING)
    qr_code = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'rooms'
        unique_together = (('room_number', 'building'),)


class Students(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    room = models.ForeignKey(Rooms, models.DO_NOTHING)
    status = models.CharField(max_length=10)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'students'


class Users(models.Model):
    username = models.CharField(unique=True, max_length=100)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=20)
    permissions = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'


class Invoices(models.Model):
    room = models.ForeignKey(Rooms, models.DO_NOTHING)
    created_by = models.ForeignKey(Users, models.DO_NOTHING, db_column='created_by', blank=True, null=True)
    approved_by = models.ForeignKey(Users, models.DO_NOTHING, db_column='approved_by', related_name='invoices_approved_by_set', blank=True, null=True)
    reading_old = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    reading_new = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    consumption = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    previous_debt = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20)
    meter_image_url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'invoices'
