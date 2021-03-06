from scrapy.item import Item, Field

class BurtonItem(Item):
    product_id =Field()
    name = Field()
    normal_image_url = Field()
    description = Field()
    master_product_id = Field()
    add_to_cart_id = Field()
    price = Field()
    color_id =Field()
    in_stock = Field()
    image_urls = Field()
    images = Field()
    variants = Field()
    all_sizes = Field()
    color_json = Field()
    old_price = Field()
    features = Field()
    product_link = Field()
