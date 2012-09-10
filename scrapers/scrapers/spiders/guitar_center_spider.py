from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
from project_modules.guitar_center import GuitarCenterItem
import modules.basic_func as basic
from modules.zmags_xml import CommonXml
from modules.excel import DictExcel
from modules.exception import ZmagsException
from modules.terminal import DatabaseTerminal
from modules.database import Database
from modules.export_to_db import CommonExport
import hashlib
import urllib2
import simplejson
import sys
from datetime import datetime
import re
import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals


class GuitarCenterSpider(CrawlSpider):
    name = "guitar_center"
    allowed_domains = ["musiciansfriend.com"]
    start_urls = ["http://www.musiciansfriend.com"]
    counter = 0

    def __init__(self, *a, **kw):
        super(GuitarCenterSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        terminal = DatabaseTerminal(sys.argv, self.name)
        self.d = terminal.get_arguments()
        self.xml = CommonXml()
        self.exc = ZmagsException(5)
        if self.d['database']:
            self.database = Database()
            self.database.connect()
            self.products, self.no_urls = self.database.select_products(self.d['catalog_id'],
                                                                        self.d['product_id'])
            self.database.disconnect()
        else:
            self.get_lists_from_excel()
        self.add_properties(self.xml)
        self.handle_not_provided()
        self.start_urls = self.products['urls']
        self.total = len(self.products['urls'])

    def parse(self, response):
        self.counter += 1
        basic.print_status(self.counter, self.total)
        hxs = HtmlXPathSelector(response)
        item = GuitarCenterItem()
        from scrapy.conf import settings
        if 'redirect_urls' in response.request.meta:
            cur_url = response.request.meta['redirect_urls'][0]
        else:
            cur_url = response.url
        index = self.products['urls'].index(cur_url)
        try:
            item['product_id'] = [self.products['product_ids'][index]]
            item['name'], item['brand'] = self.get_basic_info(hxs)
            item['heading'], item['details'], item['specs'], item['call_to_action'] = self.get_description(hxs)
            item['brand_image'], item['brand_image_promo'], brand_images = self.get_description_images(hxs)
            item['old_price'], item['discount'], item['price'] = self.get_prices(hxs)
            item['image_json'], img = self.get_images(hxs)
            item['serial'] = self.get_serials(hxs)
            item['warranty'] = self.gold_coverage(hxs)
            item['in_stock'] = self.get_available(hxs)
            item['product_ref'], item['add_to_cart_id'] = self.get_add_to_cart(hxs)
            if not item['add_to_cart_id']:
                item['in_stock'] = ["NOT_AVAILABLE"]
            item['shipping'] = self.get_shipping(hxs)
            item['colors'] = self.get_colors(hxs)
            self.products['status'][index] = "ran"
        except StandardError:
            self.products['status'][index] = "error"
            self.exc.code_handler(100, response.url)
        else:
            self.xml.create_xml(item)
            item['image_urls'] = img + brand_images
        return item

    def handle_not_provided(self):
        item = GuitarCenterItem()
        for n in self.no_urls['product_ids']:
            item['product_id'] = [n]
            index = self.no_urls['product_ids'].index(n)
            item['name'] = [self.no_urls['names'][index]]
            item['in_stock'] = ['NOT_AVAILABLE']
            self.xml.create_xml(item)

    def get_basic_info(self, hxs):
        name = hxs.select('//h1[@class="fn"]/text()').extract()
        name = [basic.clean_string("".join(name))]
        brand = hxs.select('//span[@class="brand"]/text()').extract()
        name = [name[0].replace(u"\xa0", "")]
        return name, brand

    def get_description_images(self, hxs):
        brand_image = hxs.select('//a[@class="brandImage"]/img/@src').extract()
        brand_image_promo = hxs.select('//div[@class="brandPromoLogo"]/img/@src').extract()
        images = brand_image + brand_image_promo
        if brand_image:
            brand_image = [self.get_server_path(brand_image[0])]
        if brand_image_promo:
            brand_image_promo = [self.get_server_path(brand_image_promo[0])]
        return brand_image, brand_image_promo, images

    def get_description(self, hxs):
        heading = hxs.select('//div[@id="description"]/p').extract()
        details = hxs.select('//p[@class="description"]').extract()
        specs = hxs.select('//div[@class="specs"]/ul').extract()
        last = hxs.select('//div[@class="callToAction"]/p/text()').extract()
        return basic.cdata_field(heading), basic.cdata_field(details), basic.cdata_field(specs), basic.cdata_field(last)

    #function for getting prices, returns tags and values or empty field if no option for one of them new is discount
    def get_prices(self, hxs):
        tag = hxs.select('//dl[@class="lineItemList"]/dt/text()').extract()
        value = hxs.select('//dl[@class="lineItemList"]/dd/text()').extract()
        old_price = []
        discount = []
        price = []
        if len(tag) > 1:
            old_price = [basic.clean_string(value[0])]
        try:
            discount = [basic.clean_string(value[len(value) - 1])]
        except IndexError:
            print "This product has no price."
        try:
            price = hxs.select('//span[@class="topAlignedPrice"]/text()').extract()
        except IndexError:
            print "This product has no price."
        if not old_price and not discount and not price:
            price = hxs.select('//dl[@class="inlineList"]/dd/text()').extract()
        return self.clean_price(old_price), self.clean_price(discount), self.clean_price(price)

    # returning json with image url and serial number of product image refers to
    def get_images(self, hxs):
        images = hxs.select('//ul[@id="prodDetailThumbs"]/li/a/@href').extract()
        tags = hxs.select('//ul[@id="prodDetailThumbs"]/li/@class').extract()
        images_list = []
        d = {}
        img = []
        for i in range(0, len(images)):
            d['image_url'] = self.get_server_path(images[i])
            img.append(images[i])
            if "site1sku" in tags[i]:
                d['product_serial'] = tags[i].replace("site1sku", "")
            else:
                d['product_serial'] = tags[i]
            images_list.append(basic.cdata(simplejson.dumps(d)))
        return images_list, img

    # function for getting serials and all information about them, currently returns field with jsons with all
    # information, can be modified to return dicts if needed for subproducts for those one day
    def get_serials(self, hxs):
        serials = hxs.select('//var[@class="hidden styleInfo"]/text()').extract()
        new = []
        for serial in serials:
            d = simplejson.loads(serial)
            new.append(basic.cdata(simplejson.dumps(d)))
        return new

    def get_server_path(self, url):
        #uncomment next line if you want to keep absolute image path from their site
        return url
        return IMAGES_STORE + "/full/" + hashlib.sha1(url).hexdigest() + ".jpg"

    # function for getting gold coverage from the page which is actually additional warranty options
    def gold_coverage(self, hxs):
        ids = hxs.select('//div[@class="goldCoverage"]/input[@type="checkbox"]/@value').extract()
        labels = hxs.select('//div[@class="goldCoverage"]/label/text()').extract()
        d = {}
        new = []
        for i in range(0, len(ids)):
            d['id'] = ids[i]
            d['name'] = labels[i]
            new.append(basic.cdata(simplejson.dumps(d)))
        return new

    # function for getting availability
    def get_available(self, hxs):
        p = hxs.select('//var[@class="hidden availability"]/text()').extract()
        if p:
            if p[0] == "in_stock":
                p = [p[0].upper()]
        else:
            #for those that have color options and in stock status for each of those
            #put IN_STOCK for the product as it has no that option on the page
            p = ["IN_STOCK"]
        return p

    # function for getting add to cart id and product reference
    def get_add_to_cart(self, hxs):
        try:
            temp = hxs.select('//span[@class="magicLink addToList"]/@data-rel').extract()[0]
        except:
            print "Product not available"
        else:
            return [temp.split("|")[0]], [temp.split("|")[1]]
        return [], []

    # function for gatting shipping information
    def get_shipping(self, hxs):
        return hxs.select('//div[@id="targeter_pdpShipping"]/span/text()').extract()

    # function for getting colors, return jsons with all the data about options
    def get_colors(self, hxs):
        colors = hxs.select('//var[@class="styleInfo"]/text()').extract()
        new = []
        for color in colors:
            d = simplejson.loads(color)
            new.append(basic.cdata(simplejson.dumps(d)))
        return new

    # cleaning price to leave only numbers
    def clean_price(self, price):
        new = []
        for i in price:
            new.append(re.sub('[^0-9.]', '', i))
        return new

    def spider_closed(self, spider):
        """Handles spider_closed signal from end of scraping.
        Handles usual end operations for scraper like writing xml, exporting
        to database and sending appropriate mail message."""
        msg = "Ran: {0}".format(datetime.now())
        if self.counter < self.total:
            msg += "\nScraper didn't go through all products, please report"
        msg += "\n\nScraped %d product out of %d\n\n" % (self.counter, self.total)
        # filename for writing xml
        if self.d['database']:
            try:
                self.database.connect()
                filename = self.database.get_name(self.d['catalog_id'])
                self.database.update_db(self.products)
                self.database.disconnect()
                msg += "\nRan from interface.\n"
            except:
                msg += "\nUpdating database failed, please report."
        else:
            msg += "\nRan from console.\n"
            filename = self.d['file']
        self.xml.write_xml(self.name, filename)
        msg += self.exc.create_message(self.counter)
        if self.d['upload']:
            exp = CommonExport()
            try:
                exp.xml_to_db(self.name, filename, "4a9f5955-9b8e-4e13-84ef-95f937dbc00d")
                msg += "\n\nExport to database successful"
            except StandardError:
                msg += "\n\nExport to database failed"
        else:
            msg += "\n\nUpload to database not selected"
        ## part for exporting to database here
        from modules.mail import Mail
        mail = Mail()
        try:
            mail.send_mail(msg, "GuitarCenter: {0}".format(filename))
            if self.d['email']:
                mail.send_mail(msg, "GuitarCenter: {0}".format(filename), self.d['email'])
        except:
            msg += "\nSending mail failed."
        if self.d['database']:
            path = "logs/{0}".format(self.name)
            if not os.path.exists(path):
                os.makedirs(path)
            with open("{0}/{1}".format(path, filename), 'w') as f:
                f.write(msg)

    def add_properties(self, xml):
        xml.add_property("old_price", "Old Price", "decimal")
        xml.add_property("image_json", "Image Json", "text_list")
        xml.add_property("discount", "Discount", "decimal")
        xml.add_property("product_ref", "Product Ref.", "text")
        xml.add_property("in_stock", "In Stock", "text")
        xml.add_property("serial", "Serial", "text_list")
        xml.add_property("colors", "Colors", "text_list")
        xml.add_property("add_to_cart_id", "Add To Cart ID", "text")
        xml.add_property("shipping", "Shipping", "text")
        xml.add_property("warranty", "Warranty", "text_list")
        xml.add_property("heading", "Heading", "text")
        xml.add_property("details", "Details", "text")
        xml.add_property("specs", "Specs", "text")
        xml.add_property("call_to_action", "Call To Action", "text")
        xml.add_property("brand_image", "Brand Image", "text")
        xml.add_property("brand_image_promo", "Brand Image Promo", "text")

    def get_lists_from_excel(self):
        xls = DictExcel(basic.get_excel_path(self.name, self.d['file']))
        self.products = dict()
        try:
            self.products['urls'] = xls.read_excel_collumn_for_urls(3, 15)
            self.products['product_ids'] = xls.read_excel_collumn_for_ids(1, 15)
            self.products['names'] = xls.read_excel_collumn(2, 15)
        except IOError as e:
            msg = "I/O error {0}: {1}".format(e.errno, e.strerror)
            msg += "\nError occurred for given file: {0}".format(self.d['file'])
            self.exc.code_handler(103, msg=msg)
        except StandardError:
            msg = "Error reading excel file"
            msg += "\nError occurred for given file: {0}".format(self.d['file'])
            self.exc.code_handler(103, msg=msg)
        self.products= xls.delete_duplicates_dict(self.products)
        self.products, self.no_urls = xls.separate_no_urls(self.products)
        self.products = xls._add_none_status(self.products)
        self.no_urls = xls._add_none_status(self.no_urls)
