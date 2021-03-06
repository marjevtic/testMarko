from scrapy.item import Item, Field

class LydiasItem(Item):
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
    review = Field()
    custom_size = Field()
    sizes_chart_image_url = Field()
    color_image_url = Field()
    image_urls = Field()
    images = Field()
    in_stock  = Field()
    custom_rating = Field()
    default_image_url = Field()
    old_price = Field()
    color_short = Field()
    size_short = Field()
    price_url = Field()
    embroidery = Field()
    lettering = Field()
    log = Field()
