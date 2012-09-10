# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

# The code in here is for loading spider specific settings
# Make sure to use the spider name for all directories and everything related
# for that spider
# e.g. if your new project name is example the use that name everywhere: name
# of spider should be example, directories should be e.g. xml/example,
# xls/example, project_modules/example,...

import sys
from scrapy.conf import settings

cur_settings = "project_modules.{0}.settings".format(sys.argv[1])
_temp = __import__(cur_settings, globals(), locals(), ['project_settings'], -1)
settings.overrides.update(_temp.project_settings)

