import re
import json
import scrapy
from scrapy.loader import ItemLoader
from drivingdata.items import CarItem


class BmwSydneySpider(scrapy.Spider):
    name = 'bmwsydney'
    allowed_domains = ['bmwsydney.com.au']
    start_urls = ['https://www.bmwsydney.com.au/preowned/listing/demo']
    external_hosting_url = 'https://drivingdata.com.au/facebook/bmw/images'
    debug = True

    max_images = 5

    def parse(self, response):
        vehicle_urls_html = response.xpath('//@href').getall()
        self.logger.info(response.text)
        vehicle_urls = response.xpath('//div[@class="car-padding"]/h2/a/@href').getall()
        self.logger.debug(f'we found {len(vehicle_urls)} vehicles on this page')
        for vehicle_url in vehicle_urls:
            yield scrapy.Request(
                url=response.urljoin(vehicle_url),
                callback=self.parse_vehicle
            )
       
        next_page_url = response.xpath('//div[@class="pagination"]/li/a[contains(., "Next Page")]/@href').get()
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
        l.add_value('state_of_vehicle', dd_data_layer.get('state_vehicle'))
        l.add_value('model', dd_data_layer.get('model'))
        l.add_value('exterior_color', dd_data_layer.get('colour'))
        l.add_value('year', dd_data_layer.get('year'))
        l.add_value('fuel_type', response.xpath('ul[@class="vehicle-details"]/li[contains(., "Fuel Type")]/span/text()').get())
        l.add_value('transmission', dd_data_layer.get('transmission'))
        l.add_value('vehicle_id', dd_data_layer.get('id'))
        l.add_value('price', str(dd_data_layer.get('price')))

        # l.add_value('comments', response.xpath("//div[@class='stockItemComment']/p/text()").get())
        l.add_value('title', dd_data_layer.get('pageName'))
        l.add_value('description', '')
        l.add_value('mileage_value', str(dd_data_layer.get('kms')))
        l.add_value('rego', '')
        vin = dd_data_layer.get('vin')
        l.add_value('vin', vin)

        # extract image urls and define filenames
        image_urls = response.xpath('//div[@class="sd-gallery-thumb"]/div[@class="embla__slide__inner"]/img/@src').getall()
        l.add_value('image_urls', image_urls[:self.max_images])
        # build hosted image urls
        for index, _ in enumerate(image_urls[:self.max_images]):
            l.add_value(f'image_{index}', f'{self.external_hosting_url}/{vin}_{index}.jpg')

        dealer_script = response.xpath('(//script)[7]/text()').get()
        dealer = json.loads(dealer_script)
        l.add_value('dealer_name', dealer['name'])
        l.add_value('fb_page_id', '')
        l.add_value('Make', dd_data_layer.get('mane'))
        l.add_value('mileage_unit', 'KM')
        l.add_value('body_style', dd_data_layer.get('body'))
        l.add_value('drivetrain', '')
        l.add_value('availability', '')
        l.add_value('latitude', '')
        l.add_value('longitude', '')
        dealer_address = {
            'latitude': '',
            'longitude': '',
            'city': dealer['address'].get('addressLocality'),
            'region': dealer['address'].get('addressRegion'),
            'country': 'Australia',
            'arr1': dealer['streetAddress'],
        }
        l.add_value('Address', json.dumps(dealer_address))

        yield l.load_item()
