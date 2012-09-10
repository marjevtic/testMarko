# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "Ivan"
__date__ = "$10.02.2012. 12:29:13$"


import re
from modules import BaseExcel


class CommonExcel(BaseExcel):
    """Common class used for readind from excel files.
    This class is used in most of the scrapers as reading excel files is pretty
    much the same in all scrapers."""
    def read_excel_collumn_for_urls(self, collumn, offset=0, sheet=0):
        sh = self.book.sheet_by_index(sheet)
        urls = []
        for rx in range(offset, sh.nrows):
            var = sh.cell_value(rowx=rx, colx=collumn)
            if "http://" not in var and "https://" not in var:
                var = "http://www.zmags.com/"
            urls.append(var)
        return map(lambda it: it.strip(), urls)

    def read_excel_collumn_for_ids(self, collumn, offset=0, sheet=0):
        sh = self.book.sheet_by_index(sheet)
        ids = []
        for rx in range(offset, sh.nrows):
            var = sh.cell_value(rowx=rx, colx=collumn)
            if isinstance(var, float):
                var = str(int(var))
            ids.append(var)
        return map(lambda it: it.strip(), ids)

    def delete_duplicates(self, urls, ids, names=False):
        newlist_url = []
        newlist_id = []
        newlist_names = []
        for i in range(0, len(ids)):
            if ids[i] not in newlist_id and ids[i] != "":
                newlist_url.append(urls[i])
                newlist_id.append(ids[i])
                if names:
                    newlist_names.append(names[i])
        if names:
            return newlist_url, newlist_id, newlist_names
        else:
            return newlist_url, newlist_id



class DictExcel(CommonExcel):

    def separate_no_urls(self, products):
        indexes_no_urls = []
        for i in range(0, len(products['urls'])):
            if products['urls'][i] == 'http://www.zmags.com/':
                indexes_no_urls.append(i)
        no_urls = dict()
        no_urls['urls'] = []
        no_urls['product_ids'] = []
        no_urls['names'] = []
        for i in indexes_no_urls:
            no_urls['urls'].append('')
            no_urls['product_ids'].append(products['product_ids'][i])
            no_urls['names'].append(products['names'][i])
        products = self._delete_indexes_from_dict(products, indexes_no_urls)
        return products, no_urls

    def delete_duplicates_dict(self, products):
        """For deleting duplicates"""
        newlist_id = []
        indexes_to_delete = []
        for i in range(0, len(products['product_ids'])):
            if products['product_ids'][i] not in newlist_id:
                newlist_id.append(products['product_ids'][i])
            else:
                indexes_to_delete.append(i)
        products = self._delete_indexes_from_dict(products, indexes_to_delete)
        return products

    def _delete_indexes_from_dict(self, products, indexes):
        for key in products:
            for j in reversed(indexes):
                products[key].pop(j)
        return products

    def _add_none_status(self, products):
        n = len(products['product_ids'])
        products['status'] = []
        for i in range(0, n):
            products['status'].append('none')
        return products
