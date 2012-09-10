

class Downloader(object):
    """Class for downloading files for feeds."""

    def __init__(self):
        import os
        import urllib2
        import sys
        self.os = os
        self.urllib2 = urllib2
        self.sys = sys

    def get_file(self, directory, url, name, extension=".xml"):
        """Function for downloading files.
        Attributes- directory for directory where to store, url for url from
        which to download from, name for the name by what it will be stored,
        and extension for file extension"""
        print "Getting file...."
        name = "{0}{1}".format(name, extension)
        dir_main = self.os.path.join(directory, name)
        try:
            s = self.urllib2.urlopen(url)
        except:
            return 404
        f = open(dir_main,'wb+')
        meta = s.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (name, file_size)
        current_file_size = 0
        block_size = 4096
        while True:
            buf = s.read(block_size)
            if not buf:
                break
            current_file_size += len(buf)
            f.write(buf)
            status = ("\r%10d  [%3.2f%%]" %
                     (current_file_size, current_file_size * 100. / file_size))
            status = status + chr(8)*(len(status)+1)
            self.sys.stdout.write(status)
            self.sys.stdout.flush()
        f.close()
        print "\nDone getting feed"
        return 200
