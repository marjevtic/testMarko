from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
import modules.basic_func as basic
from modules.zmags_xml import VariantsXml
from modules.excel import DictExcel
from modules.exception import ZmagsException
from modules.terminal import DatabaseTerminal
from project_modules.lydias import LydiasItem
from modules.export_to_db import CommonExport
from modules.database import Database
import project_modules.lydias.lydias as lydias
import hashlib
import urllib2
import simplejson
import sys

import re
import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.conf import settings


class LydiasSpider(CrawlSpider):
    name = "lydias"
    allowed_domains = ["example.com"]
    start_urls = ["http://www.example.com"]
    counter = 0

    def __init__(self, *a, **kw):
        super(LydiasSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        terminal = DatabaseTerminal(sys.argv, self.name)
        self.d = terminal.get_arguments()
        self.xml = VariantsXml()
        self.exc = ZmagsException(5)
        if self.d['database']:
            self.database = Database()
            self.database.connect()
            self.products, self.no_urls = self.database.select_products(self.d['catalog_id'],
                                                                        self.d['product_id'])
            self.database.disconnect()
        else:
            self.get_lists_from_excel()
        # fix for bug with links they provide
        self.products['urls'] = basic.cut_string_field(self.products['urls'], "&cat=")
        self.handle_not_provided()
        self.start_urls = self.products['urls']
        self.images_store = "/" + settings['IMAGES_STORE']
        lydias.add_properties(self.xml)
        self.total = len(self.products['urls'])

    def parse(self, response):
        self.counter += 1
        basic.print_status(self.counter, self.total)
        hxs = HtmlXPathSelector(response)
        item = LydiasItem()
        if 'redirect_urls' in response.request.meta:
            cur_url = response.request.meta['redirect_urls'][0]
        else:
            cur_url = response.url
        index = self.products['urls'].index(cur_url)
        id = self.products['product_ids'][index]
        try:
            available = hxs.select('//div[@id="searchfor"]/text()').extract()
            if not available:
                item['product_id'] = [id]
                item['name'], item['price'], item['old_price'], item['description'] = self.get_basic_info(hxs)
                item['rating'], item['custom_rating'] = self.get_rating(hxs)
                chart = self.absolute_path(self.get_size_image(hxs))
                item['sizes_chart_image_url'] = self.get_server_path(chart)
                color_urls, color_names, product_image, color_codes = self.get_image_swatches(hxs)
                color_urls = self.absolute_path(color_urls)
                item['color_image_url'] = self.make_colors_json(color_urls, color_names, color_codes)
                item['in_stock'] = ["IN_STOCK"]
                item['embroidery'] = self.get_embroidery(hxs)
                default_images = self.absolute_path(self.get_extra_images(hxs))
                item['default_image_url'] = self.get_server_path(default_images)
                self.xml.create_xml(item)
                product_image = self.absolute_path(product_image)
                self.create_subproducts(id, color_names, product_image, color_codes, hxs)
                item['image_urls'] = product_image + color_urls + chart + default_images
                self.products['status'][index] = "ran"
            else:
                self.exc.code_handler(102, response.url)
                item['product_id'] = [id]
                item['in_stock'] = ["NOT_AVAILABLE"]
                self.products['status'][index] = "not_avail"
                self.xml.create_xml(item)
        except:
            self.products['status'][index] = "error"
            self.exc.code_handler(100, response.url)
        return item

     # function for checking if product has embroidery or not
    def get_embroidery(self, hxs):
        page = hxs.select('//html').extract()[0]
        if "document.getElementById('logocolor').disabled = true;" in page:
            return ["True"]
        else:
            return ["False"]

    # function for creating json with all information for colors
    def make_colors_json(self, color_urls, color_names, color_codes):
        dict = {}
        jsons = []
        for i in range(0, len(color_urls)):
            dict['color_url'] = self.get_server_path_single(color_urls[i])
            dict['color_name'] = color_names[i]
            dict['color_short'] = color_codes[i]
            json = basic.cdata(simplejson.dumps(dict))
            jsons.append(json)
        return jsons

    # function for getting image server path
    def get_server_path_single(self, url):
#        return url
        return self.images_store + "/full/" + hashlib.sha1(url).hexdigest() + ".jpg"

    # function for getting image path for field of images
    def get_server_path(self, urls):
#        return urls
        new = []
        for url in urls:
            new.append(self.images_store + "/full/" + hashlib.sha1(url).hexdigest() + ".jpg")
        return new

    #function for getting basic information for product
    def get_basic_info(self, hxs):
        name = hxs.select('//div[@id="proddetail"]/h1/text()').extract()
        price = hxs.select('//div[@id="proddetail"]/div[@class="yourprice bigprice"]/text()').extract()
        description = basic.cdata(hxs.select('//div[@id="details"]').extract()[0])
        description = basic.clean_string(description)
        old_price = hxs.select('//span[@class="yourprice_product"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="PriceDisplay"]/text()').extract()
        if old_price:
            old_price = [re.sub('[^0-9.]', '', old_price[0])]
        price = [re.sub('[^0-9.]', '', price[0])]
        return name, price, old_price, [description]

    # function for getting rating, both number and sentence (e.g. Rating 5 out of 6 votes)
    def get_rating(self, hxs):
        temp = hxs.select('//div[@id="Customerssay"]/p[2]/text()').extract()
        if temp:
            rating = basic.get_middle_text(temp[0].replace(" ", ""), "Rating:", "out")
            return rating, temp
        else:
            return [], temp

    #function for getting reviews, returning rating and field of json reviews
    # or empty fields if there's no reviews
    def get_reviews(self, hxs):
        reviews = hxs.select('//div[@class="prodReview"]')
        if reviews:
            title = reviews[0].select('p[@class="review_title"]/text()').extract()
            text = reviews[0].select('p[@class="review_text"]/text()').extract()
            author = reviews[0].select('p[@class="review_author"]/text()').extract()
            location = reviews[0].select('p[@class="review_location"]/text()').extract()
            jsons = self.make_reviews_json(title, text, author, location)
            return jsons
        else:
            return []

    # function for making json for reviews
    # currently not in use. cause there are no reviews in DPW design
    def make_reviews_json(self, title, text, author, location):
        jsons = []
        print len(title)
        print len(text)
        print len(author)
        print len(location)
        os._exit(0)
        for i in range(0, len(title)):
            json = '{ "title" : " %s ", "text" : "%s", "author" : "%s", "location" :\
                    "%s" }' % (title[i], text[i], author[i], location[i])
            json = basic.cdata(json)
            jsons.append(json)
        return jsons

    #function for getting size chart image
    def get_size_image(self, hxs):
        temp = hxs.select('//div[@class="TabbedPanelsContent cells"]/img/@src').extract()
        return temp

    #function for getting image swatches, returning fields (image_urls, image name, product color image)
    def get_image_swatches(self, hxs):
        colors = hxs.select('//div[@class="lolite"]')
        color_images = []
        color_names = []
        products_image = []
        color_codes = []
        for color in colors:
            color_images.append(color.select('a/img/@src').extract()[0])
            color_names.append(color.select('a/img/@alt').extract()[0])
            #if zoom image needed, this is the place to get it
            products_image.append(color.select('a/@rev').extract()[0])
            color_codes.append(color.select('a/@onclick').extract()[0].split(",")[1].replace("'", ""))
        return color_images, color_names, products_image, color_codes

    #function for getting additional images, returns field of images or empty field if there is no
    def get_extra_images(self, hxs):
        additional_images = hxs.select('//div[@id="AddImg"]/script/text()').extract()
        if additional_images:
            temp = basic.get_middle_text(additional_images[0], '"', '"')
            thumb_images = temp[0].split(",")
            return thumb_images
        else:
            return []

    #function for getting product id from the page
    def get_product_id(self, hxs):
        temp = hxs.select('//div[@id="wrap"]/script/text()').extract()
        id = basic.get_middle_text(temp[0], 'productid","', '"')
        return id[0]

    # function for getting sizes from another url, retunrning field of jsons for sizes
    # one id from the page is 115NB, if needed here to hardcode for testing
    # currently not in use
    def get_sizes(self, id, hxs):
        showmode = hxs.select('//input[@name="showmode"]/@value').extract()[0]
        itemmode = hxs.select('//input[@name="itemmode"]/@value').extract()[0]
        salemode = hxs.select('//input[@name="salemode"]/@value').extract()[0]
        url = "http://www.lydiasuniforms.com/ajaxed/product-showoptions.asp?sku=%s&opt1=AV&opt2=-1&type2=l1type" % (id)
        url += "&type3=&showmode=%s&itemmode=%s&salemode=%s&rnum=429" % (showmode, itemmode, salemode)
        jsons = []
        print "reading page..."
        page = urllib2.urlopen(url).read()
        print "page read"
        page = page.replace("'", "")
        page = page.replace("[", ",")
        page = page.replace(",,", "")
        temp = page.split("]")
        for i in range(0, len(temp) - 2):
            tmp = temp[i].split(",")
            json = '{ "size_short" : " %s ", "size_full" : "%s", "some_number" :\
                    "%s", "some_id" : "%s" }' % (tmp[0], tmp[1], tmp[2], tmp[3])
            json = basic.cdata(json)
            jsons.append(json)
        return jsons

    # function that handles creating subproducts, can be implemented for the usual way product for every combination
    # of size and color if needed
    def create_subproducts(self, id, color_names, product_image, color_codes, hxs):
        item = LydiasItem()
        # if no colors for specific product do this part and call to creating size children with empty string instead
        # of actual color name
        if len(color_names) == 0:
            item['master_product_id'] = [id]
            item['product_id'] = [id + "_" + "0"]
            item['color'] = ["NO_COLOR"]
            item['custom_size'] = self.create_sizes_subproducts(id, id + "_" + "0", "", hxs)
            self.xml.create_xml(item)

        # for handling cases when there are color options for specific product, create child for every color, and call
        # for creating size children for every provided color
        else:
            for i in range(0, len(color_names)):
                print "name :" + color_names[i] + "  code:" + color_codes[i]
                item['master_product_id'] = [id]
                item['product_id'] = [id + "_" + str(i)]
                item['color'] = [color_names[i]]
                item['color_short'] = [color_codes[i]]
                item['normal_image_url'] = self.get_server_path([product_image[i]])
                item['in_stock'] = ["IN_STOCK"]
                item['custom_size'] = self.create_sizes_subproducts(id, id + "_" + str(i), color_codes[i], hxs)
                self.xml.create_xml(item)
                item.clear()
        return 0

    # function for creating child products for sizes
    # little messy with all the commented lines but those lines can be used if needed to go back to old way with
    # child products instead of json
    def create_sizes_subproducts(self, main_id, id, color_code, hxs):
        print color_code
        jsons = []
        # if block for cases when color is provided
        if color_code != "":
            showmode = hxs.select('//input[@name="showmode"]/@value').extract()[0]
            itemmode = hxs.select('//input[@name="itemmode"]/@value').extract()[0]
            salemode = hxs.select('//input[@name="salemode"]/@value').extract()[0]
            url = "http://www.lydiasuniforms.com/ajaxed/product-showoptions.asp?sku=%s&opt1=%s&opt2=-1&type2=l1type&" \
                "type3=&showmode=%s&itemmode=%s&salemode=%s&rnum=193" % (main_id, color_code, showmode, itemmode, salemode)
            page = urllib2.urlopen(url).read()
            page = page.replace("'", "")
            page = page.replace("[", ",")
            page = page.replace(",,", "")
            temp = page.split("]")
            for i in range(0, len(temp) - 2):
                tmp = temp[i].split(",")
                item = {}
#                item['master_product_id'] = [id]
                item['size_short'] = tmp[0]
                item['price_url'] = self.get_size_price(str(main_id), str(color_code), tmp[0])
                item['size'] = tmp[1]
#                item['product_id'] = [id + "_" + str(i)]
#                item['in_stock'] = ["IN_STOCK"]
#                xml.create_xml(item)
                jsons.append(basic.cdata(simplejson.dumps(item)))
            return jsons

        # when the color is not provided different block of code cause it's done differently on the page
        else:
            temp = hxs.select('//div[@class="not_size"]/text()').extract()
            for i in range(0, len(temp)):
                item = {}
#                item['master_product_id'] = [id]
#                item['product_id'] = [id + "_" + str(i)]
                item['size_short'] = temp[i]
                item['price_url'] = self.get_size_price(str(main_id), "", temp[i])
#                item['in_stock'] = ["IN_STOCK"]
#                xml.create_xml(item)
                jsons.append(basic.cdata(simplejson.dumps(item)))
            return jsons

#        return 0

    # function for getting price for combination of every size and color, can return url where the price is, or can
    # parse that url to get that actual price but will drastically increase scraping time
    def get_size_price(self, id, color, size):
        if color != "":
            url = "http://www.lydiasuniforms.com/ajaxed/product-showprice.asp?sku=%s %s %s&qty=1&itemmode=" \
                  "0&showmode=1&rnum=388" % (str(id), str(color), size)
        else:
            url = "http://www.lydiasuniforms.com/ajaxed/product-showprice.asp?sku=%s %s&qty=1&itemmode=" \
                  "0&showmode=1&rnum=259" % (id, size)
        url = url.replace(" ", "%20")
        return url

    # just adding part for getting absolute paths for relative paths from page
    def absolute_path(self, urls):
        new = []
        for i in urls:
            new.append("http://www.lydiasuniforms.com" + i)
        return new

    # function used for gettin embroidery information from clients page, was used only once to get it
    # cause embroidery is the same for all the products
    def get_emb(self, hxs):
        emb = hxs.select('//div[@id="emb"]').extract()
        lettering_colors = hxs.select('//select[@id="threadcolor"]/option/@value').extract()
        urls = []
        d = {}
        colors = []
        for i in range(1, len(lettering_colors)):
            d['type'] = "lettering colors"
            d['name'] = lettering_colors[i]
            url = "http://www.lydiasuniforms.com/images/lydias/threadcolor_"
            url += lettering_colors[i].lower().replace(' ', '_') + ".gif"
            d['url'] = self.get_server_path_single(url)

            urls.append(url)
            colors.append(basic.cdata(simplejson.dumps(d)))
        lettering = hxs.select('//select[@id="lettering"]/option/@value').extract()
        l = {}
        letterings = []
        for i in range(1, len(lettering)):
            l['type'] = "lettering"
            l['name'] = lettering[i]
            url = "http://www.lydiasuniforms.com/images/lydias/lettering_"
            url += lettering[i].lower().replace(' ', '_') + ".gif"
            l['url'] = self.get_server_path_single(url)
            letterings.append(basic.cdata(simplejson.dumps(l)))
            urls.append(url)
        logo = hxs.select('//select[@id="logoname"]/option/@value').extract()
        logos = {}
        log = []
        for i in range(1, len(logo)):
            logos['type'] = "logo"
            logos['name'] = logo[i]
            url = "http://www.lydiasuniforms.com/images/logos/"
            url += logo[i].lower() + ".jpg"
            logos['url'] = self.get_server_path_single(url)
            urls.append(url)
            log.append(basic.cdata(simplejson.dumps(logos)))
        item = LydiasItem()
        item['color'] = colors
        item['lettering'] = letterings
        item['log'] = log
        xml.create_xml(item)
        xml.write_xml("emb")

        return urls
        print  colors, letterings, log
        os._exit(0)

    def handle_not_provided(self):
        item = LydiasItem()
        for n in self.no_urls['product_ids']:
            item['product_id'] = [n]
            index = self.no_urls['product_ids'].index(n)
            item['name'] = [self.no_urls['names'][index]]
            item['in_stock'] = ['NOT_AVAILABLE']
            self.xml.create_xml(item)

    def spider_closed(self, spider):
        """Handles spider_closed signal from end of scraping.
        Handles usual end operations for scraper like writing xml, exporting
        to database and sending appropriate mail message."""
        msg = ""
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
        #if self.d['upload']:
            #exp = CommonExport()
            #try:
                #exp.xml_to_db(self.name, filename, "4b0d6b52-7b05-4e54-9d87-dfe77ac270c9")
                #msg += "\n\nExport to database successful"
            #except StandardError:
                #msg += "\n\nExport to database failed"
        #else:
            #msg += "\n\nUpload to database not selected"
        ## part for exporting to database here
        from modules.mail import Mail
        mail = Mail()
        try:
            mail.send_mail(msg, "Lydias: {0}".format(filename))
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
        else:
            self.products = xls.delete_duplicates_dict(self.products)
            self.products, self.no_urls = xls.separate_no_urls(self.products)
            self.products = xls._add_none_status(self.products)
            self.no_urls = xls._add_none_status(self.no_urls)
