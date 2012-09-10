from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
from project_modules.partylite import PartyliteItem
from modules.zmags_xml import CommonXml
from modules.excel import DictExcel
from scrapy.http import Request
import hashlib
import urllib2
import simplejson
import os
import re
import sys
from project_modules.partylite.terminal import PartyliteTerminal
from project_modules.partylite.excel import PartyliteExcel
from modules.exception import ZmagsException
import modules.basic_func as basic
import project_modules.partylite.party as party
from modules.database import Database

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.conf import settings


#Partylite spider specs:
#   partylite spider can be called with options (env, lang and upload) to
#   select options for running (production/development, english/french, yes/no
#   upload to database), catalog name for which to scrape default values are:
#   production, english, yes upload and catalog name that is kept in settings
#   and can be changed if needed
#   and catalog name for which to scrape
#   example of calling spider:
#
#   scrapy crawl partylite -a lang=french -a env=dev -a upload=no -a file=WS12
#
#   this will call spider on development environment (qa.) for usa and canada
#   french and will not upload automatically to database and will run scraper
#   for catalog name WS12 (note that catalog name is actually name of the
#   excel file where products are kept for certain catalog)
#   another example:
#
#               scrapy crawl partylite -a lang=french -a file=Halloween
#
#   this one will scrape french on production for Halloween catalog and will
#   upload as yes upload, production is a default value
#   if not language added it will scrape for us, if language provided it will
#   scrape
#
#   users used for scraping are kept in project_modules.partylite.settings
#   and can be modified in there if needed
#
#   xls names available for partylite
#       - WS12_1
#       - Fall_Holiday
#       - Halloween
#       - FH12_CA-FR


