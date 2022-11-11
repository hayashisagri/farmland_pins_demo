from django.contrib.gis.db import models


class JapanPolygon(models.Model):
    land_id = models.CharField('id', max_length=50)
    mpoly = models.MultiPolygonField(srid=4326)

# class FarmlandPins(models.Model):


class FarmlandPinOriginals(models.Model):

    city_code = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=20, decimal_places=17)
    longitude = models.DecimalField(max_digits=20, decimal_places=17)
    address = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "farmland_pin_originals"
