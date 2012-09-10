from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
import modules.basic_func as basic
from modules.zmags_xml import CommonXml
from modules.excel import DictExcel
from modules.exception import ZmagsException
from modules.terminal import DatabaseTerminal
from modules.export_to_db import CommonExport
from project_modules.chome import ChomeItem
from modules.download import Downloader
from xml.etree.cElementTree import iterparse
from scrapy.conf import settings
from modules.database import Database
from datetime import datetime
import HTMLParser
import hashlib
import urllib2
import simplejson
import sys

import re
import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals


class ChomeSpider(CrawlSpider):
    name = "chome"
    allowed_domains = ["zmags.com"]
    start_urls = ["http://www.zmags.com/"]
    counter = 0

    def __init__(self, *a, **kw):
        super(ChomeSpider, self).__init__(*a, **kw)
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
        self.images_store = "/" + settings['IMAGES_STORE']
        self.total = len(self.no_urls['product_ids'])

    def parse(self, response):
        self.counter += 1
        hxs = HtmlXPathSelector(response)
        item = ChomeItem()
        print "IDs in excel feed: {0}".format(self.total)
        item['image_urls'] = self.parse_whole_xml()
        return item

    def parse_whole_xml(self):
        xml_dir = "xml/{0}".format(self.name)
        file_url = "https://svc.celebratinghome.com/ZMags.svc/ProductInfo1"
        downloader = Downloader()
        if self.d['download']:
            downloader.get_file(xml_dir, file_url, "client_feed")
        else:
            if not os.path.exists('xml/{0}/client_feed.xml'.format(self.name)):
                basic.warning("Feed file doesn't exist please de-select no download option")
                os._exit(2)
        self.number = 0
        xml_item = ChomeItem()
        urls_all = []
        for event, elem in iterparse('xml/{0}/client_feed.xml'.format(self.name)):
            if elem.tag == "{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}properties":
                for r in elem:
                    p = "{http://schemas.microsoft.com/ado/2007/08/dataservices}"
                    if r.tag == p + "Id" and r.text in self.no_urls['product_ids']:
                        index = self.no_urls['product_ids'].index(r.text)
                        self.no_urls['status'][index] = 'ran'
                        self.number += 1
                        urls = []
                        flag = 0
                        for x in elem:
                            if x.tag == p + "Id":
                                xml_item['product_id'] = [x.text]
                            elif x.tag == p + "EngLongDesc" and x.text is not None:
                                xml_item['description_english'] = [self.escape(basic.cdata(x.text))]
                            elif x.tag == p + "RetailPrice":
                                xml_item['custom_price'] = [x.text[:-2]]
                            elif x.tag == p + "SpnLongDesc" and x.text is not None:
                                xml_item['description_spanish'] = [self.escape(basic.cdata(x.text))]
                            elif x.tag == p + "PartNumber":
                                xml_item['add_to_cart_id'] = [x.text]
                            elif x.tag == p + "MaxQty":
                                xml_item['max_qty'] = [x.text]
                            elif x.tag == p + "TimeType":
                                xml_item['time_type'] = [x.text]
                            elif x.tag == p + "SpnName" and x.text is not None:
                                xml_item['name_spanish'] = [x.text]
                            elif x.tag == p + "EngName":
                                xml_item['name_english'] = [x.text]
                            elif x.tag == p + "ImagePath_Large" and x.text is not None:
                                urls.append(self.get_absolute(x.text))
                                xml_item['normal_image_url'] = [self.get_server_path(self.get_absolute(x.text))]
                            elif x.tag == p + "IsActive":
                                if x.text == 0:
                                    xml_item['in_stock'] = ["NOT_IN_STOCK"]
                                else:
                                    xml_item['in_stock'] = ['IN_STOCK']
                            else:
                                for i in range(1, 4):
                                    tag = p + "Alternate%sImagePath_Large" % (str(i))
                                    if x.tag == tag and x.text is not None:
                                        urls.append(self.get_absolute(x.text))
                                        xml_item['normal_image_url'].append(self.get_server_path(self.get_absolute(x.text)))
                                        # change image paths for normal_image_url and return urls
                        self.xml.create_xml(xml_item)
                        urls_all += urls
        for i in range(0, len(self.no_urls['status'])):
            if self.no_urls['status'][i] != 'ran':
                self.no_urls['status'][i] = 'not_found'
        return urls_all

    def get_server_path(self, url):
        path = self.images_store + "/full/" + hashlib.sha1(url).hexdigest() + ".jpg"
        return path

    def get_absolute(self, url):
        return "http://www.celebratinghome.com/" + url

    def escape(self, string):
        temp = HTMLParser.HTMLParser().unescape(string)
        return HTMLParser.HTMLParser().unescape(temp)

    def spider_closed(self, spider):
        """Handles spider_closed signal from end of scraping.
        Handles usual end operations for scraper like writing xml, exporting
        to database and sending appropriate mail message."""
        msg = "Ran: {0}\n".format(datetime.now())
        if self.total - self.number:
            msg += "{0} id(s) from id list weren't found in feed".format(self.total - self.number)
            basic.warning(msg)
        else:
            msg += "All ids found in feed."
            basic.green(msg)
        # filename for writing xml
        if self.d['database']:
            try:
                self.database.connect()
                filename = self.database.get_name(self.d['catalog_id'])
                self.database.update_db(self.no_urls)
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
                #exp.xml_to_db(self.name, self.d['file'], "40b029c9-dff7-4bc1-b8bc-ef062960b24d")
                #msg += "\n\nExport to database successful"
            #except StandardError:
                #msg += "\n\nExport to database failed"
        #else:
            #msg += "\n\nUpload to database not selected"
        from modules.mail import Mail
        mail = Mail()
        try:
            mail.send_mail(msg, "CelebratingHome: {0}".format(filename))
            if self.d['email']:
                mail.send_mail(msg, "CelebratingHome: {0}".format(filename), self.d['email'])
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
            self.products['product_ids'] = xls.read_excel_collumn_for_ids(1, 15)
            self.products['names'] = xls.read_excel_collumn(2, 15)
            self.products['urls'] = xls.read_excel_collumn_for_urls(3, 15)
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
        xml.add_property("description_english", "Description English", "text")
        xml.add_property("description_spanish", "Description Spanish", "text")
        xml.add_property("add_to_cart_id", "Add To Cart ID", "text")
        xml.add_property("max_qty", "Max Quantity", "text")
        xml.add_property("time_type", "Time Type", "text")
        xml.add_property("name_english", "Name English", "text")
        xml.add_property("name_spanish", "Name Spanish", "text")
        xml.add_property("in_stock", "In Stock", "text")
        xml.add_property("custom_price", "Custom Price", "text")
