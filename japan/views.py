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
    wagri_id = 'grant_type=client_credentials&client_id=fcb04d4d-72da-4965-8076-f655ebb7f966&client_secret=SAgri2018'
    auth_token = requests.post(auth_url, wagri_id).json()['access_token']
    return auth_token


# 市町村コードから農地ピンを取得する
def get_farmland_pins_by_city_code(city_code, auth_token):
    wagri_url = f"https://api.wagri.net/API/Public/AgriculturalLand/SearchByCityCode?CityCode={city_code}"
    headers = {'X-Authorization': auth_token}
    farmland_pins = requests.get(wagri_url, headers=headers).json()
    return farmland_pins


# wagriから取得した農地ピンをマスターテーブルに保存する
def load_farmland_pins():
    auth_token = get_wagri_auth_token()
    city_code = 000000
    farmland_pins = get_farmland_pins_by_city_code(city_code, auth_token)
    objs = []
    for i in range(len(farmland_pins)):
        pin = farmland_pins(i)
        obj = FarmlandPinOriginals(
            city_code=pin['city_code'],
            latitude=pin['latitude'],
            longitude=pin['longitude'],
            address=pin['address'],
        )
        objs.append(obj)

    FarmlandPinOriginals.objects.bulk_create(objs)


# 住所などから農地ピンを取得する
def get_farmland_pins_by_address():
    return


# 農地ピンのリストをキーに、ポリゴンのリストを取得する
def get_polygons_by_farmland_pins():
    polygons = []
    polygon = get_polygon_by_farmland_pin()
    polygons.append(polygon)
    return


# 個別の農地ピンをキーに個別のポリゴンを取得する
def get_polygon_by_farmland_pin(pin):
    polygon = ピンからポリゴンを検索
    return polygon
