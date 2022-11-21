import logging

import requests

from django.contrib.gis.geos import GEOSGeometry

from japan.models import JapanPolygon, FarmlandPinOriginals

LOGGER = logging.getLogger('django')

PREFECTURES_MASTER = (
    ('北海道', '01'),
    ('青森県', '02'),
    ('岩手県', '03'),
    ('宮城県', '04'),
    ('秋田県', '05'),
    ('山形県', '06'),
    ('福島県', '07'),
    ('茨城県', '08'),
    ('栃木県', '09'),
    ('群馬県', '10'),
    ('埼玉県', '11'),
    ('千葉県', '12'),
    ('東京都', '13'),
    ('神奈川県', '14'),
    ('新潟県', '15'),
    ('富山県', '16'),
    ('石川県', '17'),
    ('福井県', '18'),
    ('山梨県', '19'),
    ('長野県', '20'),
    ('岐阜県', '21'),
    ('静岡県', '22'),
    ('愛知県', '23'),
    ('三重県', '24'),
    ('滋賀県', '25'),
    ('京都府', '26'),
    ('大阪府', '27'),
    ('兵庫県', '28'),
    ('奈良県', '29'),
    ('和歌山県', '30'),
    ('鳥取県', '31'),
    ('島根県', '32'),
    ('岡山県', '33'),
    ('広島県', '34'),
    ('山口県', '35'),
    ('徳島県', '36'),
    ('香川県', '37'),
    ('愛媛県', '38'),
    ('高知県', '39'),
    ('福岡県', '40'),
    ('佐賀県', '41'),
    ('長崎県', '42'),
    ('熊本県', '43'),
    ('大分県', '44'),
    ('宮崎県', '45'),
    ('鹿児島県', '46'),
    ('沖縄県', '47')
)


class Wagri:
    AUTH_URL = 'https://api.wagri.net/Token'
    WAGRI_ID = 'grant_type=client_credentials&client_id=fcb04d4d-72da-4965-8076-f655ebb7f966&client_secret=SAgri2018'
    WAGRI_URL = "https://api.wagri.net/API/Public/AgriculturalLand/SearchByCityCode?CityCode=011002"

    def get_wagri_auth_token(self) -> str:
        """
        :return: 会員情報に基づきapi認証用のトークンを返却する（有効期限12時間）
        """
        auth_token = requests.post(self.AUTH_URL, self.WAGRI_ID).json()['access_token']
        return auth_token

    def get_farmland_pins_by_city_code(self, city_code: str, auth_token: str) -> str:
        """
        :param city_code: 6桁の市区町村コード
        :param auth_token: wagriの認証トークン
        :return: 指定の市区町村の農地ピン情報を返却
        """
        headers = {'X-Authorization': auth_token}
        farmland_pins = requests.get(self.WAGRI_URL, headers=headers).json()
        return farmland_pins

    def load_farmland_pins(self, auth_token: str, city_code: str):
        """
        :param auth_token: wagriの認証トークン
        :param city_code: 6桁の市区町村コード
        :return:
        """
        farmland_pins = Wagri.get_farmland_pins_by_city_code(city_code, auth_token)
        objs = []
        for pin in farmland_pins:
            prefecture, address = Wagri.strip_prefecture_from_pin_address(pin)
            pnt = GEOSGeometry(f"POINT({pin['Longitude']} {pin['Latitude']})")
            obj = FarmlandPinOriginals(
                city_code=pin['CityCode'],
                prefecture=prefecture,
                address=address,
                point=pnt,
            )
            objs.append(obj)

        FarmlandPinOriginals.objects.bulk_create(objs)

    def strip_prefecture_from_pin_address(self, pin: dict):
        """
        :param pin: wagriから取得した農地ピン情報
        :return: 農地ピン情報のaddressから都道府県名とそれ以外を分けて返却
        """
        prefecture_code = pin['CityCode'][:2]
        prefecture = ''
        original_address = pin['Address']
        for p in PREFECTURES_MASTER:
            if prefecture_code == p[1]:
                prefecture = p[0]
        address = original_address.removeprefix(prefecture)
        return prefecture, address


