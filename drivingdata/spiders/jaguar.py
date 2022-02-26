import os
import re
import csv
import json
import scrapy
from scrapy.loader import ItemLoader
from drivingdata.items import CarItem


class JaguarSpider(scrapy.Spider):
    name = 'jaguar'
    debug = True
    external_hosting_url = 'https://drivingdata.com.au/facebook/jaguar/images'
    allowed_domains = ['quote.jaguar.com.au']

    max_images = 5

    def start_requests(self):
        with open('dealers/JaguarDealers.csv', encoding = "ISO-8859-1") as csvfile:
            reader = csv.DictReader(csvfile)

            requests = []
            for dealer in reader:
                req = scrapy.Request(
                    dealer['url'],
                    meta = {
                        'dealer_name': dealer['dealer_name'],
                        'fb_page_id': dealer['fb_page_id'],
                        'Make': dealer['Make'],
                        'mileage_unit': dealer['mileage.unit'],
                        'body_style': dealer['body_style'],
                        'drivetrain': dealer['drivetrain'],
                        'availability': dealer['availability'],
                        'latitude': dealer['latitude'],
                        'longitude': dealer['longitude'],
                        'Address': dealer['Address']
                    }
                )
                requests.append(req)

        return requests

    def parse(self, response):
        vehicle_urls = response.xpath('//span/a[@class="item-name-desc"]/@href').getall()
        self.logger.debug(f'we found {len(vehicle_urls)} vehicles on this page')
        for vehicle_url in vehicle_urls:
            yield scrapy.Request(
                url=response.urljoin(vehicle_url),
                callback=self.parse_vehicle,
                meta=response.meta
            )
       
        for next_page_url in response.xpath('//li[@class="pagination-alt"][not(contains(@class, "disabled"))]/a/@href').getall():
            yield scrapy.Request(
                url=response.urljoin(next_page_url),
                callback=self.parse,
                meta=response.meta
            )

    def parse_vehicle(self, response):
        l = ItemLoader(item=CarItem(), response=response)
        data = json.loads(response.xpath('//script[@type="application/ld+json"]/text()').get())
        stock_id = data.get('sku')

        # collect basic info
        l.add_value('url', response.url)
        l.add_value('price', str(data.get('offers', {}).get('price')))
        l.add_value('title', data.get('name'))
        l.add_value('description', data.get('description'))
        l.add_value('state_of_vehicle', data.get('itemCondition'))
        l.add_value('model', data.get('model'))
        l.add_value('exterior_colour', data.get('color'))
        l.add_value('fuel_type', data.get('fuelType'))
        l.add_value('transmission', data.get('vehicleTransmission'))
        l.add_value('vin', data.get('vehicleIdentificationNumber'))
        l.add_value('vehicle_id', stock_id)
        
        # Parse and extract odometer information:
        odo_pattern = re.compile(r"Odometer: (\d*)")
        try:
            odometer = response.xpath("//script[contains(., 'Odometer:')]/text()").re(odo_pattern)[0]
        except IndexError:
            odometer = 'N/A'
        l.add_value('mileage', odometer)

        # Parse and extract year:
        maybe_year = data.get('name').split()[0]
        l.add_value('year', ('', maybe_year)[maybe_year.isnumeric()])

        # Parse and extract Rego information:
        rego_pattern = re.compile(r"Rego: (\w*) ")
        try:
            rego_number = response.xpath("//script[contains(., 'Rego:')]/text()").re(rego_pattern)[0]
        except IndexError:
            rego_number = 'N/A'
        l.add_value('rego', rego_number)

        # Parse and extract comments:
        comments_text = response.xpath("//div[@id='comments-tab']//div[contains(@class, 'normal-text-meta')]/text()").getall()
        l.add_value('comments', comments_text)

        # extract image urls and define filenames
        image_urls = response.xpath('//div[@class="slide-gallery"]/div/a[1]/@href').getall()
        l.add_value('image_urls', image_urls[:self.max_images])
        # build hosted image urls
        for index, _ in enumerate(image_urls[:self.max_images]):
            name = data.get('vehicleIdentificationNumber')
            l.add_value(f'image_{index}', f'{self.external_hosting_url}/{name}_{index}.jpg')

        # add dealer info
        l.add_value('dealer_name', response.meta['dealer_name'])
        l.add_value('fb_page_id', response.meta['fb_page_id'])
        l.add_value('Make', response.meta['Make'])
        l.add_value('mileage_unit', response.meta['mileage_unit'])
        l.add_value('body_style', response.meta['body_style'])
        l.add_value('drivetrain', response.meta['drivetrain'])
        l.add_value('availability', response.meta['availability'])
        l.add_value('latitude', response.meta['latitude'])
        l.add_value('longitude', response.meta['longitude'])
        l.add_value('Address', response.meta['Address'])

        yield l.load_item()
