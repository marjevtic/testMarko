def replace_color_json(string):
    string = string.replace('cname','"cname"')
    string = string.replace('enh', '"enh"')
    string = string.replace('reg', '"reg"')
    return string


def replace_for_json(string):
    string = string.replace('skuId','"skuId"')
    string = string.replace('colorCode','"colorCode"')
    string = string.replace('swatchURL','"swatchURL"')
    string = string.replace('ColorDesc','"ColorDesc"')
    string = string.replace('sizeObject','"sizeObject"')
    string = string.replace('sizeCode','"sizeCode"')
    string = string.replace('sizeDesc','"sizeDesc"')
    string = string.replace('skuPrice','"skuPrice"')
    return string


def add_properties(xml):
    xml.add_property("variants", "Variants", "text_list")
    xml.add_property("all_sizes", 'All Sizes', "text")
    xml.add_property('color_json', 'Color json', 'text_list')
    xml.add_property('old_price', 'Old Price', 'text')
    xml.add_property("features", "Features", "text")
    xml.add_property("in_stock", "In Stock", "text")
    xml.add_property("product_link", "Product Link", "text")
