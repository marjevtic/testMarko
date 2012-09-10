from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
import modules.basic_func as basic
from modules.zmags_xml import CommonXml
from modules.excel import DictExcel
from modules.exception import ZmagsException
from modules.terminal import DatabaseTerminal
from project_modules.burton import BurtonItem
from modules.export_to_db import CommonExport
from scrapy.conf import settings
from modules.database import Database
from datetime import datetime
import hashlib
import urllib2
import simplejson
import sys

import re
import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
import project_modules.burton.burton_func as burton


class BurtonSpider(CrawlSpider):
    name = "burton"
    allowed_domains = ["example.com"]
    start_urls = ["http://www.example.com"]
    counter = 0

    def __init__(self, *a, **kw):
        super(BurtonSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        terminal = DatabaseTerminal(sys.argv, self.name)
        self.d = terminal.get_arguments()
        self.xml = CommonXml()
        self.exc = ZmagsException(5, "Burton")
        if self.d['database']:
            self.database = Database()
            self.database.connect()
            self.products, self.no_urls = self.database.select_products(self.d['catalog_id'],
                                                                        self.d['product_id'])
            self.database.disconnect()
        else:
            self.get_lists_from_excel()
        self.handle_not_provided()
        burton.add_properties(self.xml)
        self.start_urls = self.products['urls']
        self.start_urls = ["http://www.dickssportinggoods.com/product/index.jsp?productId=13243074"]
        self.images_store = "/" + settings['IMAGES_STORE']
        self.total = len(self.start_urls)

    def parse(self, response):
        self.counter += 1
        basic.print_status(self.counter, self.total)
        hxs = HtmlXPathSelector(response)
        item = BurtonItem()
        page = hxs.extract()
        if 'redirect_urls' in response.request.meta:
            cur_url = response.request.meta['redirect_urls'][0]
        else:
            cur_url = response.url
        index = self.products['urls'].index(cur_url)
        try:
            if 'redirect_urls' in response.request.meta:
                item['product_id'] = [self.products['product_ids'][index]]
                item['name'] = [self.products['names'][index]]
                item['in_stock'] = ["NOT_AVAILABLE"]
                self.exc.code_handler(102, response.url)
                self.xml.create_xml(item)
                self.products["status"][index] = "no_avail"
            else:
                item['product_id'], item['name'] = self.get_basic_info(hxs)
                item['description'], item['features'] = self.get_description(hxs)
                item['variants'], thumb_urls, color_names = self.get_variants(page)
                item['all_sizes'] = self.get_all_sizes(page)
                item['color_json'], image_urls = self.get_colors(page, color_names)
                item['price'], item['old_price'] = self.get_prices(hxs)
                item['in_stock'] = ['IN_STOCK']
                item['product_link'] = [basic.cdata(response.url)]
                self.xml.create_xml(item)
                item['image_urls'] = image_urls + thumb_urls
                self.products["status"][index] = "ran"
        except:
            self.exc.code_handler(100, response.url)
            self.products["status"][index] = "error"
        else:
            return item

    def handle_not_provided(self):
        item = BurtonItem()
        for n in self.no_urls['product_ids']:
            item['product_id'] = [n]
            index = self.no_urls['product_ids'].index(n)
            item['name'] = [self.no_urls['names'][index]]
            item['in_stock'] = ['NOT_AVAILABLE']
            self.xml.create_xml(item)

    def get_basic_info(self, hxs):
        name = hxs.select('//h1[@class="productHeading"]/text()').extract()
        product_id = hxs.select('//input[@name="productId"]/@value').extract()
        return product_id, name

    def get_server_path(self, url):
        path = self.images_store + "/full/" + hashlib.sha1(url).hexdigest() + ".jpg"
        return path

    def get_prices(self, hxs):
        price = hxs.select('//div[@class="op"]/text()').extract()
        price = [basic.get_price(price[0])]
        old_price = hxs.select('//span[@class="lp"]/text()').extract()
        if old_price:
            old_price = [basic.get_price(old_price[0])]
        return price, old_price

    def get_description(self, hxs):
        description = hxs.select('//div[@id="FieldsetProductInfo"]/text()').extract()[3]
        features = hxs.select('//div[@id="FieldsetProductInfo"]/ul').extract()
        if features:
            features = [features[0][:2000]]
        return [basic.cdata(description)], basic.cdata_field(features)

    def get_variants(self, page):
        """Gets jsons for colors with all available sizes.
        In json are also fetched all information for sizes that are on the site
        """
        script = basic.get_middle_text(page, 'var skuSizeColorObj = new Array();', '</script>')[0]
        sizes = []
        image_urls = []
        color_names = []
        colors = script.split('skuSizeColorObj')
        for c in range(1, len(colors)):
            temp = basic.get_middle_text(colors[c], '= ', ';')
            # delete swatch image as it obviously won't be needed
            t = simplejson.loads(burton.replace_for_json(temp[0]))
            image_urls.append(t['swatchURL'])
            color_names.append(t['ColorDesc'])
            t['swatchURL'] = self.get_server_path(t['swatchURL'])
            sizes.append(basic.cdata(simplejson.dumps(t)))
        return sizes, image_urls, color_names

    def get_all_sizes(self, page):
        script = basic.get_middle_text(page, 'var distsizeobj=new Array();', 'var indexcolor=0;')[0]
        all_sizes = basic.get_middle_text(script, ']="','";')
        return [basic.cdata(simplejson.dumps(all_sizes))]

    def get_colors(self, page, color_names):
        """Gets color information with images from javascript on the page.
        Returns  json with color name and imagself.images_store = "/" + settings['IMAGES_STORE']e url for that color, and
        returnes filed of image urls that can be used for download later"""
        script = basic.get_middle_text(page, 'var imageMap_0 = new Array();', '</script>')[0]
        colors = basic.get_middle_text(script, '] = ', ';')
        image_urls = []
        colors_json = []
        for i in range(0, len(color_names)):
            color = burton.replace_color_json(colors[i])
            color = simplejson.loads(color)
            color['cname'] = color_names[i]
            color.pop('reg')
            image_urls.append(color['enh'])
            color['enh'] = self.get_server_path(color['enh'])
            colors_json.append(basic.cdata(simplejson.dumps(color)))
        return colors_json, image_urls

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
                exp.xml_to_db(self.name, filename, "4ea95a81-90fb-49e2-837e-acf5ab58f574")
                msg += "\n\nExport to database successful"
            except StandardError:
                msg += "\n\nExport to database failed"
        else:
            msg += "\n\nUpload to database not selected"
        # part for exporting to database here
        from modules.mail import Mail
        mail = Mail()
        try:
            mail.send_mail(msg, "Burton: {0}".format(filename))
            if self.d['email']:
                mail.send_mail(msg, "Burton: {0}".format(filename), self.d['email'])
        except:
            msg += "\nSending mail failed."
        if self.d['database']:
            path = "logs/{0}".format(self.name)
            if not os.path.exists(path):
                os.makedirs(path)
            with open("{0}/{1}".format(path, filename), 'w') as f:
                f.write(msg)

    def get_lists_from_excel(self):
        xls = DictExcel(basic.get_excel_path(self.name, self.d['file']))
        self.products = dict()
        try:
            self.products["urls"] = xls.read_excel_collumn_for_urls(3, 15)
            self.products["product_ids"] = xls.read_excel_collumn_for_ids(1, 15)
            self.products["names"] = xls.read_excel_collumn(2, 15)
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
