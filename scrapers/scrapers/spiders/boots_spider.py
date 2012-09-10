from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
import modules.basic_func as basic
from modules.zmags_xml import CommonXml
from modules.excel import DictExcel
from modules.exception import ZmagsException
from modules.terminal import DatabaseTerminal
from modules.export_to_db import CommonExport
from project_modules.boots import BootsItem
from datetime import datetime
import httplib
import hashlib
import urllib2
import simplejson
import sys

import re
import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

class BootsSpider(CrawlSpider):
    name = "boots"
    allowed_domains = ["zmags.com"]
    start_urls = ["http://www.zmags.com"]
    counter = 0

    def __init__(self, *a, **kw):
        super(BootsSpider, self).__init__(*a, **kw)
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
        item = BootsItem()
        item['product_id'], item['store_id'], item['lang_id'], item['catalog_id'] = self.get_ids(hxs)
        item['name'] = self.get_name(hxs)
        item['short_description'], sponsored, description, in_stock, item['ingredients'], patient_information_url, item['offer'], item['promotion'] = self.get_description(hxs)
        item['rating'] = self.get_rating(hxs)
        size, price_per_size = self.get_size(hxs)
        item['normal_image_url'], image_urls = self.get_images(hxs)
        brand, brand_image_url = self.get_brand(hxs)
        item['save_money'], item['old_price'] = self.get_oldies(hxs)
        for i in range(0, len(description)):
            tag = 'description_%d' % (i + 1)
            item[tag] = [basic.cdata(description[i])]
        if sponsored is not None:
            item['sponsored'] = sponsored
        item['in_stock'] = ["NOT_IN_STOCK"]
        if in_stock == "In stock":
            item['in_stock'] = ["IN_STOCK"]
            item['order_id'] = hxs.select('//input[@name="orderId"]/@value').extract()
            item['cat_entry_id'] = hxs.select('//input[@name="catEntryId"]/@value').extract()
            item['calculation_usage_id'] = hxs.select('//input[@name="calculationUsageId"]/@value').extract()
        if brand_image_url is not None:
            item['brand'] = brand
            item['brand_image_url'] = ["43662980-f344-11e1-a21f-0800200c9a66/full/" + self.get_image_sha1(brand_image_url)]
            image_urls.append(brand_image_url)
        if patient_information_url is not None:
            item['patient_information_url'] = [basic.cdata(patient_information_url)]
        prices, point_prices, collect_points, colors, color_image_urls, variant_ids = self.get_color_variants(hxs)
        if size is not None:
            item['size'] = size
            item['price_per_size'] = price_per_size
        elif variant_ids is None:
            prices, point_prices, collect_points, sizes, variant_ids = self.get_size_variants(hxs)
        if color_image_urls is not None:
            image_urls.extend(color_image_urls)
        if variant_ids is not None:
            self.xml.create_xml(item)
            if colors is not None:
                self.create_color_variants(prices, point_prices, colors, color_image_urls, variant_ids, collect_points, item['product_id'])
            else:
                self.create_size_variants(prices, point_prices, sizes, variant_ids, collect_points, item['product_id'])
        else:
            prices = hxs.select('//p[@class="price"]/text()').extract()[0]
            point_prices = hxs.select('//span[@class="pointsPrice"]/text()').extract()[0]
            collect_points = [basic.get_price(hxs.select('//p[@class="collectPoints"]/text()').extract()[0])]
            item['price'] = [basic.get_price(prices)]
            item['points_price'] = [basic.get_price(point_prices)]
            item['collect_points'] = collect_points
            self.xml.create_xml(item)
        item['image_urls'] = image_urls
        #raw_input("Press Enter to continue...")
        return item

    def handle_not_provided(self):
        item = BootsItem()
        for n in self.no_urls['product_ids']:
            item['product_id'] = [n]
            index = self.no_urls['product_ids'].index(n)
            item['name'] = [self.no_urls['names'][index]]
            item['in_stock'] = ['NOT_AVAILABLE']
            self.xml.create_xml(item)

    def get_ids(self, hxs):
        product_id = hxs.select('//input[@name="productId"]/@value').extract()[0]
        store_id = hxs.select('//input[@name="storeId"]/@value').extract()[0]
        lang_id = hxs.select('//input[@name="langId"]/@value').extract()[0]
        catalog_id = hxs.select('//input[@name="catalogId"]/@value').extract()[0]
        return [product_id], [store_id], [lang_id], [catalog_id]
        
    def get_name(self, hxs):
        name = hxs.select('//span[@class="pd_productNameSpan"]/text()').extract()[0]
        return [name]
    
    def get_description(self, hxs):
        short_description = hxs.select('//div[@class="productIntroCopy"]').extract()[0]
        try:
            suitable_for = ''.join(hxs.select('//div[@id="suitableFor"]//h4 | //div[@id="suitableFor"]//p | //div[@id="suitableFor"]//div').extract())
            short_description += suitable_for
        except:
            print "There's no suitable_for section"
        try:
            ingredients = basic.clean_string(' '.join(hxs.select('//div[@class="pd_panel"][not(@id)]//div[@class="pd_HTML"]/p | //div[@class="pd_panel"][not(@id)]//div[@class="pd_HTML"]//div').extract()))
            if ingredients != '':
                ingredients = basic.cdata(ingredients)
        except:
            print "No ingredients found!"
            ingredients = None
        try:
            patient_information_url = hxs.select('//div[@class="downloadMedia"]//a/@href').extract()[0]
        except:
            print "No patient information found!"
            patient_information_url = None
        try:
            offer = hxs.select('//div[@id="mainOffer"]//a/text()').extract()[0]
        except:
            print "No special offer found!"
            offer = None
        try:
            promotion = hxs.select('//div[@id="otherOffers"]//a/text()').extract()
        except:
            print "No promotion found!"
            promotion = None
        try:
            sponsored = hxs.select('//div[@class="sponsored"]//p/text()').extract()[0]
        except:
            print "No sponsor message found!"
            sponsored = None
        description = ''.join(hxs.select('//div[@id="detailedInfo"]//div[@class="pd_panelInner"]//div[@class="pd_HTML"]').extract())
        description = basic.clean_string(description)
        description_overflow = len(description)/2000
        desc = []
        if description_overflow > 0:
            for i in range(0, description_overflow + 1):
                if i < description_overflow:
                    desc.append(description[2000*(i):2000*(i+1)-1])
                else:
                    desc.append(description[2000*i:])
        else:
            desc = [description]
        try:
            in_stock = hxs.select('//div[@class="icon_pl_stock"]/text()').extract()[0]
        except:
            in_stock = ""
        return [basic.cdata(basic.clean_string(short_description))], [sponsored], desc, in_stock, [ingredients], patient_information_url, [offer], promotion
    
    def get_images(self, hxs):
        image_urls = []
        normal_image_url = hxs.select('//meta[@property="og:image"]//@content').extract()[0]
        image_urls.append(normal_image_url)
        normal_image_url = "43662980-f344-11e1-a21f-0800200c9a66/full/" + self.get_image_sha1(normal_image_url)
        return [normal_image_url], image_urls
    
    def get_brand(self, hxs):
        try:
            brand = hxs.select('//div[@class="pd_brand"]//div//a//span//img/@alt').extract()[0]
            brand_image_url = hxs.select('//div[@class="pd_brand"]//div//a//span//img/@src').extract()[0]
            return [brand], brand_image_url
        except:
            print "No brand name or image found!"
            return None, None
    
    def get_rating(self, hxs):
        try:
            rating = hxs.select('//span[@property="v:average"]/text()').extract()[0]
        except:
            rating = "0.0"
        return [rating]
    
    def get_size(self, hxs):
        try:
            size = hxs.select('//span[@class="size"]/text()').extract()[0]
            size = basic.clean_string(size)
            size = size.replace("|", "")
            price_per_size = hxs.select('//span[@class="pricePerSize"]/text()').extract()[0]
            return [size], [price_per_size]
        except:
            print "No size found"
            return None, None
        
    def get_oldies(self, hxs):
        try:
            save = hxs.select('//span[@class="save"]/text()').extract()[0]
            old = hxs.select('//span[@class="oldPrice"]/text()').extract()[0]
            save = basic.get_price(save)
            old = basic.get_price(old)
        except:
            save = None
            old = None
        return [save], [old]
            
    def get_color_variants(self, hxs):
        try:
            variants = hxs.select('//script').re('productCode:\".*\d\"')[0].split(",")
            colors = hxs.select('//div[@class="gp_80-20a column"]//div[@class="innerColumn"]//fieldset//div//label//span/text()').extract()
            color_image_urls = hxs.select('//div[@class="gp_80-20a column"]//div[@class="innerColumn"]//fieldset//div//label//img//@src').extract()
            collect_points = []
            prices = []
            point_prices = []
            variant_ids = []
            for i in range(0, len(variants), 8):
                price = basic.get_price(variants[i+2])
                prices.append(price)
                points = str(int(float(price) * 100))
                point_prices.append(points)
                variant_id = basic.get_price(variants[i])
                variant_ids.append(variant_id)
                points = basic.get_price(variants[i+5])
                collect_points.append(points)
            return prices, point_prices, collect_points, colors, color_image_urls, variant_ids
        except:
            print "No color variants found"
            return None, None, None, None, None, None
            
    def get_size_variants(self, hxs):
        try:
            variants = hxs.select('//script').re('productCode:\".*\d\"')[0].split(",")
        except:
            print "No size variants found"
            return None, None, None, None, None
        sizes = hxs.select('//select[@id="size_x"]//option/text()').extract()[1:]
        collect_points = []
        prices = []
        point_prices = []
        variant_ids = []
        for i in range(7, len(variants), 7):
            price = basic.get_price(variants[i+2])
            prices.append(price)
            points = str(int(float(price) * 100))
            point_prices.append(points)
            variant_id = basic.get_price(variants[i+4])
            variant_ids.append(variant_id)
            points = basic.get_price(variants[i+1])
            collect_points.append(points)
        return prices, point_prices, collect_points, sizes, variant_ids
    
    def create_color_variants(self, prices, point_prices, colors, color_image_urls, variant_ids, collect_points, product_id):
        for i in range(0, len(colors)):
            variant = BootsItem()
            variant['master_product_id'] = product_id
            variant['product_id'] = [variant_ids[i]]
            variant['price'] = [prices[i]]
            variant['points_price'] = [point_prices[i]]
            variant['collect_points'] = [collect_points[0]]
            variant['color'] = [colors[i]]
            variant['color_image_url'] = ["43662980-f344-11e1-a21f-0800200c9a66/full/" + self.get_image_sha1(color_image_urls[i])]
            self.xml.create_xml(variant)
            
    def create_size_variants(self, prices, point_prices, sizes, variant_ids, collect_points, product_id):
        for i in range(0, len(sizes)):
            variant = BootsItem()
            variant['master_product_id'] = product_id
            variant['product_id'] = [variant_ids[i]]
            variant['price'] = [prices[i]]
            variant['points_price'] = [point_prices[i]]
            variant['collect_points'] = [collect_points[0]]
            variant['size'] = [sizes[i]]
            self.xml.create_xml(variant)
    
    def get_image_sha1(self, image_url):
        h = hashlib.sha1()
        h.update(image_url)
        return h.hexdigest()
    
    def spider_closed(self, spider):
        """Handles spider_closed signal from end of scraping.
        Handles usual end operations for scraper like writing xml, exporting
        to database and sending appropriate mail message."""
        msg = "Ran: {0}".format(datetime.now())
        if self.counter < self.total:
            msg += "\nScraper didn't go through all products, please report"
        msg += "\n\nScraped %d product out of %d\n\n" % (self.counter, self.total)
        # filename for writing xml"""
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
                exp.xml_to_db(self.name, filename, "5097450b-2c49-49d4-b47a-55b1bc652c78")
                msg += "\n\nExport to database successful"
            except StandardError:
                msg += "\n\nExport to database failed"
        else:
            msg += "\n\nUpload to database not selected"
        ## part for exporting to database here
        from modules.mail import Mail
        mail = Mail()
        """try:
            mail.send_mail(msg, "Boots: {0}".format(filename))
            if self.d['email']:
                mail.send_mail(msg, "Boots: {0}".format(filename), self.d['email'])
        except:
            msg += "\nSending mail failed."
        if self.d['database']:
            path = "logs/{0}".format(self.name)
            if not os.path.exists(path):
                os.makedirs(path)
            with open("{0}/{1}".format(path, filename), 'w') as f:
                f.write(msg)"""

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

    def add_properties(self, xml):
        xml.add_property("in_stock", "In Stock", "text")
        xml.add_property("store_id", "Store ID", "text")
        xml.add_property("lang_id", "Lang ID", "text")
        xml.add_property("catalog_id", "Catalog ID", "text")
        xml.add_property("order_id", "Order ID", "text")
        xml.add_property("cat_entry_id", "Cat Entry ID", "text")
        xml.add_property("calculation_usage_id", "Calculation Usage ID", "text")
        xml.add_property("ingredients", "Ingredients", "text")
        xml.add_property("patient_information_url", "Patient Information Url", "text")
        xml.add_property("points_price", "Points Price", "integer")
        xml.add_property("collect_points", "Collect Points", "integer")
        xml.add_property("brand_image_url", "Brand Image Url", "text")
        xml.add_property("description_1", "Description 1", "text")
        xml.add_property("description_2", "Description 2", "text")
        xml.add_property("description_3", "Description 3", "text")
        xml.add_property("description_4", "Description 4", "text")
        xml.add_property("description_5", "Description 5", "text")
        xml.add_property("description_6", "Description 6", "text")
        xml.add_property("sponsored", "Sponsored", "text")
        xml.add_property("offer", "Offer", "text")
        xml.add_property("promotion", "Promotion", "text")
        xml.add_property("old_price", "Old Price", "decimal")
        xml.add_property("save_money", "Save Money", "decimal")
        xml.add_property("price_per_size", "Price Per Size", "text")