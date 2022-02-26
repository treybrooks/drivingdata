import enum
import scrapy
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exporters import CsvItemExporter


class VehicleImagesPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        adapter = ItemAdapter(item)
        vin = ''.join(adapter['vehicle_id'])
        return [scrapy.Request(x, meta={'image_name': f"{vin}_{index}"})
            for index, x in enumerate(item.get('image_urls', []))]

    def file_path(self, request, response=None, info=None):
        return f"{request.meta['image_name']}.jpg"

class CarScraperPipeline:
    def open_spider(self, spider):
        self.dealership_exporter = {}

    def close_spider(self, spider):
        for exporter, csv_file in self.dealership_exporter.values():
            exporter.finish_exporting()
            csv_file.close()

    def _exporter_for_item(self, item, spider):
        adapter = ItemAdapter(item)
        dealer = adapter['dealer_name'][0]

        if dealer not in self.dealership_exporter:
            spider.logger.debug(f"Adding: {dealer} to exporters")
            csv_file = open(f'output/{dealer}.csv', 'wb')
            exporter = CsvItemExporter(
                csv_file,
                fields_to_export = [
                    'url',
                    'price',
                    'title',
                    'description',
                    'state_of_vehicle',
                    'model',
                    'exterior_color',
                    'mileage_value',
                    'year',
                    'fuel_type',
                    'transmission',
                    'vin',
                    'vehicle_id',
                    'rego',
                    'comments',
                    'dealer_name',
                    'fb_page_id',
                    'Make',
                    'mileage_unit',
                    'body_style',
                    'drivetrain',
                    'availability',
                    'latitude',
                    'longitude',
                    'Address',
                    'image_0',
                    'image_1',
                    'image_2',
                    'image_3',
                    'image_4',
                ])
            exporter.start_exporting()
            self.dealership_exporter[dealer] = (exporter, csv_file)
        return self.dealership_exporter[dealer][0]

    def process_item(self, item, spider):
        exporter = self._exporter_for_item(item, spider)
        exporter.export_item(item)
        return item
