from scrapy.item import Item, Field

class ExpressItem(Item):
    product_id = Field()
    enabled = Field()
    master_product_id = Field()
    default_variant_product_id = Field()
    name = Field()
    category_name = Field()
    category_id = Field()
    description = Field()
    short_description = Field()
    brand = Field()
    manufacturer = Field()
    color = Field()
    size = Field()
    price = Field()
    discount_price = Field()
    discount_rate = Field()
    available_to_sell = Field()
    age = Field()
    rating = Field()
    recommendable = Field()
    thumb_image_url = Field()
    normal_image_url = Field()
    zoom_image_url = Field()
    color_image_url = Field()
    size_option_id = Field()
    images = Field()
    image_urls = Field()
    in_stock = Field()
    style = Field()
    variants = Field()
    colors = Field()
    mode = Field()
    mode = Field()
    shop_look = Field()
    shop_line = Field()
    normal = Field()
    ensemble_id = Field()
    promo_text = Field()
    product_page = Field()
    master_price = Field()
    category_id = Field()
    subcategory_id = Field()
    add_to_cart_id = Field()
    order_index = Field()



from scrapy.contrib.pipeline.images import ImagesPipeline
from scrapy.http import Request
from cStringIO import StringIO
from scrapy.utils.misc import md5sum

import Image
import hashlib


class ExpressImagesPipeline(ImagesPipeline):

    def get_image_name(self, url):
        temp = url.split("?")
        image_site = temp[0]
        image_site = image_site.split("fashion/")
        image_guid = image_site[1]
        if url.count("$") > 0:
            temp = image_guid.split("/i")
            image_guid = temp[0]
        return image_guid

    def image_key(self, url):
        image_guid = self.get_image_name(url)
        return 'full/%s.jpg' % image_guid

    def custom_image_key(self, url, id):
        image_guid = hashlib.sha1(url).hexdigest()
        return '%s/full/%s.jpg' % (id, image_guid)

    def custom_thumb_key(self, url, thumb_id, id):
        image_guid = hashlib.sha1(url).hexdigest()
        return '%s/%s/%s.jpg' % (id, thumb_id, image_guid)

    def thumb_key(self, url, thumb_id):
        image_guid = self.get_image_name(url)
        return '%s/%s.jpg' % (thumb_id, image_guid)

    def get_media_requests(self, item, info):
        print item.get('image_urls')
        return [Request(x, meta={'id': item.get('product_id')}) for x in item.get('image_urls', [])]

    def get_images(self, response, request, info):
        key = self.image_key(request.url)
        id = request.meta.get('id')[0]
        key = self.custom_image_key(request.url, id)
        print key
        orig_image = Image.open(StringIO(response.body))

        width, height = orig_image.size
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            raise ImageException("Image too small (%dx%d < %dx%d): %s" %
                                (width, height, self.MIN_WIDTH, self.MIN_HEIGHT, response.url))

        image, buf = self.convert_image(orig_image)
        yield key, image, buf

        for thumb_id, size in self.THUMBS.iteritems():
            thumb_key = self.custom_thumb_key(request.url, thumb_id, id)
            thumb_image, thumb_buf = self.convert_image(image, size)
            yield thumb_key, thumb_image, thumb_buf
