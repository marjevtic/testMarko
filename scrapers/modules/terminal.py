from modules import BaseTerminal
import modules.basic_func as basic


class CommonTerminal(BaseTerminal):
    """Common class used for terminal commands.
    This class has two basic command line arguments: file and upload.
    File is to select what file to run scraper for and upload is whether to
    upload automatically to database or not."""

    def __init__(self, *a, **kwargs):
        super(CommonTerminal, self).__init__(*a, **kwargs)
        import os
        self.os = os
        self.options['file'] = 'provide file name in here which to scrape'
        self.options['upload'] = 'put no if you do not want automatic upload'
        self.mandatory.append('file')

    def get_arguments(self):
        xls_file = None
        self.d['upload'] = True
        for arg in self.args:
            if "=" in arg:
                current = arg.split('=')[0]
                if current in self.options:
                    if current == "file":
                        xls_file = arg.split('=')[1]
                        self.__check_file(xls_file)
                        self.d[current] = xls_file
                    elif current == "upload":
                        upload = self.__check_upload(arg.split('=')[1])
                        self.d[current] = False
                    else:
                        self.get_custom_arguments(current, arg.split('=')[1])
                else:
                    print "Option {0} not supported".format(current)
                    self.print_arguments()
                    self.os._exit(3)
        self._check_mandatory()
        self._check_valid()
        return self.d

    def get_custom_arguments(self, current, value):
        """Override this function to handle new terminal options"""

    def __check_file(self, file_name):
        path = "xls/{0}/{1}.xls".format(self.name, file_name)
        print path
        if not self.os.path.exists(path):
            basic.warning("File you selected does not exist")
            basic.green("Files available for this script:")
            files = self.os.listdir("xls/{0}/".format(self.name))
            for f in files:
                if '.xls' in f and '.xlsx' not in f:
                    if not f.startswith('.'):
                        basic.green("\t{0}".format(f.replace(".xls", "")))
            self.os._exit(3)

    def __check_upload(self, value):
        if value != "no":
            print "Error: Upload option can only be 'no', yes is default"
            self.os._exit(3)
        else:
            return False

    def _check_mandatory(self):
        for k in self.mandatory:
            if k not in self.d:
                basic.warning("Option '{0}' is mandatory.".format(k))
                self.print_arguments()
                self.os._exit(3)

    def _check_valid(self):
        """Override this function for more checking options"""


class NewProjectTerminal(BaseTerminal):
    """Class used for run.py script for adding/deleting new projects."""

    def __init__(self, *a, **kwargs):
        super(NewProjectTerminal, self).__init__(*a, **kwargs)
        import os
        self.os = os
        self.mandatory.append('name')

    def get_arguments(self):
        for arg in self.args:
            if "=" in arg:
                current = arg.split('=')[0]
                if current in self.options:
                    if current == "name":
                        name = arg.split('=')[1]
                        self.d[current] = name
                    else:
                        self.get_custom_arguments(current, arg.split('=')[1])
                else:
                    print "Option {0} not supported".format(current)
                    self.print_arguments()
                    self.os._exit(3)
        self._check_mandatory()
        return self.d

    def _check_mandatory(self):
        for k in self.mandatory:
            if k not in self.d:
                basic.warning("Option '{0}' is mandatory.".format(k))
                self.print_arguments()
                self.os._exit(3)

    def _add_options(self):
        self.options['name'] = "provide name of new project to create"
        self.options['delete'] = "put delete=yes if you want to delete project"
        self.d['delete'] = False

    def get_custom_arguments(self, current, value):
        if current == 'delete':
            if value == "yes":
                self.d[current] = True
            else:
                print "delete option can only be set to yes"
                self.os._exit(3)



class FeedTerminal(CommonTerminal):
    """Class that support one additional option: donwload.
    Mostly used for feed scrapers to dowloadn/not download new feed."""

    def get_custom_arguments(self, current, value):
        if current == 'download':
            if value == "no":
                self.d[current] = False
            else:
                print "download option can only be set to 'no'"
                self.os._exit(3)

    def _add_options(self):
        self.options['download'] = "default is yes if set 'no' it won't\
                                    \tdonwload feed will use old one if exists"
        self.d['download'] = True

class DatabaseTerminal(CommonTerminal):

    def __init__(self, *a, **kwargs):
        super(DatabaseTerminal, self).__init__(*a, **kwargs)
        self.mandatory.remove('file')

    def get_custom_arguments(self, current, value):
        if current == 'email':
            if value != 'None':
                self.d[current] = value
        elif current == 'catalog_id':
            self.d[current] = value
        elif current == 'client_id':
            self.d[current] = value
        elif current == 'product_id':
            self.d[current] = value
        elif current == 'database':
            if value == 'yes':
                self.d[current] = True
            else:
                print "database option can only be set to yes"
                self.os._exit(3)
        elif current == 'download':
            if value == "no":
                self.d[current] = False
            else:
                print "download option can only be set to 'no'"
                self.os._exit(3)

    def _add_options(self):
        self.options['email'] = "email to send scraping results to"
        self.options['catalog_id'] = 'catalog id in database'
        self.options['product_id'] = 'product id from database'
        self.options['client_id'] = 'client id from database'
        self.options['database'] = 'indicate whether to use database'
        self.options['download'] = "default is yes if set 'no' it won't\
                            \tdonwload feed will use old one if exists"
        self.d['file'] = None
        self.d['email'] = None
        self.d['catalog_id'] = None
        self.d['client_id'] = None
        self.d['product_id'] = None
        self.d['database'] = False
        self.d['download'] = True

    def _check_valid(self):
        msg = "Either 'file' option or 'database' option must be set"
        if not self.d['database'] and not self.d['file']:
            basic.warning(msg)
            self.print_arguments()
            self.os._exit(3)
