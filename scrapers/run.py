from modules.terminal import NewProjectTerminal
import sys
import os
import re
from xlwt import *


def green_print(string, inline=False):
    """Function for printing green."""
    if inline:
        print "\033[92m{0}\033[0m".format(string),
    else:
        print "\033[92m{0}\033[0m".format(string)
def red_print(string):
    print "\033[93m{0}\033[0m".format(string)


terminal = NewProjectTerminal(sys.argv, "adding_catalog")
d = terminal.get_arguments()

name = re.match('[a-z]*_[a-z]*', d['name'])
if not name:
    name = re.match('[a-z][a-z]*', d['name'])
if not name or name.group() != d['name']:
    red_print("Invalid name for project. Name can be of format:")
    print "\t1. example"
    print "\t2. eaxmple_site"
    print "Format is one or two words separated with '_'"
    os._exit(0)

name = d['name']

if '_' in name:
    n = name.replace('_', ' ')
    class_name = n.title().replace(' ','')
else:
    class_name = name.title()



spider_template = r'''from scrapy.contrib.spiders import CrawlSpider
from scrapy.selector import HtmlXPathSelector
import modules.basic_func as basic
from modules.zmags_xml import CommonXml
from modules.excel import DictExcel
from modules.exception import ZmagsException
from modules.terminal import DatabaseTerminal
from modules.export_to_db import CommonExport
from project_modules.{0} import {1}Item
from datetime import datetime
import hashlib
import urllib2
import simplejson
import sys

import re
import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

class {1}Spider(CrawlSpider):
    name = "{0}"
    allowed_domains = ["zmags.com"]
    start_urls = ["http://www.zmags.com"]
    counter = 0

    def __init__(self, *a, **kw):
        super({1}Spider, self).__init__(*a, **kw)
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
        item = {1}Item()

    def handle_not_provided(self):
        item = {1}Item()
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
        msg = "Ran: {{0}}".format(datetime.now())
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
                exp.xml_to_db(self.name, filename, "upload key here")
                msg += "\n\nExport to database successful"
            except StandardError:
                msg += "\n\nExport to database failed"
        else:
            msg += "\n\nUpload to database not selected"
        ## part for exporting to database here
        from modules.mail import Mail
        mail = Mail()
        try:
            mail.send_mail(msg, "{1}: {{0}}".format(filename))
            if self.d['email']:
                mail.send_mail(msg, "{1}: {{0}}".format(filename), self.d['email'])
        except:
            msg += "\nSending mail failed."
        if self.d['database']:
            path = "logs/{{0}}".format(self.name)
            if not os.path.exists(path):
                os.makedirs(path)
            with open("{{0}}/{{1}}".format(path, filename), 'w') as f:
                f.write(msg)

    def get_lists_from_excel(self):
        xls = DictExcel(basic.get_excel_path(self.name, self.d['file']))
        self.products = dict()
        try:
            self.products['urls'] = xls.read_excel_collumn_for_urls(3, 15)
            self.products['product_ids'] = xls.read_excel_collumn_for_ids(1, 15)
            self.products['names'] = xls.read_excel_collumn(2, 15)
        except IOError as e:
            msg = "I/O error {{0}}: {{1}}".format(e.errno, e.strerror)
            msg += "\nError occurred for given file: {{0}}".format(self.d['file'])
            self.exc.code_handler(103, msg=msg)
        except StandardError:
            msg = "Error reading excel file"
            msg += "\nError occurred for given file: {{0}}".format(self.d['file'])
            self.exc.code_handler(103, msg=msg)
        self.products= xls.delete_duplicates_dict(self.products)
        self.products, self.no_urls = xls.separate_no_urls(self.products)
        self.products = xls._add_none_status(self.products)
        self.no_urls = xls._add_none_status(self.no_urls)

    def add_properties(self, xml):
        xml.add_property("in_stock", "In Stock", "text")
        xml.add_property("add_to_cart_id", "Add To Cart ID", "text")'''.format(name, class_name)


items_template = """from scrapy.item import Item, Field

class {0}Item(Item):
    product_id =Field()
    name = Field()
    normal_image_url = Field()
    description = Field()
    master_product_id = Field()
    add_to_cart_id = Field()
    price = Field()
    color_id =Field()
    in_stock = Field()
    image_urls = Field()
    images = Field()""".format(class_name)


# check all paths if they already exist


xls_path = "xls/{0}".format(name)
xml_path = "xml/{0}".format(name)
project_modules_path = "project_modules/{0}".format(name)
spider_path = "scrapers/spiders/{0}_spider.py".format(name)
spider_path_pyc = "scrapers/spiders/{0}_spider.pyc".format(name)


check = False
existing = []
if os.path.exists(xls_path):
    existing.append(xls_path)
    check = True
if os.path.exists(xml_path):
    existing.append(xml_path)
    check = True
if os.path.exists(project_modules_path):
    existing.append(project_modules_path)
    check = True
if os.path.exists(spider_path):
    existing.append(spider_path)
    check = True
if os.path.exists(spider_path_pyc):
    existing.append(spider_path_pyc)


if not d['delete']:
    
    if check:
        red_print("There are some directories or spider existing by this name, please check.")
        print "Existing paths:"
        for i in existing:
            print "\t{0}".format(i)
        os._exit(0)

    # creating everything after succesfull check
    os.makedirs(xml_path)
    os.makedirs(xls_path)
    with open(spider_path, 'w') as f:
        f.write(spider_template)
    os.makedirs(project_modules_path)
    file_path = "{0}/__init__.py".format(project_modules_path)
    with open(file_path, 'w') as f:
        f.write(items_template)
    file_path = "{0}/settings.py".format(project_modules_path)
    with open(file_path, 'w') as f:
        f.write("project_settings = {}")
    w = Workbook()
    ws = w.add_sheet('Croatia')
    w.save('{0}/test.xls'.format(xls_path))

else:
    if not existing:
        print "Nothing to delete for name {0}".format(name)
        os._exit(0)
    print "To delete:"
    for i in existing:
        print "\t {0}".format(i)
    while True:
        green_print("Are you sure you want to delete? (yes/no)", True)
        var = raw_input()
        if var == 'yes':
            to_delete = True
            break
        elif var == 'no':
            to_delete = False
            break
    if to_delete:
        import shutil
        for f in existing:
            try:
                print "Deleting directory"
                shutil.rmtree(f)
            except OSError:
                print "Failed, trying to delete file"
                try:
                    os.remove(f)
                except:
                    red_print("Error trying to erase the file")
                    os._exit(0)
        green_print("Project {0} succesfully deleted".format(name))