class PartyliteSpider(CrawlSpider):
    name = "partylite"
    allowed_domains = ["partylite.biz"]
    start_urls = ["http://www.zmags.com"]
    counter = 0

    def __init__(self, *a, **kw):
        super(PartyliteSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        terminal = PartyliteTerminal(sys.argv, self.name)
        self.d = terminal.get_arguments()
        self.images_store = "/" + settings['IMAGES_STORE']
        self.users = party.get_users(settings, self.d)
        self.exc = ZmagsException(50)
        self.production = self.d['env']
        self.upload = self.d['upload']
        self.english = self.d['lang']
        self.file_name = self.d['file']
        if self.d['database']:
            self.database = Database()
            self.database.connect()
            self.products, self.no_urls = self.database.select_products(self.d['catalog_id'],
                                                                        self.d['product_id'])
            self.database.disconnect()
            self.change_url_list()
        else:
            self.get_lists_from_excel()
        self.xml = CommonXml()
        party.add_properties(self.xml)
        self.total = len(self.products['urls'])

    def parse(self, response):

        for url in self.products['urls']:

            if self.d['lang'] == 'us':
                request = Request(url, callback=self.parse_can, dont_filter=True)
                yield request

            elif self.d['lang'] == 'english':
                c_url = url.replace(self.users['us'], self.users['canada_en'])
                request = Request(c_url, callback=self.parse_can, dont_filter=True)
                request.meta['language'] = "eng"
                yield request

            elif self.d['lang'] == 'french':
                c_url = url.replace(self.users['us'], self.users['canada_fr'])
                request = Request(c_url, callback=self.parse_can, dont_filter=True)
                request.meta['language'] = "fr"
                yield request

    def change_url_list(self):
        for i in range(0, len(self.products['urls'])):
            if not self.production:
                self.products['urls'][i] = self.products['urls'][i].replace('www', 'qa')
            self.products['urls'][i] = self.products['urls'][i].replace('XXXXX', self.users['us'])

    def get_in_stock(self, hxs):
        """Gets in stock information about product."""
        stock = hxs.select('//div[@id="availability_container"]').extract()
        if not stock:
            return ["IN_STOCK"]
        else:
            return ["NOT_IN_STOCK"]

    def get_basic_info(self, hxs):
        """Getting basic info about products (name, shown with)."""
        name = hxs.select('//div[@id="product_name"]/text()').extract()
        if name:
            name = basic.cdata_field(name)
        shown_with = hxs.select('//div[@id="shown_with_container"]').extract()
        if shown_with:
            shown_with = [basic.cdata(shown_with[0])]
        return name, shown_with

    def get_description(self, hxs):
        description = description = hxs.select('//div[@id="item_description"]').extract()
        description = [basic.cdata(basic.remove_tags(description[0]))]
        description = [description[0].replace(u"\u2044", "/")]
        return description

    def get_price(self, hxs):
        """Getting product prices.
        Gets regular and discount price if there is one."""
        price = hxs.select('//span[@id="divUnitPrice"]/text()').extract()
        if not price:
            price = hxs.select('//div[@id="product_price"]/span[1]/text()').extract()
        if not price:
            price = hxs.select('//div[@id="product_price"]/text()').extract()
        discount = hxs.select('//div[@id="product_price"]/span[@class="pc-salePrice"]/text()').extract()
        price = basic.clean_string(price[0])
        price = re.sub(" +", " ", price)
        price = price.replace("Price:", "")
        price = price.replace("Prix:", "")
        price = basic.cdata(price.strip())
        if discount:
            discount = basic.cdata_field(discount)
        return [price], discount

    def get_add_to_cart_id(self, page):
        """Gets add to cart id from the javascript on the page."""
        tmp = basic.get_middle_text(page, "if(isOrderStarted){", "}else")[0]
        tmp = basic.get_middle_text(tmp, "addItemToCart(", ",")
        return tmp

    def create_subproducts(self, page):
        """Gets information about colors from javascript.
        Returns field of dicts with information about colors.
        Those are really color variants for product."""
        try:
            tmp = page.split("var largeImages = new Array();")[1]
        except IndexError:
            print "This product has no images"
        else:
            tmp = tmp.split("colorDropdownArray")[0]
            images = basic.get_middle_text(tmp, "ProductGroupProduct(", ");")
            image_names = self.get_image_names(page)
            color_products = []
            for im in images:
                product = {}
                attributes = im.split("',")
                product['normal_image_url'] = "http://qa.partylite.biz/imaging/resize?fileName=/productcatalog/production"
                product['normal_image_url'] += self.custom_clean_string(attributes[26], True)
                product['description'] = basic.cdata(self.custom_clean_string(attributes[27]))
                product['color_id'] = self.custom_clean_string(attributes[7], True)
                product['swatch_color'] = basic.cdata(self.custom_clean_string(attributes[9]).replace(" ", ""))
                product['name'] = basic.cdata(image_names[product['color_id']])
                product['add_to_cart_id'] = self.custom_clean_string(attributes[0], True).replace(" ", "")
                product['price'] = self.custom_clean_string(attributes[10], True)
                color_products.append(product)
            return color_products
        return []

    def custom_clean_string(self, string, spaces=False):
        """Custom function for cleaning strings.
        Replaces new line, return and tab signs, also replaces multiple spaces with only one."""
        string = string.replace("\r", "")
        string = string.replace("\n", "")
        string = string.replace("\t", "")
        if not spaces:
            string = re.sub(' +', ' ', string)
        else:
            string = re.sub(' ', '', string)
        string = string.replace("'", "")
        return string

    def get_image_names(self, page):
        """Gets color names for color swatches."""
        temp = page.split("new DropDownInfo")
        names = {}
        for i in range(1, len(temp)):
            names[basic.get_middle_text(temp[i], "('", "'")[0]] = basic.get_middle_text(temp[i], "'", "')")[2]
        return  names

    def get_recommended(self, hxs):
        """Gets recommended product information.
        Returns information about recommended products as dict"""
        rec = hxs.select('//div[@id="right_column_container"]/div')
        new = []
        i = 0
        for r in rec:
            d = {}
            #to do: see how to get full href(different accounts)
            if not i:
                d['link'] = r.select('div/a/@href').extract()[0]
                d['image'] = "http://www.partylite.biz/imaging/resize"
                d['image'] += r.select('div/a/img/@src').extract()[0]
                d['name'] = r.select('div/a/text()').extract()[0]
                new.append(basic.cdata(simplejson.dumps(d)))
            i += 1
        return  new

    def get_reviews(self, page):
        """Gets average product rating.
        Returns string like 4.6 of 5 reviews."""
        id = self.get_review_id(page)
        url = "http://partylite.ugc.bazaarvoice.com/8504-en_us/" + id + "/reviews.djs?format=embeddedhtml"
        url = url.replace(" ", "")
        page = urllib2.urlopen(url).read()
        page = basic.get_middle_text(page, '<div class=\\"BVRRRatingNormalImage\\">', '<\/div>')
        if page:
            rating = basic.get_middle_text(page[0], 'alt=\\"', '\\"')[0]
            return [rating]
        else:
            return []

    def get_more_images(self, page):
        """Gets field of images."""
        try:
            script = basic.get_middle_text(page, "var moreImages", "var numberOfImages")[0]
        except IndexError:
            print "This product has no images."
        else:
            r = basic.get_middle_text(script, "moreImages[", "';")
            images = []
            # return cdata here if needed to go with absolute links
            for i in range(0, len(r)):
                if self.production:
                    images.append("http://www.partylite.biz" + r[i].split("= '")[1])
                else:
                    images.append("http://qa.partylite.biz" + r[i].split("= '")[1])
            return images
        return []

    def get_absolute(self, relatives):
        """Creates absolute path for images. [DEPRECATED]
        Please check if there is a need for this function again.
        If needed dimensions of images got from the client server
        can be changed here."""
        new = []
        print relatives
        os._exit(0)
        for i in range(0, len(relatives)):
            #add width, height here for different dimensions
            #don't change the url in here from qa to www it's meant to be qa always
            new.append("http://www.partylite.biz/imaging/resize?fileName=/productcatalog/production" + relatives[i])
        return new

    def get_review_id(self, page):
        """Gets review id that is used in javascript for reviews."""
        return basic.get_middle_text(page, 'productId: "', '"')[0]

    def write_subproducts(self, id, list, xml):
        """Writes child products to xml.
        Receives id, list and xml attributes, id is master product id,
        list is list of child products and xml is Xml instance"""
        for i in range(0, len(list)):
            item = PartyliteItem()
            item['master_product_id'] = id
            item['product_id'] = [id[0] + "_" + str(i)]
            item['in_stock'] = ["IN_STOCK"]
            for k, v in list[i].iteritems():
                item[k] = [v]
            xml.create_xml(item)
        return 1

    def parse_can(self, response):
        """Parse function for scraping canadian sites.
        There is meta information send in request in this function about language."""
        self.counter += 1
        basic.print_status(self.counter, self.total)
        item = PartyliteItem()
        hxs = HtmlXPathSelector(response)
        image_urls = []
        if  'redirect_urls' in response.request.meta:
            item['product_id'] = [self.get_id(response.request.meta['redirect_urls'][0])[0]]
            self.exc.code_handler(102, response.request.meta['redirect_urls'])
            if 'language' in response.request.meta:
                item['product_id'] = [self.get_id(response.request.meta['redirect_urls'][0])[0]
                                      + "_can" + "_" + response.meta['language']]
            try:
                index = self.products['product_ids'].index(self.get_id
                                (response.request.meta['redirect_urls'][0])[0])
                item['name'] = [basic.cdata(item['product_id'][0]
                                + self.products['names'][index])]
                self.products['status'][index] = 'no_avail'
            except KeyError as e:
                print "This %s id is not in list" % (item['product_id'][0])
            item['in_stock'] = ['NOT_AVAILABLE']
            item['product_id'] = self.remove_spaces(item['product_id'])
            self.xml.create_xml(item)
        else:
            index = self.products['product_ids'].index(self.get_id(response.url)[0])
            try:
                item['product_id'] = self.get_id(response.url)
                item['name'], item['shown_with'] = self.get_basic_info(hxs)
                item['description'] = self.get_description(hxs)
                if 'language' in response.meta:
                    item['product_id'] = [item['product_id'][0] + "_can" + "_" + response.meta['language']]
                response.meta['item'] = item
                page = " ".join(hxs.select('//html').extract())
                image_urls = self.get_more_images(page)
                item['normal_image_url'] = self.get_server_path_field(image_urls)
                item['in_stock'] = self.get_in_stock(hxs)
                color_products = self.create_subproducts(page)
                if color_products:
                    self.write_subproducts(item['product_id'], color_products, xml)
                else:
                    item['add_to_cart_id'] = self.get_add_to_cart_id(page)
                    item['custom_price'], item['custom_discount'] = self.get_price(hxs)
                self.products['status'][index] = "ran"
            except StandardError:
                basic.print_error()
                self.products['status'][index] = "error"
                self.exc.code_handler(100, response.url)
            else:
                item['product_id'] = self.remove_spaces(item['product_id'])
                self.xml.create_xml(item)
        if image_urls:
            item['image_urls'] = image_urls
        return item

    def spider_closed(self, spider):
        """Handles spider_closed signal from end of scraping.
        Handles usual end operations for scraper like writing xml, exporting
        to database and sending appropriate mail message."""
        msg = party.get_settings_message(self.d)
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
        logname = filename
        filename = "{0}_{1}".format(filename, self.d['lang'])
        self.xml.write_xml(self.name, filename)
        msg += self.exc.create_message(self.counter)
        from modules.mail import Mail
        from modules.export_to_db import CommonExport
        exp = CommonExport()
        if self.upload:
            try:
                if self.d['lang'] == 'us':
                    exp.xml_to_db(self.name, filename, "55892247-1b92-4ff9-a8a3-33cc976f9341")
                else:
                    exp.xml_to_db(self.name, filename, "9cb6c676-c14f-403b-b94f-b981184e1de0")
                msg += "\n\nExport to database successful"
            except StandardError:
                msg += "\n\nExport to database failed"
        else:
            msg += "\n\nUpload to database not selected"
        mail = Mail()
        try:
            mail.send_mail(msg, "Partylite: {0}".format(filename))
            if self.d['email']:
                mail.send_mail(msg, "Partylite: {0}".format(filename), self.d['email'])
        except:
            msg += "\nSending mail failed."
        if self.d['database']:
            path = 'logs/{0}'.format(self.name)
            if not os.path.exists(path):
                os.makedirs(path)
            with open("{0}/{1}".format(path, logname), 'w') as f:
                f.write(msg)

    def get_id(self, url):
        """Gets id from product url."""
        return [url.split("&sku=")[1]]

    def get_server_path(self, url):
        """Gets server path for image url."""
        url = url.split("partylite.biz")[1]
        return self.images_store + "/full/" + hashlib.sha1(url).hexdigest() + ".jpg"

    def get_server_path_field(self, urls):
        """Getting server path for field of image urls."""
        new = []
        for url in urls:
            url = url.split("partylite.biz")[1]
            new.append(self.images_store + "/full/" + hashlib.sha1(url).hexdigest() + ".jpg")
        return new

    def remove_spaces(self, field):
        new = []
        for i in field:
            new.append(i.replace(' ', ''))
        return new

    def get_lists_from_excel(self):
        excel_path = "xls/{0}/{1}.xls".format(self.name, self.d['file'])
        xls = PartyliteExcel(path=excel_path, user=self.users['us'], production=self.production)
        self.products = dict()
        try:
            self.products['urls'] = xls.read_excel_collumn_for_urls(3, 15)
            self.products['product_ids'] = xls.read_excel_collumn_for_ids(1, 15)
            self.products['names'] = xls.read_excel_collumn(2, 15)
        except IOError as e:
            msg = "I/O error {0}: {1}".format(e.errno, e.strerror)
            msg += "\nError occurred for given file: {0}".format(self.d['file'])
            exc.code_handler(103, msg=msg)
        except StandardError:
            msg = "Error reading excel file"
            msg += "\nError occurred for given file: {0}".format(self.d['file'])
            exc.code_handler(103, msg=msg)
        self.products= xls.delete_duplicates_dict(self.products)
        self.products, self.no_urls = xls.separate_no_urls(self.products)
        self.products = xls._add_none_status(self.products)
        self.no_urls = xls._add_none_status(self.no_urls)
