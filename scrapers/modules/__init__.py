# This module contains base classes used for some of the scrapers modules used
# in scraper framework. Never change anything here unless absolutely sure that
# it won't break any past scraper. Ideally this should never been changed cause
# it's just skeleton for all the other with only code that every class should
# have. If changing anything here check past scrapers to make sure they work


import modules.basic_func as basic


class BaseXml(object):

    def __init__(self):
        """Initializes instance variables used to create xml tree.
        Imports ElementTree and creates basic structure for zmags xml that
        is used in the class to modify it where it needs."""
        from elementtree import ElementTree as ETree
        self.ET = ETree
        self.ET.xml_declaration = "true"
        self.products = self.ET.Element("products")
        schema = "http://schema.zmags.com/product_data_1.0"
        self.products.attrib["xmlns"] = schema
        self.update = self.ET.Element("update")
        self.delete = self.ET.Element("delete")
        self.products.append(self.delete)
        self.products.append(self.update)

    def create_xml(self, item):
        """Puts an element(product) into xml tree.
        Product is passed as a dict and here it gets into xml tree.
        Values of dict passed has to be fields."""
        if len(item) > 0:
            product = self.ET.Element("product")
            self.update.append(product)
            for k, v in item.iteritems():
                for i in range(0, len(v)):
                    if v[i] != "" and v[i] is not None:
                        if k == "product_id":
                            self._add_element(k, v[i], product)
                            self._add_element(k, v[i], self.delete)
                        else:
                            self._add_element(k, v[i], product)

    def to_string(self):
        """Returns string representation of current xml tree."""
        return self.ET.tostring(self.products, "utf-8")

    def _add_element(self, name, text, root_element):
        """Private function that actually does adding to xml tree."""
        product_id = self.ET.Element(name)
        product_id.text = text
        root_element.append(product_id)


class BaseExcel(object):
    """Base class for excel reading.
    All excel reading classes must inherit from this class."""

    def __init__(self, path):
        import xlrd
        self.book = xlrd.open_workbook(path)

    def read_excel_collumn(self, collumn_number, offset=0, sheet=0):
        sh = self.book.sheet_by_index(sheet)
        l = []
        for rx in range(offset, sh.nrows):
            var = sh.cell_value(rowx=rx, colx=collumn_number)
            l.append(var)
        return map(lambda it: it.strip(), l)


class BaseTerminal(object):
    """Base class for getting passed arguments.
    All classes for reading terminal arguments must inherit from this class."""

    def __init__(self, terminal_arguments, name):
        """Takes sys.argv to instantiate this class.
        Name is a current project name for creating paths for xls files."""
        self.args = terminal_arguments
        self.name = name
        self.options = {}
        self.mandatory = []
        self.d = {}
        self._add_options()
        self._add_mandatory()

    def print_arguments(self):
        basic.green("Options supported to pass to catalog are:\n")
        self.__print_options(self.options)

    def __print_option_lie(self, option, description):
        basic.green("\t -a {0}= \t {1}".format(option, description))

    def __print_options(self, options):
        for k in options:
            self.__print_option_lie(k, options[k])

    def _add_options(self):
        """Override this method to allow more terminal options."""

    def _add_mandatory(self):
        """Override this method for adding mandatory options."""
