# To change this template, choose Tools | Templates
# and open the template in the editor.

__author__ = "Ivan"
__date__ = "$15.02.2012. 16:14:37$"


class Export(object):

    def xml_to_db(self, file_path, key):
        import MultipartPostHandler
        import urllib2

        url = 'http://api.admin.zmags.com/product/import?key=' + key

        params = {'file': file(file_path, 'rb'), 'param1': 'hello'}
        # see why token isn't working
        opn = urllib2.build_opener(MultipartPostHandler.MultipartPostHandler)
        code = opn.open(url, params).getcode()

        if (code != 202):
            print ("Achtung")


class CommonExport(Export):
    def xml_to_db(self, project, file_name, key):
        import MultipartPostHandler
        import urllib2
        file_path = "xml/{0}/{1}.xml".format(project, file_name)
        url = 'http://api.admin.zmags.com/product/import?key=' + key

        params = {'file': file(file_path, 'rb'), 'param1': 'hello'}
        # see why token isn't working
        opn = urllib2.build_opener(MultipartPostHandler.MultipartPostHandler)
        code = opn.open(url, params).getcode()

        if (code != 202):
            print ("Achtung")
