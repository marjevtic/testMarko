from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
import modules.basic_func as basic
from modules.zmags_xml import CommonXml
from modules.excel import DictExcel
from modules.exception import ZmagsException
from modules.terminal import DatabaseTerminal
from modules.export_to_db import CommonExport
from project_modules.sportman import SportmanItem
from scrapy.conf import settings
from modules.database import Database
from datetime import datetime
import project_modules.sportman.sportman_func as sportman
import hashlib
import urllib2
import simplejson
import sys
import requests
import json
import urllib

import re
import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

class SportmanSpider(CrawlSpider):
    name = "sportman"
    allowed_domains = ["example.com"]
    start_urls = ["http://www.example.com"]
    counter = 0

    def __init__(self, *a, **kw):
        super(SportmanSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        terminal = DatabaseTerminal(sys.argv, self.name)
        self.d = terminal.get_arguments()
        self.xml = CommonXml()
        self.exc = ZmagsException(5, "Sportmann")

        if self.d['database']:
            self.database = Database()
            self.database.connect()
            self.products, self.no_urls = self.database.select_products(self.d['catalog_id'],
                self.d['product_id'])
            self.database.disconnect()
        else:
            self.get_lists_from_excel()
        self.add_properties(self.xml)
        self.start_urls = self.products['urls']
        self.images_store = "/" + settings['IMAGES_STORE']
        self.total = len(self.start_urls)


    def parse(self, response):
        self.counter += 1
        basic.print_status(self.counter, self.total)
        hxs = HtmlXPathSelector(response)
        item = SportmanItem()
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
                item["name"], item["short_desc"], item["description"], item["old_price"], item["custom_price"], item["product_id"], item["sku"] = self.get_basic_info(hxs)
                item['in_stock'] = ['IN_STOCK']
                viewstate, eventval, prevpage, hidden, view_page, even_page, pre_page, hidd_page = self.get_vars(response, hxs)

                viewstate1 = viewstate[:2000]
                viewstate2 = viewstate[2000:4000]
                viewstate3 = viewstate[4000:6000]
                viewstate4 = viewstate[6000:8000]
                viewstate5 = viewstate[8000:10000]
                viewstate6 = viewstate[10000:]

                item["viewstate1"] = [basic.cdata(viewstate1)]
                item["viewstate2"] = [basic.cdata(viewstate2)]
                item["viewstate3"] = [basic.cdata(viewstate3)]
                item["viewstate4"] = [basic.cdata(viewstate4)]
                item["viewstate5"] = [basic.cdata(viewstate5)]
                item["viewstate6"] = [basic.cdata(viewstate6)]
                item["eventval"] = [basic.cdata(eventval)]
                item["size_options"] = self.get_variants(hxs, response)

                images_url = self.get_images(hxs)

                item["normal_image_url"] = self.get_server_path(images_url)

                self.xml.create_xml(item)
                item.clear()
                item['image_urls'] = self.get_images(hxs)
                self.products["status"][index] = "ran"
        except:
            self.exc.code_handler(100, response.url)
            self.products["status"][index] = "error"
        else:
            return item


    def get_basic_info(self, hxs):
        name = hxs.select('//div[@id="fragment-1"]/h2/text()').extract()

        short_desc = hxs.select('//div[@class="description2"]/text()').extract()

        description = hxs.select('//div[@id="fragment-1"]/div[@class="description"]').extract()
        description = sportman.delete_tags(re, description[0])
        description = [basic.cdata(description)]

        old_price = hxs.select('//span[@class="oldprice"]/text()').extract()
        if (old_price != []):
            old_price = " ".join(old_price)
            old_price = old_price.split(':')
            old_price = old_price[1].replace('Kr','')
            old_price = [old_price.replace(" ","")]
        else:
            old_price = old_price

        price = hxs.select('//span[@class="nowprice"]/text()').extract()
        if (price != []):
            price = " ".join(price)
            price = price.split(':')
            price = price[1].replace('Kr','')
            price = [price.replace(" ","")]
        else:
            price = hxs.select('//span[@class="normalprice"]/text()').extract()
            price = " ".join(price)
            price = price.split(':')
            price = price[1].replace('Kr','')
            price = [price.replace(" ","")]

        id = hxs.select('//div[@class="articlenumber"]').extract()
        id = " ".join(id)
        id = id.replace(u"\xa0","")
        id = basic.get_middle_text(id, 'Art.nr.', '</div>')
        sku = id
        id = [id[0]]

        return name, short_desc, description, old_price, price, id, sku


    def get_vars(self, response, hxs):
        headers1 = {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:13.0) Gecko/20100101 Firefox/13.0.1',
                    'Host': 'www.sportmann.no',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                    'Connection': 'keep-alive',
                    'Referer': '/product.aspx?productid=613232',
                    'Cookie': 'ASP.NET_SessionId=lurvsvrn3jxsfd45cedmsv45; Besok=922884e3-e9cb-4b69-b8c8-215f3cc988a9; __utma=184084580.1353376623.1312483243.1312483243.1312483243.1; __utmb=184084580.9.10.1312483243; __utmc=184084580; __utmz=184084580.1312483243.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)'
        }

        page = hxs.select('//html').extract()
        page = " ".join(page)

        viewst = basic.get_middle_text(page, 'id="__VIEWSTATE" value="', '"')
        eventval = basic.get_middle_text(page, 'id="__EVENTVALIDATION" value="', '"')
        prevpage = [""]
        hidden_field = [""]

        r=requests.get(response.url  , headers = headers1)

        page_one = r.content

        viewst_page = basic.get_middle_text(page_one, 'id="__VIEWSTATE" value="' , '"')
        eventval_page = basic.get_middle_text(page_one, 'id="__EVENTVALIDATION" value="' , '"')
        prevpage_page = basic.get_middle_text(page_one, 'id="__PREVIOUSPAGE" value="', '"')
        hidden_temp = page_one.split('id="__VIEWSTATE"')
        hidden_temp = hidden_temp[1].split('id="__PREVIOUSPAGE"')
        hidden_temp = hidden_temp[0].split('<script sr')

        val_x = len(hidden_temp) - 1

        hidden_temp = basic.get_middle_text(hidden_temp[val_x], 'c="', '"')
        hidden_temp_val = hidden_temp[0]
        hidden_temp_val = hidden_temp_val.replace('amp;','')
        hidden_url = "http://www.sportmann.no" + hidden_temp_val

        request_hidden = urllib2.Request(hidden_url)
        response_hidden = urllib2.urlopen(request_hidden)
        hidden_field_page = basic.get_middle_text(response_hidden.read(),"ctl00_ScriptManager1_HiddenField').value += '", "';" )

        return viewst[0], eventval[0], prevpage[0], hidden_field[0], viewst_page[0], eventval_page[0], prevpage_page[0], hidden_field_page[0]


    def get_variants(self, hxs, response):
        page = hxs.select('//html').extract()
        page = " ".join(page)
        dict_one = {}
        test_one = []

        temp = page.split('<div class="color">')
        temp = temp[1].split('</div>')
        temp = temp[0].split('<select name')

        viewstate, eventvalidation, previouspage, hiddenfield, view_page, even_page, pre_page, hidd_page = self.get_vars(response, hxs)

        if (len(temp) == 1):
            color = hxs.select('//div[@class="color"]/text()').extract()
            value = hxs.select('//input[@id="ctl00_ContentPlaceHolder1_Variant1Hidden"]/@value').extract()
            color[0] = color[0].replace("  ", "")
            color = basic.clean_string(color[0])
            value = value[0]

        #            color = basic.clean_string(color[0])
        #            color = color.replace("  ","")
        #
        #            dict['color'] = color
        #            dict['color_value'] = value[0]

        else:
            test_color = basic.get_middle_text(temp[1], 'farge</option>', '</select>')
            color = basic.get_middle_text(test_color[0], '">', '</option>')
            value = basic.get_middle_text(test_color[0], 'value="', '">')

            for i in range(0, len(color)):
                color[i] = color[i].replace("  ", "")
            #
            #                dict['color'] = color
            #                dict['color_value'] = value

        size_temp = page.split('<div class="size">')
        size_temp = size_temp[1].split('</div>')
        size_temp = size_temp[0].split('<select name')

        if (len(size_temp) == 1):
            size = hxs.select('//div[@class="size"]/text()').extract()
            size = basic.clean_string(size[0])
            size = [size.replace("   ", "")]

            size_val = hxs.select('//input[@id="ctl00_ContentPlaceHolder1_Variant2Hidden"]/@value').extract()

            if size[0] == "":
                for i in range(len(value)):
                    resp_page = self.get_data(response, hidd_page, view_page, pre_page, even_page, value[i])

                    a_page = resp_page.split('<div class="siz')
                    a_page = a_page[1].split('</select>')

                    if len(a_page) == 1:

                        size = basic.get_middle_text(a_page[0], 'e">', '<input type="hidden"')
                        size_val = basic.get_middle_text(a_page[0], 'value="', '"')
                        size_val = size_val[0]
                        size_val =  [size_val]

                    else:
                        a_page = basic.get_middle_text(a_page[0],'se</option>', '</select>' )
                        size = basic.get_middle_text(a_page[0], '">', '</option>')
                        size_val = basic.get_middle_text(a_page[0], 'value="', '">')

                    dict_one["color"] = color[i]
                    dict_one["color_value"] = value[i]
                    dict_one["size_value"] = size_val

                    for x in range(0, len(size)):
                        size[x] = basic.clean_string(size[x])
                        size[x]= size[x].replace("   ", "")

                        dict_one["size"] = size

                    test_one.append(basic.cdata(json.dumps(dict_one)))

            else:
                dict_one["color"] = color

                dict_one["color_value"] = value
                dict_one['size'] = size
                dict_one['size_value'] = size_val
                test_one.append(basic.cdata(simplejson.dumps(dict_one)))

        else:
            test_size = basic.get_middle_text(size_temp[1], 'se</option>', '</select>')
            size = basic.get_middle_text(test_size[0], '">', '</option>')
            size_val = basic.get_middle_text(test_size[0], 'value="', '">')

            for x in range(0, len(size)):
                size[x] = basic.clean_string(size[x])
                size[x]= size[x].replace("   ", "")

            dict_one["color"] = color
            dict_one["color_value"] = value
            dict_one['size'] = size
            dict_one['size_value'] = size_val

            test_one.append(basic.cdata(json.dumps(dict_one)))

        return test_one


    def get_server_path(self, url):
        images_array = []
        for i in range(0, len(url)):
            url[i] = basic.clean_string(url[i])

            images_array.append(self.images_store + "/full/" + hashlib.sha1(url[i]).hexdigest() + ".jpg")

        return images_array


    def get_images(self, hxs):
        page = hxs.select('//html').extract()
        page = " ".join(page)

        images = []

        temp = page.split('class="gallery_demo_unstyled"')
        temp = temp[1].split('<div class="right_container">')
        temp = basic.get_middle_text(temp[0], 'src="', '"')

        for i in range(0, len(temp)):
            image_url = "http://www.sportmann.no" + temp[i]
            images.append(image_url)

        return images


    def get_data(self, response,hidden, viewstate, previouspage, eventvalidation, colorvalue):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:5.0) Gecko/20100101 Firefox/5.0',
                   'Host': 'www.sportmann.no',
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                   'Accept-Language': 'en-us,en;q=0.5',
                   'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                   'Connection': 'keep-alive',
                   'Referer': 'http://www.sportmann.no/product.aspx?productid=613232',
                   'Cookie': '' }

        eventvalidation = urllib.urlencode({"__EVENTVALIDATION" : eventvalidation})
        viewstate = urllib.urlencode({"__VIEWSTATE" : viewstate})
        previouspage = urllib.urlencode({"__PREVIOUSPAGE" : previouspage})
        hidden = urllib.urlencode({"ctl00_ScriptManager1_HiddenField" : hidden})

        data = "ctl00%24ScriptManager1=ctl00%24ContentPlaceHolder1%24dropdownPanel%7Cctl00%24ContentPlaceHolder1%24ddlVariant&" + hidden + "%3B%3BAjaxControlToolkit%2C%20Version%3D3.0.20820.16598%2C%20Culture%3Dneutral%2C%20PublicKeyToken%3D28f01b0e84b6d53e%3Aen-US%3A707835dd-fa4b-41d1-89e7-6df5d518ffb5%3Ae2e86ef9%3A1df13a87%3A8ccd9c1b%3A9ea3f0e2%3A9e8e87e9%3A4c9865be%3Aba594826%3A757f92c2%3Ac7c04611%3Acd120801%3Ac4c00916%3A3858419b%3A96741c43%3A38ec41c0%3B%3BAjaxControlToolkit%2C%20Version%3D3.0.20820.16598%2C%20Culture%3Dneutral%2C%20PublicKeyToken%3D28f01b0e84b6d53e%3Aen-US%3A707835dd-fa4b-41d1-89e7-6df5d518ffb5%3Ae2e86ef9%3A1df13a87%3A8ccd9c1b%3A9ea3f0e2%3A9e8e87e9%3A4c9865be%3Aba594826%3A757f92c2%3Ac7c04611%3Acd120801%3Ac4c00916%3A3858419b%3A96741c43%3A38ec41c0%3B%3BAjaxControlToolkit%2C%20Version%3D3.0.20820.16598%2C%20Culture%3Dneutral%2C%20PublicKeyToken%3D28f01b0e84b6d53e%3Aen-US%3A707835dd-fa4b-41d1-89e7-6df5d518ffb5%3Ae2e86ef9%3A1df13a87%3A8ccd9c1b%3A9ea3f0e2%3A9e8e87e9%3A4c9865be%3Aba594826%3A757f92c2%3Ac7c04611%3Acd120801%3Ac4c00916%3A3858419b%3A96741c43%3A38ec41c0&__EVENTTARGET=ctl00%24ContentPlaceHolder1%24ddlVariant&__EVENTARGUMENT=&__LASTFOCUS=&" + viewstate + "&" + previouspage + "&" + eventvalidation + "&ctl00%24ProductSearch%24txtProdSearch=&ctl00%24ProductSearch%24TextBoxWatermarkProdSearch_ClientState=&ctl00%24ContentPlaceHolder1%24ddlVariant=" + colorvalue + "&ctl00%24ContentPlaceHolder1%24Variant1Hidden=&ctl00%24ContentPlaceHolder1%24Variant2Hidden=&ctl00%24ContentPlaceHolder1%24tbAmount=1&ctl00%24ContentPlaceHolder1%24modTellFriend%24tellFriend%24txtFriendsName=&ctl00%24ContentPlaceHolder1%24modTellFriend%24tellFriend%24vceFriendsName_ClientState=&ctl00%24ContentPlaceHolder1%24modTellFriend%24tellFriend%24txtFriendsEmail=&ctl00%24ContentPlaceHolder1%24modTellFriend%24tellFriend%24vceFriendsEmail_ClientState=&ctl00%24ContentPlaceHolder1%24modTellFriend%24tellFriend%24txtYourName=&ctl00%24ContentPlaceHolder1%24modTellFriend%24tellFriend%24vceYourName_ClientState=&ctl00%24ContentPlaceHolder1%24modTellFriend%24tellFriend%24txtYourEmail=&ctl00%24ContentPlaceHolder1%24modTellFriend%24tellFriend%24vceYourEmail_ClientState=&ctl00%24ContentPlaceHolder1%24modTellFriend%24tellFriend%24txtComment=&ctl00%24ContentPlaceHolder1%24modTellFriend%24tellFriend%24vceComment_ClientState=&__ASYNCPOST=true&"

        #r = requests.get(response.url, h)
        req=urllib2.Request(response.url, data, headers)

        resp_page=urllib2.urlopen(req).read()

        return resp_page


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
                exp.xml_to_db(self.name, filename, "1ccd39a5-af4e-47cc-aebe-e0dede5b14d8")
                msg += "\n\nExport to database successful"
            except StandardError:
                msg += "\n\nExport to database failed"
        else:
            msg += "\n\nUpload to database not selected"
        from modules.mail import Mail
        mail = Mail()
        try:
            mail.send_mail(msg, "Sportmann: {0}".format(filename))
            if self.d['email']:
                mail.send_mail(msg, "Sportmann: {0}".format(filename), self.d['email'])
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

    def add_properties(self, xml):
        xml.add_property("short_desc","Short Description", "text")
        xml.add_property("old_price","Old Price", "text")
        xml.add_property("custom_price","New Price", "text")
        xml.add_property("color_value","Color Value", "text")
        xml.add_property("in_stock","In Stock", "text")
        xml.add_property("size_val","Size Value", "text_list")
        xml.add_property("sku","Sku", "text")
        xml.add_property("size_options","Size_options", "text_list")
        xml.add_property("viewstate1","Viewstate1", "text_list")
        xml.add_property("viewstate2","Viewstate2", "text_list")
        xml.add_property("viewstate3","Viewstate3", "text_list")
        xml.add_property("viewstate4","Viewstate4", "text_list")
        xml.add_property("viewstate5","Viewstate5", "text_list")
        xml.add_property("viewstate6","Viewstate6", "text_list")
        xml.add_property("eventval","Eventval", "text_list")
        xml.add_property("hidden","Hidden Field", "text_list")
        xml.add_property("prevpage","Previous Page", "text_list")
        xml.add_property("recommended_product","Recommended Product", "text_list")
