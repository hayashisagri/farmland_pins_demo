import hashlib
from pathlib import Path

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.utils import LayerMapping

from .models import JapanPolygon

japan_mapping = {
    'land_id': 'id',
    'mpoly': 'MULTIPOLYGON'
}

japan_shp = Path(__file__).resolve().parent / 'data' / 'sapporo' / '01100sapporo_2021_5.shp'
ds = DataSource(japan_shp, encoding='Shift-jis')


def run(verbose=True):
    lm = LayerMapping(JapanPolygon, ds, japan_mapping)
    lm.save(strict=True, verbose=verbose)
