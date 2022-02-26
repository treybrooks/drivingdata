from datetime import datetime
import urllib
import json
import scrapy
from scrapy.http import JsonRequest
from scrapy.loader import ItemLoader
from drivingdata.items import CarItem

def getn(d, path, default=None):
    for p in path:
        if p not in d:
            return default
        d = d[p]
    return d

class AudiSpider(scrapy.Spider):
    name = 'audi'
    allowed_domains = ['audi.com.au']
    BASE_URL = 'https://scs.audi.de/api/v2/search/filter/auuc/en'
    external_hosting_url = 'https://drivingdata.com.au/facebook/audi-v2/images'
    max_images = 5

    def start_requests(self):
        size = 100
        def build_request(start_index):
            svd = datetime.now().strftime("svd-%Y-%m-%dt%H_%M_%S_063-7")
            params = {
                'svd': svd,
                'from': start_index,
                'size': size
            }
            url = f'{self.BASE_URL}?{urllib.parse.urlencode(params)}'
            request = JsonRequest(url, callback=self.parse)
            request.meta['params'] = params
            return request
        # Always pulls 10 pages. Not ideal
        return [build_request(i) for i in range(0, 1000, 100)]

    def parse(self, response):
        data = json.loads(response.body)

        for vehicle in data['vehicleBasic']:
            try:
                l = ItemLoader(item=CarItem(), response=response)
                l.add_value('url', vehicle.get('weblink'))
                prices = vehicle.get('typedPrices', [])
                if len(prices) > 0:
                    price = int(prices[0].get('amount'))
                else:
                    price = 0
                l.add_value('price', str(price))
                l.add_value('title', vehicle.get('symbolicCarline').get('description'))
                l.add_value('description',	vehicle.get('modelCode').get('description'))
                l.add_value('state_of_vehicle', 'demo')
                l.add_value('model', getn(vehicle, ['symbolicCarlineGroup', 'description'], ''))
                l.add_value('exterior_color',	vehicle.get('extColor').get('description'))
                l.add_value('mileage_value',	str(vehicle.get('used').get('mileage')))
                l.add_value('year',	str(vehicle.get('modelYear')))
                fuels = getn(vehicle, ['io', 'fuels'], [])
                fuels = [fuel['fuel'] for fuel in fuels if 'fuel' in fuel]
                l.add_value('fuel_type', ', '.join(fuels))
                l.add_value('transmission',	vehicle.get('gearType').get('description'))
                l.add_value('vin', '')
                car_id = vehicle.get('decodedCarId', 'no_car_id')
                l.add_value('vehicle_id', car_id)
                l.add_value('rego',	'')
                l.add_value('comments', '')
                l.add_value('dealer_name', vehicle.get('dealer').get('name'))
                l.add_value('fb_page_id', '')
                l.add_value('Make', 'Audi')
                l.add_value('mileage_unit', 'KM')
                l.add_value('body_style', getn(vehicle, ['bodyType', 'description'], ''))
                l.add_value('drivetrain', getn(vehicle, ['driveType', 'description'], ''))
                l.add_value('availability', '')
                address = {
                    'latitude': getn(vehicle, ['dealer', 'geoLocation', 'lat']),
                    'longitude': getn(vehicle, ['dealer', 'geoLocation', 'lon']),
                    'city': getn(vehicle, ['dealer', 'city'], ''),
                    'region': '',
                    'country': 'Australia',
                    'arr1': getn(vehicle, ['dealer', 'street']),
                }
                l.add_value('latitude', str(getn(vehicle, ['dealer', 'geoLocation', 'lat'])))
                l.add_value('longitude', str(getn(vehicle, ['dealer', 'geoLocation', 'lon'])))
                l.add_value('Address', json.dumps(address))

                image_urls = list(map(lambda i: i["url"], vehicle.get('pictures', [])))[:self.max_images]
                l.add_value('image_urls', image_urls)
                for index in range(len(image_urls)):
                    l.add_value(f'image_{index}', f'{self.external_hosting_url}/{car_id}_{index}.jpg')

                yield l.load_item()

            except KeyError as e:
                self.logger.error(f'KeyError: {e}\n {vehicle.get(e)}')
