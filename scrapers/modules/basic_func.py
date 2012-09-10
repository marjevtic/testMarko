__author__ = "Ivan"
__date__ = "$10.02.2012. 13:25:54$"

#module with some useful functions that are used in most scrapers
import re
import hashlib


def clean_string(string):
    string = string.replace("\r", "")
    string = string.replace("\n", "")
    string = string.replace("\t", "")
    return string

    
def cdata(string):
    return '<![CDATA[' + string + ']]>'


def cdata_field(field):
    new = []
    for i in range(0, len(field)):
        new.append('<![CDATA[' + field[i] + ']]>')
    return new


def clean_spaces_field(field):
    new = []
    for string in field:
        string = string.replace(" ", "")
        new.append(string)
    return new


def remove_tags(string):
    return re.sub('<.*?>', '', string)


def get_middle_text(string, start, end):
    tmp = string.split(start)
    result = []
    if len(tmp) == 1:
        return result
    for x in range(1, len(tmp)):
        temp = tmp[x].split(end)[0]
        result.append(temp)
    return result


def add_to_dict(dict, index, value):
    try:
        dict[index].append(value)
    except:
        if (type(value) == list):
            dict[index] = value
        else:
            dict[index] = [value]
    return dict


def add_to_list(list, value):
    try:
        list.append(value)
    except:
        if (type(value) == list):
            list = value
        else:
            list = [value]
    return list


def print_status(counter, total):
    print "-------------------------------------------------------------------"
    print "Scraping url {0} of {1}".format(counter, total)
    print "-------------------------------------------------------------------"


def not_provided():
    print "-------------------------------------------------------------------"
    print "**************URL NOT PROVIDED FOR THIS PRODUCT********************"
    print "-------------------------------------------------------------------"


def print_error():
    print "-------------------------------------------------------------------"
    print "-------------------------------------------------------------------"
    print "*****************ERROR SCRAPING THIS PRODUCT***********************"
    print "-------------------------------------------------------------------"
    print "-------------------------------------------------------------------"


def print_not_finished():
    print "-------------------------------------------------------------------"
    print "-------------------------------------------------------------------"
    print "****************SCRAPER DIDN'T FINISH FOR ALL**********************"
    print "-------------------------------------------------------------------"
    print "-------------------------------------------------------------------"


def get_excel_path(project_name, file_name):
    return "xls/{0}/{1}.xls".format(project_name, file_name)


def green(string, inline=False):
    if inline:
        print "\033[92m{0}\033[0m".format(string),
    else:
        print "\033[92m{0}\033[0m".format(string)


def warning(string):
    print "\033[93m{0}\033[0m".format(string)


def get_price(string):
    return re.sub('[^0-9,.]', '', string)


def cut_string(string, splitter, part=0):
    return string.split(splitter)[part]


def cut_string_field(strings, splitter, part=0):
    new = []
    for string in strings:
        if splitter in string:
            new.append(cut_string(string, splitter, part))
        else:
            new.append(string)
    return new