import unicodedata
import requests
from japan.data import SAPPORO_POLYGONS
from django.contrib.gis.geos import Point

from django.shortcuts import render, redirect

from japan.models import JapanPolygon, FarmlandPinOriginals


def root_view(request):
    return redirect('map')


def map_view(request):
    if request.POST:
        farmland_pin_address = request.POST.get('farmland_pin_address')
        cleaned_input_address = unicodedata.normalize("NFKC", farmland_pin_address)
        farmland_pins = SAPPORO_POLYGONS
        """
        農地ピンデータについては暫定で、data.pyにそのまま保存をしている。
        入力された地番（cleaned_input_address）を使用して、data.pyのデータを検索し、
        一致した地番のオブジェクトから緯度、経度を取得している。
        実際にはRDBにデータは保管予定なので修正の必要あり。

        緯度経度の順番に注意、containsで検索できなくなる

        農地ピンの測地系 JGD2000(?) SRID4612
        筆ポリゴンの測地系 JGD2011 SRID6668

        1. 検索部分を引数で受け取り、該当するポリゴンを戻値で返す
        2. 都道府県と市区町村（オプション）、retry可能にする（再検索）
        """
        long, lat = 0.0, 0.0
        for fp in range(len(farmland_pins)):
            if cleaned_input_address in farmland_pins[fp].values():
                pin_dict = farmland_pins[fp]
                long = pin_dict['Longitude']
                lat = pin_dict['Latitude']

        pnt = Point(long, lat)
        try:
            multi_polygon = JapanPolygon.objects.get(mpoly__contains=pnt).mpoly.json
        except:
            multi_polygon = {"type": "MultiPolygon", "coordinates": [[[[0, 0], [0, 0], [0, 0]]]]}
            print('error')

        return render(
            request,
            'japan/map.html',
            {
                'lat': lat,
                'long': long,
                'address': f'"{cleaned_input_address}"',
                'coordinates': multi_polygon,
            }
        )

    return render(
        request,
        'japan/map.html'
    )


# wagriの会員IDとパスワードからapi用の認証トークンを取得
def get_wagri_auth_token():
    auth_url = 'https://api.wagri.net/Token'
    wagri_id = 'askme'
    auth_token = requests.post(auth_url, wagri_id).json()['access_token']
    return auth_token


# 市町村コードから農地ピンを取得する
def get_farmland_pins_by_city_code(city_code, auth_token):
    wagri_url = f"https://api.wagri.net/API/Public/AgriculturalLand/SearchByCityCode?CityCode={city_code}"
    headers = {'X-Authorization': auth_token}
    farmland_pins = requests.get(wagri_url, headers=headers).json()
    return farmland_pins


# wagriから取得した農地ピンをマスターテーブルに保存する
# shellで中身を一行ずつ読み込んだら動くのに関数を呼んだらエラーになる、なぜ。。。pin = farmland_pins[i]
# TypeError: 'list' object is not callable
def load_farmland_pins():
    # auth_token = get_wagri_auth_token()
    # city_code = 000000
    farmland_pins = SAPPORO_POLYGONS
    objs = []
    for i in range(len(farmland_pins)):
        pin = farmland_pins[i]
        obj = FarmlandPinOriginals(
            city_code=pin['CityCode'],
            latitude=pin['Latitude'],
            longitude=pin['Longitude'],
            address=pin['Address'],
        )
        objs.append(obj)

    FarmlandPinOriginals.objects.bulk_create(objs)


# 住所などから農地ピンを取得する
def get_farmland_pins_by_address(prefecture, city, address):
    if address:
        try:
            pin = FarmlandPinOriginals.objects.filter(address='北海道札幌市北区新川743-3')
            return pin
        except:
            print('invalid value is given')
    elif city:
        try:
            pins = FarmlandPinOriginals.objects.filter(address__contains=city)
            return pins
        except:
            print('invalid value is given')
    elif prefecture:
        try:
            pins = FarmlandPinOriginals.objects.filter(address__contains=prefecture)
            return pins
        except:
            print('invalid value is given')
    raise  # 例外処理


# 農地ピンのリストをキーに、ポリゴンのリストを取得する
def get_polygons_by_farmland_pins():
    search_input = 'sample address'  # 検索ワード、都道府県名や住所など
    pins = get_farmland_pins_by_address(prefecture='', city='', address=search_input)
    polygons = []
    for pin in pins:
        polygon = get_polygon_by_farmland_pin(pin)
        polygons.append(polygon)
    return polygons


# 個別の農地ピンをキーに個別のポリゴンを取得する
def get_polygon_by_farmland_pin(pin):
    # Decimal('43.04352666500010116')
    # 緯度経度のみを取り出して、座標として設定する方法がわからない
    # pnt = Point(pnt.longitude, pnt.latitude)
    # TypeError: Invalid parameters given for Point initialization.
    pnt = Point(pin.longitude, pin.latitude)
    polygon = JapanPolygon.objects.get(mpoly__contains=pnt).mpoly.json
    return polygon
