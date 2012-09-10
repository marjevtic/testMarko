import sys
import os
import xlrd
import sys
from xlwt import *

# script to parse express excel files to update available urls
# on their page. Script is called in command line simply by
#           python update.py -a file=file_name
# where file name is one of the file names that are used for
# scraping express prodcuts but without .xls part
# example of calling script:
#
#          python update.py -a file=august
#
# this will call script for august.xls file and update urls in
# that xls file


from mechanize import ParseResponse, urlopen, urljoin
working_file = None
all_products = False
for arg in sys.argv:
    if "=" in arg:
        if "file=" in arg:
            working_file = arg.split("file=")[1]
        elif "all=" in arg:
            if arg.split("all=")[1] == "yes":
                all_products = True
            else:
                print "Only option for 'all' is 'yes'"
                os._exit(2)
        else:
            print 'option "{0}" not suported'.format(arg.split("=")[0])
            os._exit(2)


def get_url(var):
    form['keyword'] = str(var)
    sys.stdout.write("\r{0} for id {1}".format(msg, form['keyword']))
    sys.stdout.flush()
    response_page = urlopen(form.click())
    url = response_page.geturl()
    if "http://www.express.com/catalog/search.cmd?" in url:
        url = ''
        global not_found
        not_found += 1
    return url

if not working_file:
    print "Can't run script without giving file name"
    print "\tpython update.py -a file=august"
    print "Don't use .xls in names. Use only file names from xls directory"
    os._exit(2)

working_file = "{0}.xls".format(working_file)
if not os.path.exists(working_file):
    print "File you selected does not exist"
    print "Files available for this script:"
    files = os.listdir(".")
    for f in files:
        if '.xls' in f and '.xlsx' not in f:
            print "\t{0}".format(f.replace(".xls", ""))
    os._exit(2)

w = Workbook()
ws = w.add_sheet('Products')

response = urlopen("http://www.express.com/home.jsp")
forms = ParseResponse(response, backwards_compat=False)
form = forms[0]
book = xlrd.open_workbook(working_file)
sh = book.sheet_by_index(0)

total = 0
current = 0
not_found = 0

for rx in range(sh.nrows):
    if sh.cell_value(rowx=rx, colx=4) == '':
        total += 1
if all_products:
    total = sh.nrows

for rx in range(sh.nrows):
    for cx in range(sh.ncols):
        flag = 0
        if cx == 4:
            if all_products:
                current += 1
                msg = "\rparsing " + str(current) + " of " + str(total)
                var = sh.cell_value(rowx=rx, colx=0)
                url = get_url(var)
                ws.write(rx, cx, url)
                flag = 1
            else:
                if sh.cell_value(rowx=rx, colx=cx) == '':
                    current += 1
                    msg = "\rparsing " + str(current) + " of " + str(total)
                    var = sh.cell_value(rowx=rx, colx=0)
                    url = get_url(var)
                    ws.write(rx, cx, url)
                    flag = 1
        if flag == 0:
            ws.write(rx, cx, sh.cell_value(rowx=rx, colx=cx))

print "\n"

for i in range(1, 3):
    try:
        sh = book.sheet_by_index(i)
    except IndexError as e:
        print "Sheet does not exist"
    else:
        if i == 1:
            shop_look = w.add_sheet('Get Look')
        elif i == 2:
            shop_line = w.add_sheet('Get Line')
        for rx in range(sh.nrows):
            for cx in range(sh.ncols):
                if i == 1:
                    shop_look.write(rx, cx, sh.cell_value(rowx=rx, colx=cx))
                elif i == 2:
                    shop_line.write(rx, cx, sh.cell_value(rowx=rx, colx=cx))

print "Updated {0} out of {1} missing links".format(total - not_found, total)
if os.path.exists(working_file):
    os.remove(working_file)
w.save(working_file)
