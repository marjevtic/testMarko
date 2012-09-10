from scrapy.item import Item, Field

class KennethItem(Item):
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
    size = Field()
    add_to_cart_id = Field()
    in_stock = Field()
    images = Field()
    image_urls = Field()
    color_image_urls = Field()
    recommended_product = Field()
    color_option_id = Field()
    size_option_id = Field()
    product_page = Field()
    new_price = Field()
    old_price = Field()



from scrapy.contrib.pipeline.images import ImagesPipeline
from scrapy.http import Request
import Image
from cStringIO import StringIO


class KennethImagesPipeline(ImagesPipeline):


    def image_key(self, url):
        image_guid = self.get_image_name(url)
        return 'full/%s.jpg' % (image_guid)
    
    def custom_image_key(self, url, id):
        image_guid = self.get_image_name(url)
        return '%s/full/%s.jpg' % (id,image_guid)
    
    def custom_thumb_key(self, url, thumb_id, id):
        image_guid = self.get_image_name(url)
        return '%s/%s/%s.jpg' % (id, thumb_id,image_guid)

    def thumb_key(self, url, thumb_id):
        image_guid = self.get_image_name(url)
        return '%s/%s.jpg' % (thumb_id, image_guid)

    def get_image_name(self, url):
        temp = url.split("/")
        guid = temp[len(temp)-1].split(".")[0]
        return guid
    
    def get_media_requests(self, item, info):
        print item.get('image_urls')
        return [Request(x, meta={'id' : item.get('product_id')}) for x in item.get('image_urls', [])]
    
    def get_images(self, response, request, info):
        key = self.image_key(request.url)
        id = request.meta.get('id')[0]
        key = self.custom_image_key(request.url, id)
        print key
        orig_image = Image.open(StringIO(response.body))

        width, height = orig_image.size
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            raise ImageException("Image too small (%dx%d < %dx%d): %s" % \
                    (width, height, self.MIN_WIDTH, self.MIN_HEIGHT, response.url))

        image, buf = self.convert_image(orig_image)
        yield key, image, buf

        for thumb_id, size in self.THUMBS.iteritems():
            thumb_key = self.custom_thumb_key(request.url, thumb_id, id)
            thumb_image, thumb_buf = self.convert_image(image, size)
            yield thumb_key, thumb_image, thumb_buf
