from scrapy.item import Item, Field

class GuitarCenterItem(Item):
    product_id = Field()
    name = Field()
    brand = Field()
    description = Field()
    old_price = Field()
    discount = Field()
    price = Field()
    image_json = Field()
    serial = Field()
    image_urls = Field()
    images = Field()
    warranty = Field()
    in_stock = Field()
    add_to_cart_id = Field()
    shipping = Field()
    product_ref = Field()
    colors = Field()
    heading = Field()
    details = Field()
    specs = Field()
    call_to_action = Field()
    brand_image = Field()
    brand_image_promo = Field()
