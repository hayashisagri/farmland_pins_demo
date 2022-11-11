from django.contrib.gis import admin
from japan.models import JapanPolygon

admin.site.register(JapanPolygon, admin.OSMGeoAdmin)
