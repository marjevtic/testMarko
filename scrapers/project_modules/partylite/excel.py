from modules.excel import DictExcel

class PartyliteExcel(DictExcel):

    def __init__(self, path, user="serino", production=True):
        super(PartyliteExcel, self).__init__(path)
        self.user = user
        self.production = production

    def read_excel_collumn_for_urls(self, collumn, offset=0):
        sh = self.book.sheet_by_index(0)
        urls = []
        for rx in range(offset, sh.nrows):
            var = sh.cell_value(rowx=rx, colx=collumn)
            if "http://" not in var:
                var = "http://www.zmags.com/"
            var = var.replace("XXXXX", self.user)
            if not self.production:
                var = var.replace("www","qa")
            urls.append(var) 
        return urls
