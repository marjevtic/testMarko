# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class PartyliteItem(Item):
    product_id =Field()
    recommended = Field()
    name = Field()
    custom_price = Field()
    review = Field()
    normal_image_url = Field()
    description = Field()
    master_product_id = Field()
    add_to_cart_id = Field()
    price = Field()
    swatch_color = Field()
    color_id =Field()
    in_stock = Field()
    image_urls = Field()
    images = Field()
    shown_with = Field()
    custom_discount = Field()

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/topics/item-pipeline.html


class PartylitePipeline(object):
    def process_item(self, item, spider):
        return item

from scrapy.contrib.pipeline.images import ImagesPipeline
import hashlib


class PartyliteImagesPipeline(ImagesPipeline):
    def image_key(self, url):
        url = url.split("partylite.biz")[1]
        return 'full/%s.jpg' % hashlib.sha1(url).hexdigest()
