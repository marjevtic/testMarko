# Class for handling interaction with database
#
# methods in this class that are not "private":
#
# connect           -   connects to the database, and instantiates
#                       cursor used in the class
#-----------------------------------------------------------------------
# disconnect        -   disconnects from the database
#-----------------------------------------------------------------------
# select_products   -   takes catalog_id and optionally product_id
#                       and returns dict that contains product info to
#                       be used in scraper, also saves class internal
#                       dict of products that don't have valid url in
#                       database
#-----------------------------------------------------------------------
# get_xls_file      -   gets xls file name and takes catalog_id
#-----------------------------------------------------------------------
# update_db         -   takes products dict and updates the database if
#                       if needed with new statuses


import MySQLdb as mdb


class Database:

    def __init__(self):
        pass

    def connect(self):
        self.db = mdb.connect(host="localhost", user="root",
                              passwd="ivan", db="zmags1")
        self.cur = self.db.cursor()

    def disconnect(self):
        if self.db.open == 1:
            self.cur.close()
            self.db.close()

    def select_products(self, catalog_id, product_id="None"):
        if product_id == "None":
            self.cur.execute("SELECT id,name,product_link,product_id,status \
                             FROM scraper_gui_product WHERE catalog_id=%s" %
                             (catalog_id))
        else:
            self.cur.execute("SELECT id,name,product_link,product_id,status \
                             FROM scraper_gui_product WHERE id=%s" %
                             (product_id))
        rows = self.cur.fetchall()
        products = self._initialize_dict()
        self.products_no_url = self._initialize_dict()
        for row in rows:
            if (row[2].startswith("http://")):
                self._populate_dict(products, row)
            else:
                self._populate_dict(self.products_no_url, row)
        return products, self.products_no_url

    def get_xls_file(self, catalog_id):
        query = ("SELECT xls_file FROM scraper_gui_catalog WHERE id=%s"
                 % (catalog_id))
        self.cur.execute(query)
        return self.cur.fetchall()[0][0]

    def get_name(self, catalog_id):
        query = ("SELECT name FROM scraper_gui_catalog WHERE id=%s"
                 % (catalog_id))
        self.cur.execute(query)
        return self.cur.fetchall()[0][0]

    def update_db(self, products):
        # to do: see if it's better to keep connection open until the
        # end of the script or to close it and open new one at the end
        # of the scraping
        wh_st = []
        in_st = []
        wh_st, in_st = self._get_update_fields(wh_st, in_st, products)
        wh_st, in_st = self._get_update_fields(wh_st, in_st,
                                               self.products_no_url, True)
        query = self._make_update_query(wh_st, in_st)
        self.cur.execute(query)
        print "Number of rows updated: %d" % self.cur.rowcount
        self.db.commit()

    def _get_update_fields(self, when_string, in_string, d, no_url=False):
        print d
        for p in d['ids']:
            index = d['ids'].index(p)
            if no_url is False:
                when_string.append("WHEN %s THEN '%s'" % (d['ids'][index],
                                   d['status'][index]))
            else:
                when_string.append("WHEN %s THEN '%s'" % (d['ids'][index],
                                   'no_url'))
            in_string.append(str(d['ids'][index]))
        return when_string, in_string

    # internal function for making update query for all products
    def _make_update_query(self, when_string, in_string):
        table = "scraper_gui_product"
        when_string = " ".join(when_string)
        in_string = "(%s)" % (",".join(in_string))
        query = "UPDATE %s SET status = CASE id " % (table)
        query += when_string + " END WHERE id IN %s" % (in_string)
        return query

    def _initialize_dict(self):
        d = {}
        d['ids'] = []
        d['names'] = []
        d['urls'] = []
        d['product_ids'] = []
        d['status'] = []
        return d

    def _populate_dict(self, d, row):
        d['ids'].append(row[0])
        d['names'].append(row[1])
        d['urls'].append(row[2])
        d['product_ids'].append(row[3])
        d['status'].append(row[4])
        return d
