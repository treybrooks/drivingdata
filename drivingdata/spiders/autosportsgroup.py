import os
import re
import csv
import json
import scrapy
from scrapy.loader import ItemLoader
from drivingdata.items import CarItem


class AutosportsGroupSpider(scrapy.Spider):
    name = 'autosportsgroup'
    allowed_domains = ['autosportsgroup.com.au']
    external_hosting_url = 'https://drivingdata.com.au/facebook/autosports/images'
    debug = True

    max_images = 5

    def start_requests(self):
        with open('..dealers/AutosportsDealers.csv', encoding = "ISO-8859-1") as csvfile:
            reader = csv.DictReader(csvfile)

            requests = []
            for dealer in reader:
                req = scrapy.Request(
                    f"http://autosportsgroup.com.au/new-demo-used-cars.html?location={dealer['name']}",
                    meta = {
                        'dealer_name': dealer['name'],
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
        vehicle_urls = response.xpath('//div[@class="stockLeft"]/a/@href').getall()
        self.logger.debug(f'we found {len(vehicle_urls)} vehicles on this page')
        for vehicle_url in vehicle_urls:
            yield scrapy.Request(
                url=response.urljoin(vehicle_url),
                callback=self.parse_vehicle,
                meta=response.meta
            )
       
        next_page_url = response.xpath('//a[contains(., "Next")]/@href').get()
        self.logger.debug(f'NEXT PAGE: {next_page_url}')
        yield scrapy.Request(
            url=response.urljoin(next_page_url),
            callback=self.parse,
            meta=response.meta
        )

    def parse_vehicle(self, response):
        l = ItemLoader(item=CarItem(), response=response)
        l.add_value('url', response.url)
        
        script = response.xpath('(//script)[2]/text()').get()
        re_extracted_data = re.findall(r'ddDataLayer.push\((.*\})', script, re.DOTALL)[0]
        dd_data_layer = json.loads(re_extracted_data)
        price = dd_data_layer.get('dd_stock_price')
        l.add_value('state_of_vehicle', dd_data_layer.get('dd_stock_type'))
        l.add_value('model', dd_data_layer.get('dd_stock_model'))
        l.add_value('exterior_color', dd_data_layer.get('dd_stock_colour'))
        l.add_value('year', dd_data_layer.get('dd_stock_year')) # response.xpath(base_xpath, val="Vehicle:")
        l.add_value('fuel_type', dd_data_layer.get('dd_stock_fuel')) # response.xpath(base_xpath, val="Vehicle:")
        l.add_value('transmission', dd_data_layer.get('dd_stock_trans')) # response.xpath(base_xpath, val="Vehicle:")
        l.add_value('vehicle_id', dd_data_layer.get('dd_stock_number')) # response.xpath(base_xpath, val="Vehicle:")
        
        # converts price to int because zero evaluates to false too
        if not int(price):
            s_price = response.xpath("//h4[@class='fullPrice']/text()").get()
            if s_price:
                price = s_price.replace("$","").replace(",","")
        l.add_value('price', price)

        l.add_value('comments', response.xpath("//div[@class='stockItemComment']/p/text()").get())

        # base_xpath = "//li/span[@class='spec' and text()=$val]/following-sibling::span[@class='info']/text()"
        base_xpath = "//li[contains(., $val)]/span[@class='info']/text()"
        l.add_value('title', response.xpath(base_xpath, val="Vehicle Description:").get())
        l.add_value('description', response.xpath(base_xpath, val="Vehicle:").get())
        odometer = response.xpath(base_xpath, val="Odometer:").get()
        if odometer:
            odometer = odometer.replace("kms","").replace(",","")
            l.add_value('mileage_value', odometer)
        l.add_value('rego', response.xpath(base_xpath, val="Registration:").get())
        vin = response.xpath(base_xpath, val="VIN:").get()
        l.add_value('vin', vin)

        # extract image urls and define filenames
        image_urls = response.xpath('//div[@class="stockItemGallery"]/a/@href').getall()
        l.add_value('image_urls', image_urls[:self.max_images])
        # build hosted image urls
        for index, _ in enumerate(image_urls[:self.max_images]):
            l.add_value(f'image_{index}', f'{self.external_hosting_url}/{vin}_{index}.jpg')

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
