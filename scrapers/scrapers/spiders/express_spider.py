from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
import modules.basic_func as basic
from modules.zmags_xml import VariantsXml
from modules.excel import CommonExcel
from modules.exception import ZmagsException
from modules.terminal import CommonTerminal
from project_modules.express import ExpressItem
from project_modules.express.shop import CreateShops
from modules.export_to_db import CommonExport
from modules.messaging import Logger
import hashlib
import urllib2
import simplejson
import sys

import re
import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals


class ExpressSpider(CrawlSpider):
    name = "express"
    allowed_domains = ["example.com"]
    start_urls = ["http://www.example.com"]
    temp_msg = ""
    handle_httpstatus_list = [404]
    counter = 0

    def __init__(self, *a, **kw):
        super(ExpressSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        terminal = CommonTerminal(sys.argv, self.name)
        self.log = Logger()
        self.d = terminal.get_arguments()
        self.xml = VariantsXml()
        self.exc = ZmagsException(5)
        shops = CreateShops(self.d['file'], self.xml)
        try:
            shops.get()
        except IndexError:
            print "This sheet has no shop look or line"
        self.get_lists_from_excel()
        self.add_properties(self.xml)
        self.start_urls = self.url_list[:2]
        self.total = len(self.start_urls)

    def parse(self, response):
        self.counter += 1
        basic.print_status(self.counter, self.total)
        hxs = HtmlXPathSelector(response)
        item = ExpressItem()
        index = self.url_list.index(response.url)
        self.url_list[index] = self.counter
        flag = 0
        shop_look = 0
        # main try that catches all unhandled errors
        try:
            hxs = HtmlXPathSelector(response)
            if response.url != "http://www.zmags.com/":
                error_404 = hxs.select('//img[@alt="404 Error Page Not Found"]').extract()
                flag = 1
                if not error_404:
                    flag = 1
                    available = hxs.select('//span[@class="glo-tex-error"]/text()').extract()
                    page = " ".join(hxs.select('//html').extract())
                    #part for creating main product in xml
                    id = self.get_product_id(hxs)[0]
                    if id != self.id_list[index]:
                        msg = "\nNot equal, id in sheet {0}, on site {1}".format(self.id_list[index], id)
                        self.temp_msg += msg
                    item['product_id'] = [id]
                    item['name'] = self.get_name(hxs)
                    item['description'], item['promo_text'] = self.get_basic_info(hxs)
                    item['master_price'], item['discount_price'] = self.get_product_prices(hxs)
                    item['shop_look'] = ['False']
                    item['normal'] = ['True']
                    item['shop_line'] = ['False']
                    item['in_stock'] = ["NOT_IN_STOCK"]
                    if available[0] != "This item is no longer available for purchase.":
                        item['category_id'], item['subcategory_id'] = self.get_categories(hxs)
                        item['add_to_cart_id'] = self.get_add_to_cart_id(hxs)
                        color_names, urls, swatch_image_names, jsons = self.get_swatch_images(hxs)
                        #urls = basic.cdata_field(self.map_url_to_server(urls, id, True))
                        item['color_image_url'] = self.create_color_json(urls, color_names)
                        item['in_stock'] = ["IN_STOCK"]
                        item['product_page'] = [response.url]
                        self.xml.create_xml(item)
                        product_images, images_grouped = self.parse_jsons(jsons, color_names)
                        ids, sizes, prices = self.get_variants(page)
                        # calling function that will handle creating all child products
                        self.create_child_products(id, ids, sizes, prices, images_grouped)
                        item['image_urls'] = urls + product_images
                        if self.shop_look_list[index]:
                            self.parse_for_shop_look(hxs, self.shop_look_list[index],
                                                     id, page, images_grouped, response.url, index)
                        if self.shop_line_list[index]:
                            self.parse_for_shop_look(hxs, self.shop_line_list[index],
                                                     id, page, images_grouped, response.url, index)
                    else:
                        self.xml.create_xml(item)
                        self.exc.code_handler(102, response.url)

                else:
                    self.exc.code_handler(104, response.url)
            else:
                basic.not_provided()
                self.exc.code_handler(101, response.url)
            if not flag:
                item['product_id'] = [self.id_list[index]]
                item['in_stock'] = ["NOT_AVAILABLE"]
                item['name'] = ["not available"]
                self.xml.create_xml(item)
        except StandardError:
            self.exc.code_handler(100, response.url)
        #if it's last product write xml and run end_operations
        return item

    def parse_for_shop_look(self, hxs, id, product_id, page, images_grouped, product_url, index):
        """Special parse function for shop looks and lines.
        It gets same info stored in different format, mostly json and reference
        to master product id that is actually shop look/line id.
        TO DO: see if there is need to specially handle the case
        for not available"""
        item = ExpressItem()
        item['master_product_id'] = [id]
        item['product_id'] = [id + "_" + product_id]
        if self.ordered:
            item['order_index'] = [self.order_list[index]]
        item['style'] = [product_id]
        item['product_page'] = [product_url]
        item['category_id'], item['subcategory_id'] = self.get_categories(hxs)
        item['add_to_cart_id'] = self.get_add_to_cart_id(hxs)
        # below is part fot creating swatch images and images json
        color_names, urls, swatch_image_names, jsons = self.get_swatch_images(hxs)
        i = 0
        colors = []
        for k in color_names:
            d = {'name': k, 'swatch_url': urls[i], 'image_url': self.get_absolute_url(images_grouped[k])}
            i += 1
            colors.append(simplejson.dumps(d))
        item['colors'] = basic.cdata_field(colors)
        item['price'], item['discount_price'] = self.get_product_prices(hxs)
        item['description'], item['promo_text'] = self.get_basic_info(hxs)
        item['name'] = self.get_name(hxs)
        # below is part for creating variants json
        ids, sizes, prices = self.get_variants(page)
        variants = []
        for k in ids:
            d = {'color': k, 'prices': prices[k], 'ids': ids[k]}
            try:
                d['sizes'] = sizes[k]
            except StandardError:
                print "This product has no sizes"
            variants.append(simplejson.dumps(d))
        item['variants'] = basic.cdata_field(variants)
        self.xml.create_xml(item)

    def parse_shop_look(self, hxs):
        products = hxs.select('//div[@id="cat-ens-prod-item"]')
        i = 0
        # do this with actual id
        item = ExpressItem()
        whole_page = hxs.extract()
        whole_page = "".join(whole_page)
        ensemble_id = basic.get_middle_text(whole_page, "ensembleId: '", "',")
        name = hxs.select('//div[@id="cat-ens-prod-con"]/h1/text()').extract()
        name = basic.clean_string_field(name)
        item['ensemble_id'] = ensemble_id
        item['normal_image_url'] = self.shl_get_image(hxs)
        item['product_id'] = ["DUMMIE1"]
        item['shop_look'] = ['True']
        item['normal'] = ['False']
        item['shop_line'] = ['False']
        item['in_stock'] = ['IN_STOCK']
        item['name'] = name
        xml.create_xml(item)
        item.clear()
        for p in products:
            i += 1
            item = ExpressItem()
            item['master_product_id'] = ['DUMMIE1']
            item['product_id'] = ["DUMMIE1_" + str(i)]
            item['name'], item['price'], item['style'] = self.shl_basic_info(p)
            page = p.extract()
            item['variants'] = basic.cdata_field([self.shl_create_variants(self.get_variants(page))])
            item['colors'] = basic.cdata_field(self.shl_get_swatches(p))
            xml.create_xml(item)
        # return images for download here once it's needed

    def get_categories(self, hxs):
        category_id = hxs.select('//input[@name="categoryId"]/@value').extract()
        sub_category_id = hxs.select('//input[@name="subCategoryId"]/@value').extract()
        return category_id, sub_category_id

    def get_add_to_cart_id(self, hxs):
        return hxs.select('//input[@name="productId"]/@value').extract()

    def shl_get_image(self, hxs):
        page = hxs.extract()
        image = basic.get_middle_text(page, 'imagesets = "', '";')
        image = "http://t.express.com/com/scene7/s7d5/=/is/image/expressfashion/%s/i81" % (image[0])
        return [image]

    def shl_create_variants(self, f):
        """Creates variants for shop look products.
        Stored in dict with all info and returned as json"""
        d_main = {}
        n = []
        colors = [p for p in f[0]]
        for c in colors:
            d = {'color': c, 'ids': f[0][c]}
            try:
                d['sizes'] = f[1][c]
            except StandardError:
                print "This product has no sizes"
            d['prices'] = f[2][c]
            n.append(d)
        d_main['variants'] = n
        return simplejson.dumps(n)

    def shl_get_swatches(self, hxs):
        """Function for getting swatches for shop look way.
        Stores information in dict (name, swatch_url and image url)"""
        p = hxs.select('div[@class="cat-ens-prod-info"]/div[@class="cat-ens-prod-swatch-display"]')
        p = p.select('span/text()').extract()
        l = []
        d = {}
        for c in p:
            temp = c.split(",")
            d['name'] = temp[0]
            d['swatch_url'] = temp[1]
            d['image_url'] = temp[2]
            l.append(simplejson.dumps(d))
        return l

    def shl_basic_info(self, hxs):
        name = hxs.select('div[@class="cat-ens-prod-info"]/h1/text()').extract()
        name = basic.clean_string_field(name)
        price = hxs.select('div[@class="cat-ens-prod-info"]/span/text()').extract()
        price = basic.clean_spaces_field(basic.clean_string_field(price))
        style = hxs.select('div[@class="cat-ens-prod-info"]/text()').extract()
        if len(style) > 2:
            style = [basic.clean_string(style[1])]
        else:
            style = []
        return name, price, style

    def create_color_json(self, urls, names):
        d = {}
        n = []
        for i in range(0, len(urls)):
            d['url'] = urls[i]
            d['name'] = names[i]
            n.append(simplejson.dumps(d))
        return n

    def get_basic_info(self, hxs):
        """Gets basic info about products.
        Returns description and promo text"""
        description = hxs.select('//li[@class="cat-pro-desc"]').extract()[0]
        description = basic.clean_string(description)
        description = [basic.cdata(description)]
        promo_text = hxs.select('//span[@class="cat-pro-promo-text"]/text()').extract()
        if not promo_text:
            promo_text = hxs.select('//span[@class="cat-pro-promo-text"]/font').extract()
        if promo_text:
            promo_text = basic.cdata_field(promo_text)
        return description, promo_text

    def get_name(self, hxs):
        name = hxs.select('//div[@id="cat-pro-con-detail"]/h1/text()').extract()[0]
        name = [basic.clean_string(name)]
        return name

    def get_product_prices(self, hxs):
        """Gets product prices, regular and discount if it exists.
        If no discount returns empty field."""
        price = hxs.select('//li[@class="cat-pro-price"]/strong/text()').extract()
        discount_price = []
        if not price:
            price = hxs.select('//li[@class="cat-pro-price"]/span[@class="cat-glo-tex-oldP"]/text()').extract()
            discount_price = hxs.select('//li[@class="cat-pro-price"]/span[@class="cat-glo-tex-saleP"]/text()').extract()
        if discount_price:
            discount_price = [re.sub('[^0-9.,]', '', discount_price[0])]
        price = [re.sub('[^0-9.,]', '', price[0])]
        return price, discount_price

    def get_product_id(self, hxs):
        """Gets product sku from the page as a field"""
        sku = hxs.select('//input[@name="omnitureStyleID"]/@value').extract()[0]
        sku = sku.replace(";", "")
        return [sku]

    def get_swatch_images(self, hxs):
        """Function for getting swatch images info (names, urls, image names and urls).
        Also it gets and json as list of json urls for getting images set for every color."""
        urls = hxs.select('//li[@id="widget-product-swatches"]/a/img/@src').extract()
        color_names = hxs.select('//li[@id="widget-product-swatches"]/a/img/@alt').extract()
        swatch_image_names = self.get_swatch_image_name(urls)
        if not swatch_image_names and not color_names:
            color_names.append("no_color")
            swatch_image_names = self.get_imagesets(hxs)
        jsons = self.get_json(swatch_image_names)
        return color_names, urls, swatch_image_names, jsons

    def get_imagesets(self, hxs):
        """Function for getting image set in case where there is no color for product.
        Gets image set info from the javascript on the page and selects only first one,
        if there is more because there is only one color to associate with (no_color)"""
        page = hxs.extract()
        print len(page)
        iset = basic.get_middle_text(page, 'imagesets = "', '"; //Change')
        iset = iset[0].split(',')
        return [iset[0]]

    def get_swatch_image_name(self, image_sites):
        """Gets swatch image name from swatch image url"""
        image_names = []
        for x in range(0, len(image_sites)):
            name = basic.get_middle_text(image_sites[x], "fashion/", "_s")[0]
            image_names.append(name)
        return image_names

    def get_json(self, image_names):
        """Gets list of jsons from list of swatch images names"""
        jsons = []
        for i in range(0, len(image_names)):
            json = "http://s7d5.scene7.com/is/image/expressfashion/" + image_names[i] + "?req=imageset,json"
            jsons.append(json)
        return jsons

    def parse_jsons(self, jsons, color_names):
        """Parsing json from json urls.
        Returning all images in field, also returns them grouped by colors,
        so those groups can be used later when creating child products in xml"""
        images = []
        images_grouped = {}
        for i in range(0, len(jsons)):
            json = urllib2.urlopen(jsons[i]).read()
            image = basic.get_middle_text(json, '"expressfashion/', ";")
            rest_of_images = basic.get_middle_text(json, ',expressfashion/', ";")
            temp = image + rest_of_images
            images_grouped = basic.add_to_dict(images_grouped, color_names[i], temp)
            images += temp
        return self.get_absolute_url(images), images_grouped

    def get_absolute_url(self, images):
        """Gets absolute path for images.
        Receives field of relative path images and returns absolute paths"""
        image_urls = []
        for x in range(0, len(images)):
            image_url = "http://s7d5.scene7.com/is/image/expressfashion/" + images[x]
            image_url += "?width=351"
            image_urls.append(image_url)
        return image_urls

    def get_variants(self, page):
        """Getting variants from javascript on the page.
        Returns three dicts ids, sizes and prices. Format of the dicts is like
        (key = color, value = field of (ids, sizes and prices))"""
        temp = page.split("// Load the product variants")[1]
        temp = temp.split("// Set the field to update with the product variant")[0]
        variants = temp.split("// Create the variant")
        sizes = {}
        ids = {}
        prices = {}
        for i in range(1, len(variants)):
            color = basic.get_middle_text(variants[i], "Color','", "')")
            if color:
                color = color[0]
            else:
                color = "no_color"
            ids = basic.add_to_dict(ids, color, basic.get_middle_text(variants[i], "setId('", "')")[0])
            if variants[i].find("Size','") != -1:
                sizes = basic.add_to_dict(sizes, color, basic.get_middle_text(variants[i], "Size','", "')")[0])
            prices = basic.add_to_dict(prices, color, basic.get_middle_text(variants[i], 'numericPrice="', '"')[0])
        return ids, sizes, prices

    def get_image_url(self, images, is_swatch=False):
        """Returns path for images on our servers.
        If it's for swatch it return also swatch paths."""
        image_paths = []
        thumb_paths = []
        for x in range(0, len(images)):
            path = normal_image_url + images[x] + ".jpg"
            thumb_path = thumb_image_url + images[x] + ".jpg"
            image_paths.append(path)
            thumb_paths.append(thumb_path)
        if is_swatch is True:
            return image_paths
        else:
            return image_paths, thumb_paths

    def create_child_products(self, main_id, ids, sizes, prices, images_grouped):
        """Creating child products (both colors and sizes).
        Arguments it gets are: main_id as product id of the master product,
        images_grouped that is a dict of images grouped by color (field i field)
        and dicts ids, sizes and prices (e.g. dict with color names as keys and
        fields of ids for it as values 'black': ['32854, '32855''])"""
        item = ExpressItem()
        i = 0
        for k in ids:
            cur_id = main_id + "_" + chr(i + 97)
            item['product_id'] = [cur_id]
            item['master_product_id'] = [main_id]
            item['color'] = [k]
            # use this for some other path (our server)
#            images, thumbs = self.get_image_url(images_grouped[i])
            if images_grouped:
                images = self.get_absolute_url(images_grouped[k])
    #            item['normal_image_url'], item['thumb_image_url'] = self.map_url_to_server(images,main_id)
                item['normal_image_url'] = basic.cdata_field(self.map_url_to_server(images, main_id))
            self.xml.create_xml(item)
            item.clear()
            j = 0
            for val in ids[k]:
                item['product_id'] = [cur_id + "_" + chr(j + 97)]
                item['master_product_id'] = [cur_id]
                if len(sizes):
                    item['size'] = [sizes[k][j]]
                item['size_option_id'] = [ids[k][j]]
                item['price'] = [prices[k][j]]
                self.xml.create_xml(item)
                j += 1
            i += 1

    def map_url_to_server(self, urls, main_id, is_swatch=False):
        return urls
        new = []
        new1 = []
        for i in range(0, len(urls)):
            new.append(image_path + "/" + main_id + "/full/" + hashlib.sha1(urls[i]).hexdigest() + ".jpg")
            if is_swatch is False:
                new1.append(image_path + "/" + main_id + "/thumb/" + hashlib.sha1(urls[i]).hexdigest() + ".jpg")
        if is_swatch is True:
            return new
        else:
            return new, new1

    def spider_closed(self, spider):
        """Handles spider_closed signal from end of scraping.
        Handles usual end operations for scraper like writing xml, exporting
        to database and sending appropriate mail message."""
        msg = ""
        if self.counter < self.total:
            msg += "\nScraper didn't go through all products, please report"
        msg += "\n\nScraped %d product out of %d\n\n" % (self.counter, self.total)
        # filename for writing xml
        self.xml.write_xml(self.name, self.d['file'])
        msg += self.exc.create_message(self.counter)
        msg += "\n{0}".format(self.temp_msg)
        exp = CommonExport()
        # part for exporting to database here
        if self.d['upload']:
            try:
                exp.xml_to_db(self.name, self.d['file'], "e2b3b658-16d5-4059-a9df-3c212c817d2c")
                msg += "\n\nExport to database successful"
            except StandardError:
                msg += "\n\nExport to database failed"
        else:
            msg += "\n\nUpload to database not selected"
        msg += self.log.get_message()
        from modules.mail import Mail
        mail = Mail()
        mail.send_mail(msg, "Express scraper report")

    def get_lists_from_excel(self):
        xls = CommonExcel(basic.get_excel_path(self.name, self.d['file']))
        self.ordered = True
        try:
            self.url_list = xls.read_excel_collumn_for_urls(4, 1)
            self.id_list = xls.read_excel_collumn_for_ids(0, 1)
            self.shop_look_list = xls.read_excel_collumn(1, 1)
            self.shop_line_list = xls.read_excel_collumn(2, 1)
            try:
                self.order_list = xls.read_excel_collumn_for_ids(6, 1)
            except:
                self.ordered = False
                self.log.add_message("No order provided in this sheet.")
        except IOError as e:
            msg = "I/O error {0}: {1}".format(e.errno, e.strerror)
            msg += "\nError occurred for given file: {0}".format(self.d['file'])
            self.exc.code_handler(103, msg=msg)
        except StandardError:
            msg = "Error reading excel file"
            msg += "\nError occurred for given file: {0}".format(self.d['file'])
            self.exc.code_handler(103, msg=msg)

    def add_properties(self, xml):
        xml.add_property("size_option_id", "Size Option Id", "text")
        xml.add_property("color_image_url", "Color Image Url", "text_list")
        xml.add_property("colors", "Colors", "text_list")
        xml.add_property("variants", "Variants", "text_list")
        xml.add_property("style", "Style", "text")
        xml.add_property("mode", "Mode", "text")
        xml.add_property("shop_look", "Shop look", "boolean")
        xml.add_property("shop_line", "Shop line", "boolean")
        xml.add_property("normal", "Normal", "boolean")
        xml.add_property("ensemble_id", "Ensemble ID", "text")
        xml.add_property("promo_text", "Promo text", "text")
        xml.add_property("in_stock", "In Stock", "text")
        xml.add_property("product_page", "Product page", "text")
        xml.add_property("master_price", "Master Price", "decimal")
        xml.add_property("subcategory_id", "Sub Category ID", "text")
        xml.add_property("add_to_cart_id", "Add to cart ID", "text")
        xml.add_property("order_index", "Order Index", "integer")
