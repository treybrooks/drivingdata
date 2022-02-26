# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Item, Field


class CarItem(scrapy.Item):
    url = Field()
    price = Field()
    title = Field()
    description = Field()
    state_of_vehicle = Field()
    model = Field()
    exterior_color = Field()
    mileage_value = Field()
    year = Field()
    fuel_type = Field()
    transmission = Field()
    vin = Field()
    vehicle_id = Field()
    comments = Field()
    rego = Field()
    dealer_name = Field()
    
    # dealer info
    dealer_name = Field()
    fb_page_id = Field()
    Make = Field()
    mileage_unit = Field()
    body_style = Field()
    drivetrain = Field()
    availability = Field()
    latitude = Field()
    longitude = Field()
    Address = Field()
    
    # image urls
    image_urls = Field()
    images = Field()
    image_0 = Field()
    image_1 = Field()
    image_2 = Field()
    image_3 = Field()
    image_4 = Field()