class FarmlandPins:

    def search_farmland_pins(self, prefecture: str, address: str) -> list | None:
        """
        :param prefecture: 都道府県名
        :param address: 住所（地番）
        :return: あいまい検索でヒットした農地ピンのリストを返却
        """
        try:
            pins = FarmlandPinOriginals.objects.filter(prefecture__contains=prefecture, address__contains=address)
            return pins
        except:
            message = f"unexpected input value. value: {prefecture, address}"
            LOGGER.error(message)
            return None

    def search_farmland_pin(self, address: str):
        """
        :param address: 住所（地番）
        :return: 完全一致する農地ピンを返却
        """
        try:
            pin = FarmlandPinOriginals.objects.get(address=address)
            return pin
        except:
            message = f"unexpected input value. value: {address}"
            LOGGER.error(message)
            return None

    def get_polygons_by_farmland_pins(self, pins: list) -> list:
        """
        :param pins: 農地ピンのリスト
        :return: 農地ピンと重なるポリゴンのリスト
        """
        polygons = []
        for pin in pins:
            try:
                polygon = JapanPolygon.objects.get(mpoly__contains=pin.point).mpoly.json
                polygons.append(polygon)
            except:
                message = f"matching polygon does not exist. farmland_pin_originals id:{pin.id} address:{pin.address}"
                LOGGER.info(message)
        return polygons

    def get_polygon_by_farmland_pin(self, pin):
        """
        :param pin: 単体の農地ピン情報
        :return: 農地ピンと重なる単体のポリゴン
        """
        polygon = JapanPolygon.objects.get(mpoly__contains=pin.point).mpoly.json
        return polygon

    def get_pins_by_distance(self, polygon: str, distance: float):
        """
        :param polygon: ポリゴン
        :param distance: ポリゴンの中心からの距離（半径）メートル
        :return: 距離以内の農地ピンリスト
        """
        distance_limit = 5000  # todo: どこまでの距離を検索対象として許可するか要検討
        if distance >= distance_limit:
            message = f"distance is too large. must be smaller than {distance_limit}"
            LOGGER.error(message)
            return None
        pnt_center = GEOSGeometry(polygon).centroid
        pins = FarmlandPinOriginals.objects.filter(point__dwithin=(pnt_center, distance))
        return pins


# 農地ピンのサンプル（不要な要素は落としています）
pin_sample = [
    {
        "CityCode": "462136",
        "Latitude": 30.7009760660001,
        "Longitude": 131.065587658,
        "Address": "北海道札幌市中央区盤渓279-4",
    },
    {
        "CityCode": "462136",
        "Latitude": 30.6804379820001,
        "Longitude": 131.051926976,
        "Address": "北海道札幌市中央区盤渓279-8",
    }
]

# メソッド呼び出しサンプル
Wagri.get_wagri_auth_token()
Wagri.get_farmland_pins_by_city_code('010101', 'トークン')
Wagri.load_farmland_pins('010101', 'トークン')
FarmlandPins.strip_prefecture_from_pin_address(pin_sample[0])
# prefecture='北海道', address='札幌市中央区盤渓279-4'

FarmlandPins.search_farmland_pins(prefecture='北海', address='盤渓')
# [<FarmlandPinOriginals: FarmlandPinOriginals object (1)>, <FarmlandPinOriginals: FarmlandPinOriginals object (2)>, ....]

FarmlandPins.search_farmland_pin(address='札幌市中央区盤渓279-4')
# [<FarmlandPinOriginals: FarmlandPinOriginals object (1)>]

FarmlandPins.get_polygons_by_farmland_pins(
    pins='[<FarmlandPinOriginals: FarmlandPinOriginals object (1)>, <FarmlandPinOriginals: FarmlandPinOriginals object (2)>, .....]')
# ['{ "type": "MultiPolygon", "coordinates": [ [ [ [ 141.258993790830999, 43.043309390616102 ], [ 141.258974796249987, 43.043334142656697 ], [ 141.258902917036011, 43.043398084454203 ] ] ] ] }']

FarmlandPins.get_polygon_by_farmland_pin(pin='<FarmlandPinOriginals: FarmlandPinOriginals object (1)>')
# '{ "type": "MultiPolygon", "coordinates": [ [ [ [ 141.258993790830999, 43.043309390616102 ], [ 141.258974796249987, 43.043334142656697 ], [ 141.258902917036011, 43.043398084454203 ]......}'

FarmlandPins.get_pins_by_distance(
    polygon='{ "type": "MultiPolygon", "coordinates": [ [ [ [ 141.258993790830999, 43.043309390616102 ]....',
    distance=1000)
# [<FarmlandPinOriginals: FarmlandPinOriginals object (1)>, <FarmlandPinOriginals: FarmlandPinOriginals object (2)>, ....]
