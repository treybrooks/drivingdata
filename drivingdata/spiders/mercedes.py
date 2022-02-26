from audioop import add
from datetime import datetime
import urllib
import json
import csv
import scrapy
from scrapy.http import JsonRequest
from scrapy.loader import ItemLoader
from drivingdata.items import CarItem

dealer_dict = {}
with open('Dealers.csv', 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        dealer_dict[row["dealer_name"]] = row

def getn(d, path, default=None):
    for p in path:
        if p not in d:
            return default
        d = d[p]
    return d

class MercedesSpider(scrapy.Spider):
    name = 'mercedes'
    allowed_domains = ['shop.mercedes-benz.com']
    BASE_URL = 'https://shop.mercedes-benz.com/dcpoto-api/dcp-api/v2/dcp-mp-au/products/search'
    external_hosting_url = 'https://drivingdata.com.au/facebook/mercedes-v2/images'
    max_images = 5

    def start_requests(self):
        def build_request(index):
            params = {
                'query': ':relevance:useProductType:UCOS',
                'currentPage': index,
                'pageSize': 100,
                'fields': 'FULL',
                'lang': 'en',
            }
            url = f'{self.BASE_URL}?{urllib.parse.urlencode(params)}'
            request = JsonRequest(url, callback=self.parse)
            request.meta['params'] = params
            return request
        # Always pulls 30 pages. Not ideal
        return [build_request(i) for i in range(30)]

    def parse(self, response):
        data = json.loads(response.body)

        for vehicle in data['products']:
            try:
                # l = ItemLoader(item=CarItem(), response=response)
                item_dict = {}
                car_id = vehicle.get('code')
                response.meta['car_id'] = car_id

                item_dict['url'] = f'https://shop.mercedes-benz.com/en-au/shop/vehicle/pdp/{car_id}'
                item_dict['price'] = str(getn(vehicle, ['price','value'], ''))
                item_dict['title'] = vehicle.get('name')
                item_dict['description'] =	vehicle.get('description')
                item_dict['state_of_vehicle'] = self.get_vehicle_state(vehicle['categories'])
                item_dict['model'] = vehicle.get('model')
                item_dict['exterior_color'] = self.get_feature(vehicle['classifications'][0]['features'], "Colour")
                item_dict['mileage_value'] =	str(getn(vehicle, ['mileage','value']))
                item_dict['year'] =	str(vehicle.get('modelYear'))
                item_dict['fuel_type'] = self.get_feature(vehicle['classifications'][0]['features'], "Fuel Type")
                item_dict['transmission'] =	vehicle.get('gearBox')
                item_dict['vin'] = vehicle.get('vin')
                item_dict['vehicle_id'] = car_id
                # l.add_value('rego', self.get_feature(vehicle['classifications'][0]['features'], "Registration Number"))
                # l.add_value('comments', self.get_feature(vehicle['classifications'][1]['features'], "Dealer comments"))
                item_dict['availability'] = 'Available'

                try:
                    dealer_info = vehicle.get('pointOfServices')[0]
                    dealer_known_info = dealer_dict.get(dealer_info.get('displayName', ''))

                    item_dict['dealer_name'] = dealer_info.get('displayName', '')
                    item_dict['fb_page_id'] = dealer_known_info["fb_page_id"]
                    address = dealer_known_info.get("Address", {
                        'latitude': dealer_known_info.get("latitude", ''),
                        'longitude': dealer_known_info.get("longitude", ''),
                        'city': getn(dealer_info, ['address', 'town'], ''),
                        'region': '',
                        'country': getn(dealer_info, ['address', 'country', 'name'], ''),
                        'arr1': getn(dealer_info, ['address', 'line1'], ''),
                    })
                    item_dict['latitude'] = str(dealer_known_info.get("latitude", ''))
                    item_dict['longitude'] = str(dealer_known_info.get("longitude", ''))
                    item_dict['Address'] = address
                except:
                    dealer_info = ''

                item_dict['Make'] = 'Mercedes-Benz'
                item_dict['mileage_unit'] = getn(vehicle, ['mileage','unit'], 'KM')
                item_dict['body_style'] = vehicle.get('bodyType', '')
                item_dict['drivetrain'] = 'Automatic'

                image_urls = list(map(lambda i: i["url"], vehicle.get('images', [])))[:self.max_images]
                item_dict['image_urls'] = image_urls
                for index in range(len(image_urls)):
                    item_dict[f'image_{index}'] = f'{self.external_hosting_url}/{car_id}_{index}.jpg'

                # yield l.load_item()

            except KeyError as e:
                self.logger.error(f'KeyError: {e}\n {vehicle.get(e)}')

            setattr(self, car_id, item_dict)
            params = {
                'fields': 'FULL'
            }
            uri=f'https://shop.mercedes-benz.com/dcpoto-api/dcp-api/v2/dcp-mp-au/products/{car_id}'
            vehicle_url = f'{uri}?{urllib.parse.urlencode(params)}'
            yield JsonRequest(
                url=vehicle_url,
                callback=self.parse_car_page,
                meta=response.meta
            )


    def parse_car_page(self, response):
        vehicle = json.loads(response.body)
        
        # get car_id
        car_id = response.meta['car_id']
        item_dict = getattr(self, car_id)
        l = ItemLoader(item=CarItem(item_dict), response=response)
        delattr(self, car_id)

        rego = self.get_feature(vehicle['classifications'][0]['features'], "Registration Number")
        l.add_value('rego', rego)

        comments = self.get_feature(vehicle['classifications'][1]['features'], "Dealer comments")
        l.add_value('comments', comments)

        return l.load_item()

    def get_vehicle_state(self, categories):
        vehicle_state = ''
        for category in categories:
            code = category['code']
            if code == '5_Certified':
                vehicle_state = 'Certified'
                break
            elif code == '4_Demonstrator':
                vehicle_state = 'Demonstrator'
                break
        return vehicle_state

    def get_feature(self, features, feature_name):
        value = None
        for feature in features:
            if feature['name'] == feature_name:
                value = feature['featureValues'][0]['value']
                break
        return value
