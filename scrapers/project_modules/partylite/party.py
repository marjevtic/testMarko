def get_settings_message(d):
    """Calculates message for settings used on scrape.
    Takes prod, upload and eng as arguments as boolean values for settings.
    Checks them and return appropriate message for settings used"""
    if d['lang'] == 'us':
        msg = "Running US "
    elif d['lang'] == 'english':
        msg = "Running canada english"
    else:
        msg = "Running canada french" 
    if d['env']:
        msg += " on production "
    else:
        msg += " on development "
    if d['upload']:
        msg += "with upload "
    else:
        msg += "without upload "
    if d['file']:
        msg += "for {0} catalog".format(d['file'])
    return msg


def get_users(settings, d):
    """Gets users used in scraper.
    It gets users from partylite.setting depending on whether it's running
    on production or development environment. Returns dict with
    appropriate users"""
    if d['env']:
        users = settings['USERS_PRODUCTION']
    else:
        users = settings['USERS_DEVELOPMENT']
    return users

def add_properties(xml):
    xml.add_property("review", "Review", "text")
    xml.add_property("recommended", "Recommended", "text_list")
    xml.add_property("add_to_cart_id", "Add To Cart ID", "text")
    xml.add_property("custom_price", "Custom price", "text")
    xml.add_property("custom_discount", "Custom discount price", "text")
    xml.add_property("in_stock", "In Stock", "text")
    xml.add_property("color_id", "Color ID", "text")
    xml.add_property("swatch_color", "Swatch Color", "text")
    xml.add_property("shown_with", "Shown With", "text")
