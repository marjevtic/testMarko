# Class for creating master products for shop the look and shop
# the line, in constructor need to pass it xls file name and Xml
# object instance that is used in scraper and it will read excel
# for needed ids and create master products
from project_modules.express import ExpressItem
import modules.basic_func as basic


class CreateShops(object):

    def __init__(self, xls_file, xml):
        from modules.excel import CommonExcel
        path = "xls/express/{0}.xls".format(xls_file)
        self.excel = CommonExcel(path)
        self.xls_file = xls_file
        self.xml = xml

    def get(self):
        shop_look_ids = self.excel.read_excel_collumn(0, 1, 1)
        shop_look_names = self.excel.read_excel_collumn(1, 1, 1)
        shop_look_images = self.excel.read_excel_collumn_for_urls(2, 1, 1)
        self._create_shop_looks(shop_look_ids, shop_look_names, shop_look_images)

        shop_line_ids = self.excel.read_excel_collumn(0, 1, 2)
        shop_line_names = self.excel.read_excel_collumn(1, 1, 2)
        self._create_shop_lines(shop_line_ids, shop_line_names)

    def _create_shop_looks(self, ids, names, urls):
        item = ExpressItem()
        for i in range(0, len(ids)):
            item['product_id'] = [ids[i]]
            item['name'] = [basic.cdata(names[i])]
            item['normal_image_url'] = [basic.cdata(urls[i])]
            item['shop_look'] = ['True']
            item['normal'] = ['False']
            item['shop_line'] = ['False']
            item['in_stock'] = ['IN_STOCK']
            self.xml.create_xml(item)

    def _create_shop_lines(self, ids, names):
        item = ExpressItem()
        for i in range(0, len(ids)):
            item['product_id'] = [ids[i]]
            item['name'] = [basic.cdata(names[i])]
            item['shop_look'] = ['False']
            item['normal'] = ['False']
            item['shop_line'] = ['True']
            item['in_stock'] = ['IN_STOCK']
            self.xml.create_xml(item)
