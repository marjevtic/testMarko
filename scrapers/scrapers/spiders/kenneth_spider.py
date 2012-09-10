from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
import modules.basic_func as basic
from modules.zmags_xml import VariantsXml
from modules.excel import DictExcel
from modules.exception import ZmagsException
from modules.terminal import DatabaseTerminal
from modules.export_to_db import CommonExport
from project_modules.kenneth import KennethItem
from modules.database import Database
from scrapy.conf import settings
import hashlib
import urllib2
import simplejson
import sys

import re
import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

class KennethSpider(CrawlSpider):
    name = "kenneth"
    allowed_domains = ["example.com"]
    start_urls = ["http://www.example.com"]
    counter = 0

    def __init__(self, *a, **kw):
        super(KennethSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        terminal = DatabaseTerminal(sys.argv, self.name)
        self.images_store = "/" + settings['IMAGES_STORE'] + "/"
        self.d = terminal.get_arguments()
        self.xml = VariantsXml()
        self.exc = ZmagsException(5)
        print self.d
        if self.d['database']:
            self.database = Database()
            self.database.connect()
            self.products, self.no_urls = self.database.select_products(self.d['catalog_id'],
                                                                        self.d['product_id'])
            self.database.disconnect()
        else:
            self.get_lists_from_excel()
        self.add_properties(self.xml)
        self.no_url_products(self.no_urls)
        self.start_urls = self.products['urls'] 
        self.total = len(self.start_urls)

    def parse(self, response):
        self.counter += 1
        basic.print_status(self.counter, self.total)
        hxs = HtmlXPathSelector(response)
        item = KennethItem()
        #main try for script, run general except if error happens in code (send
        # url on mail where it happened)
        try:
            cur_url = response.url
                # search for noResultContent div on the page, if it exists keep
                # track, that product doesn't exist on
                # their page, otherwise continue scraping page
            available = hxs.select('//div[@id="noResultsContent"]').extract()

            if not available:
                index = self.products['urls'].index(cur_url)
                cur_id = self.get_product_id(cur_url)
                id = self.products['product_ids'][index]
                page = hxs.select('//div[@id="mainContent"]').extract()
                page = " ".join(page)
                item['name'], item['description'] = self.get_basic_info(hxs)
                price, new_p, old_p = self.get_prices(hxs)
                if new_p:
                    item['new_price'] = new_p
                    item['old_price'] = old_p
                else:
                    item['price'] = price
                desc = basic.clean_string(item['description'][0])
                item['description'] = [desc]
                urls = self.get_color_image(hxs)
                new = self.get_image_server_path(urls, id)
                item['color_image_urls'] = new
                self.export(item['color_image_urls'], [id], "swatchImage")
                jsons, images = self.we_also_recommend(cur_id, id)
                item['product_page'] = [cur_url]
                item['product_id'] = [id]
                item['add_to_cart_id'] = [cur_id]
                item['recommended_product'] = jsons
                item['in_stock'] = ["IN_STOCK"]
                self.products['status'][index] = "ran"
                images_or_404 = self.get_colors(hxs, page, id)
                if images_or_404 == 404:
                    item['in_stock'] = ["NOT_AVAILABLE"]
                self.xml.create_xml(item)
                item['image_urls'] = []
                if images_or_404 != 404:
                    item['image_urls'] += images_or_404
                item['image_urls'] += urls
                item['image_urls'] += images
                #self.export(item['image_urls'])
                #item['image_urls'] = [] #uncomment for donwloading images 

            else:
                # part for handling products that are not available
                cur_id = self.get_product_id(cur_url)
                cur_url = "http://www.kennethcole.com/product/index.jsp?"
                cur_url += "productId=" + str(cur_id)
                index = self.products['urls'].index(cur_url)
                self.products['status'][index] = "no_avail"
                item['product_id'] = [self.products['product_ids'][index]]
                if self.products['product_ids'][index]:
                    item['name'] = [self.products['names'][index]]
                else:
                    item['name'] = ["not available"]
                item['in_stock'] = ["NOT_AVAILABLE"]
                self.xml.create_xml(item)
                self.exc.code_handler(102, cur_url)
        except:
            # part for catching errors and keeping track of numbers of
            # it and urls where it happened
            print "Error occured scraping this product"
            index = self.products['urls'].index(cur_url)
            self.products['status'][index] = "error"
            self.exc.code_handler(100, cur_url)
        return item

    def no_url_products(self, no_url):
        item = KennethItem()
        for n in no_url['product_ids']:
            item['product_id'] = [n]
            index = no_url['product_ids'].index(n)
            item['name'] = [no_url['names'][index]]
            item['in_stock'] = ['NOT_AVAILABLE']
            self.xml.create_xml(item)

    #function for getting basic product info from the page
    def get_basic_info(self, hxs):
        name = hxs.select('//div[@id="productInfoTop"]/h1/text()').extract()
        description = basic.cdata(hxs.select('//div[@id="productDescription"]').extract()[0])
        return name, [description]

    # function for getting prices from the page, nly one or new and old one if
    # that's the case
    def get_prices(self, hxs):
        price = hxs.select('//div[@id="productInfoTop"]/h2/text()').extract()[0]
        new_p = hxs.select('//h2[@class="sale-now"]/text()').extract()
        old_p = hxs.select('//span[@class="productGrey"]/text()').extract()
        price = re.sub('[^0-9.,]', '', price)
        return [price], new_p, old_p

    def get_color_image(self, hxs):
        return hxs.select('//div[@id="productInfoR2W"]/img/@src').extract()

    # function for gettng colors from javascript on the page, and writing them
    # in xml, from here is called function
    # for creating further sizes subproducts
    def get_colors(self, hxs, page, main_id):
        item = KennethItem()
        try:
            tmp = page.split('displays[0]')[1]
        except IndexError:
            print "This product is not available"
            return 404
        script = tmp.split('</script>')[0]
        displays = script.split("};")
        global counter
        ids = []
        images = []
        color_ids = []
        sizes_script = self.get_sizes_part_page(page)
        color_internal_code = {}

        for x in range(0, len(displays) - 1):
            id = basic.get_middle_text(displays[x], 'colorId: "', '"')
            ids.append(id[0])
            reg = displays[x].count("Reg")
            images_in = []
            for i in range(1, reg + 1):
                image = basic.get_middle_text(displays[x], "vw" + str(i) + 'Reg: "', '"')
                if len(image) == 0:
                    image = basic.get_middle_text(displays[x], "vw" + str(i) + 'Reg:"', '"')
                if (len(image) > 0):
                    if (image[0] != "null"):
                        images_in.append(image[0])

            if not images_in:
                images_in = hxs.select('//input[@name="productImage"]/@value').extract()
            color_ids.append(str(main_id) + "_" + str(x))
            item['product_id'] = [str(main_id) + "_" + str(x)]
            item['color_option_id'] = id
            item['master_product_id'] = [main_id]
            item['normal_image_url'] = self.get_image_server_path(images_in, main_id)
            item['thumb_image_url'] = self.get_image_server_path_thumb(images_in, main_id)
            item['in_stock'] = ["NOT_IN_STOCK"]
            item['color'] = self.get_color_name(sizes_script, id[0])
            color_internal_code[id[0]] = str(x)
            self.xml.create_xml(item)
            images += images_in
            self.export(item['normal_image_url'], item['product_id'], "productImage")
        self.get_sizes(sizes_script, ids, main_id, color_internal_code)
        return images

    # function for getting sizes for products from javascript, and storing 
    # information in dicts of format {id : information}
    def get_sizes(self, page, ids, main_id, color_internal_code):
        options = page.split("};")
        skus = {}
        colors_name = {}
        inStocks = {}
        sizes = {}
        prices = {}
        for x in range(0, len(options) - 1):
            id = basic.get_middle_text(options[x], 'cId: "', '"')
            for i in range(0, len(ids)):
                if (id[0] == ids[i]):
                    sku = basic.get_middle_text(options[x], 'sku: ', ',s')
                    sku = re.sub("[^0-9]", "", sku[0])
                    skus = self.add_to_dict(skus, ids[i], sku)
                    size = basic.get_middle_text(options[x], 'sDesc: "', '"')
                    sizes = self.add_to_dict(sizes, ids[i], size[0])
                    price = basic.get_middle_text(options[x], 'price: "', '"')
                    price = self.clean_price(price[0])
                    prices = self.add_to_dict(prices, ids[i], price[0])
                    available = basic.get_middle_text(options[x], 'avail: "', '"')
                    inStocks = self.add_to_dict(inStocks, ids[i], available[0])
        self.create_subproducts_xml(main_id, color_internal_code, colors_name, sizes, skus, inStocks, prices)
        return main_id, colors_name, sizes, skus, inStocks, prices

    # function for creating subproducts for every size
    def create_subproducts_xml(self, main_id, color_internal_code, colors_name, sizes, skus, inStocks, prices):
        number = 0
        global counter
        for k, v in sizes.iteritems():
            item = KennethItem()
            for i in range(0, len(v)):
                item['size'] = [v[i]]
                item['size_option_id'] = [skus[k][i]]
                m_id = main_id + "_" + color_internal_code[k]
                item['master_product_id'] = [m_id]
                id = m_id + "_" + str(i)
                item['product_id'] = [id]
                if inStocks[k][i] == "NOT_AVAILABLE":
                    item['in_stock'] = ["NOT_IN_STOCK"]
                elif inStocks[k][i] == "ADVANCED_SALE_LIMITED":
                    item['in_stock'] = ["IN_STOCK"]
                else:
                    item['in_stock'] = [inStocks[k][i]]
                item['price'] = [prices[k][i]]
                #item['color'] = colors_name[k]
                self.xml.create_xml(item)
            number += 1

    def add_to_dict(self, dict, index, value):
        try:
            dict[index].append(value)
        except:
            dict[index] = [value]
        return dict

    # function for getting we also recommend information about products from
    # their page, returns json list with information and images
    # list with images urls
    def we_also_recommend(self, id, main_id):
        url = "http://www.res-x.com/ws/r2/Resonance.aspx?appid=kennethcole01&t"
        url += "k=154212870918247&ss=525178103419747&sg=1&pg=897706724574618&b"
        url += "x=true&vr=2.67&sc=product_rr&ev=product&ei=" + id + "&cu=&ct=k"
        url += "ennethcolec01&no=3&cb=r1eh&clk=&cv1=" + id + "&cv23=63&ur=http%"
        url += "3A//www.kennethcole.com/product/index.jsp%3FproductId%3D3" + id
        url += "&plk=&rf="
        import urllib2
        page = urllib2.urlopen(url).read()
        temp = page.split("certonaRecBoxes")
        images = []
        ids = []
        names = []
        prices = []
        urls = []
        # parsing data got from the upper url about we also recommend products
        for i in range(1, len(temp)):
            id = [basic.get_middle_text(temp[i], "d=", '\\"')[0]]
            image = basic.get_middle_text(temp[i], 'src=\\"', '\\"')[0]
            name = basic.get_middle_text(temp[i], 'alt=\\"', '\\"')
            price = basic.get_middle_text(temp[i], '<br>', '</a>')
            url = "http://www.kennethcole.com/product/index.jsp?productId="
            url += id[0]
            urls.append(url)
            ids.append(id)
            names.append(name)
            prices.append(price)
            images.append(image)
        jsons = self.make_json(ids, names, prices, self.get_image_server_path(images, main_id), urls)
        return jsons, images

    # function for getting product id from the url
    def get_product_id(self, url):
        return url.split("=")[1]

    #function for making json
    def make_json(self, ids, names, prices, images, urls):
        jsons = []
        for i in range(0, len(ids)):
            json = "{" + ' "id" : "' + str(ids[i][0]) + '", '
            json += '"name" : "' + str(names[i][0]) + '", '
            # insert function for storing the right image path
            json += '"image_url" : "' + str(images[i]) + '", '
            json += '"product_url" : "' + urls[i] + '", '
            json += '"price" : "' + str(prices[i][0]) + '" } '
            json = basic.cdata(json)
            jsons.append(json)
        return jsons

    #function for getting javascript where sizes are handled
    def get_sizes_part_page(self, page):
        tmp = page.split("availDates = new Array();")[1]
        script = tmp.split("</script>")[0]
        return script

    # function for getting name of the color by id
    def get_color_name(self, script, id):
        temp = script.split(id)
        temp = temp[0].split('cDesc: "')
        temp = temp[len(temp) - 1]
        name = temp.split('"')[0]
        return [name]
        return {id: name}

    #function for exporting images to database via rest
    def export(self, images, id, tags):
        #set override to 0 for uploading images or else to skip uploading
        override = 1
        if override == 0:
            import MultipartPostHandler
            import urllib2
            import os
            url = 'http://api.admin.zmags.com/productImage/import?key=5ef90922-283b-4412-a1c8-3e70bc28b9d3'

            for i in range(0, len(images)):
                image_name = self.get_image_name(images[i])
                path = "images/kenneth_images/small/" + str(image_name)
                params = {'file': file(path, 'rb'), 'product_id': id[0],
                          'index': str(i + 1), 'tags': tags}
                          #token not working
                opener = urllib2.build_opener(MultipartPostHandler.MultipartPostHandler)
                code = opener.open(url, params).getcode()

                if (code != 202):
                    print ("Achtung")
                global images_number
                images_number += 1
                print images_number

                print "Image uploaded to product " + id[0]
        else:
            #print "Image upload overriden.."
            pass

    #function for getting image name from url
    def get_image_server_path(self, urls, id):
#        print urls
        new = []
        for url in urls:
            temp = url.split("/")
            new.append(self.images_store + id + "/full/" + temp[len(temp) - 1])
        return new

    # function for getting image paths on our server
    def get_image_server_path_thumb(self, urls, id):
        new = []
        for url in urls:
            temp = url.split("/")
            new.append(self.images_store + id + "/small/" + temp[len(temp) - 1])
        return new

    def clean_price(self, price):
        return [re.sub('[^0-9.,]', '', price)]

    def spider_closed(self, spider):
        """Handles spider_closed signal from end of scraping.
        Handles usual end operations for scraper like writing xml, exporting
        to database and sending appropriate mail message."""
        msg = ""
        if self.counter < self.total:
            msg += "\nScraper didn't go through all products, please report"
        msg += "\n\nScraped {0} product out of {1}\n\n".format(self.counter, self.total)
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
            #try:
            exp.xml_to_db(self.name, filename, "29eac9ea-8c57-4d22-baf4-3f1471dc3ab6")
            msg += "\n\nExport to database successful"
            #except StandardError:
                #msg += "\n\nExport to database failed"
        else:
            msg += "\n\nUpload to database not selected"
        from modules.mail import Mail
        mail = Mail()
        try:
            mail.send_mail(msg, "KennethCole: {0}".format(filename))
            if self.d['email']:
                mail.send_mail(msg, "KennethCole: {0}".format(filename), self.d['email'])
        except:
            msg += "\nSending mail failed."
        if self.d['database']:
            path = 'logs/{0}'.format(self.name)
            if not os.path.exists(path):
                os.makedirs(path)
            with open("{0}/{1}".format(path, filename), 'w') as f:
                f.write(msg)

    def get_lists_from_excel(self):
        xls = DictExcel(basic.get_excel_path(self.name, self.d['file']))
        self.products = dict()
        try:
            self.products['urls'] = xls.read_excel_collumn_for_urls(2, 2)
            self.products['product_ids'] = xls.read_excel_collumn_for_ids(0, 2)
            self.products['names'] = xls.read_excel_collumn(1, 2)
        except IOError as e:
            msg = "I/O error {0}: {1}".format(e.errno, e.strerror)
            msg += "\nError occurred for given file: {0}".format(self.d['file'])
            self.exc.code_handler(103, msg=msg)
        except StandardError:
            msg = "Error reading excel file"
            msg += "\nError occurred for given file: {0}".format(self.d['file'])
            self.exc.code_handler(103, msg=msg)
        self.products = xls.delete_duplicates_dict(self.products)
        self.products, self.no_urls = xls.separate_no_urls(self.products)
        self.products = xls._add_none_status(self.products)
        self.no_urls = xls._add_none_status(self.no_urls)

    def add_properties(self, xml):
        xml.add_property("add_to_cart_id", "Add To Cart Id", "text")
        xml.add_property("product_page", "Product page", "text")
        xml.add_property("color_image_urls", "Color Image URLs", "text_list")
        xml.add_property("color_option_id", "Color Option ID", "text")
        xml.add_property("recommended_product", "Recommended Product", "text_list")
        xml.add_property("size_option_id", "Size Option ID", "text")
        xml.add_property("in_stock", "In Stock", "text")
        xml.add_property("old_price", "Old Price", "text")
        xml.add_property("new_price", "New Price", "text")

