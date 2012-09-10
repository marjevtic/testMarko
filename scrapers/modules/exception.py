__author__ = "Ivan"
__date__ = "$10.02.2012. 12:32:37$"

# class for handling different errors that can occur in typical scraper,
# function create_message is called when you want to create message to send
# on mail with scraper report
# codes for errors:
#        100    =   unhandled errors (that need to be checked)
#        101    =   url not provided for product in excel sheet
#        102    =   product not available on client page
#        103    =   exit scraper with given message
#        104    =   internal error on client page(404...)

# to do: add a variable that can be set to stop scraper after certain number of
# unhandled errors and send appropriate message on mail


class ZmagsException(object):

    #def __init__(self, max_number, title): where title will be scraper name,
    # and create message will handle
    #sending mail along creating message
    def __init__(self, max_number, name="No name"):
        self.maximum = max_number
        self.name = name
        self.counter_100 = 0
        self.counter_101 = 0
        self.counter_102 = 0
        self.counter_104 = 0
        self.list_100 = []
        self.list_102 = []

    def code_handler(self, code, cur_url="no url provided", msg=None):
        if code == 100:
            return self.handler_100(cur_url)
        elif code == 101:
            return self.handler_101()
        elif code == 102:
            return self.handler_102(cur_url)
        elif code == 103:
            return self.handler_103(msg)
        elif code == 104:
            return self.handler_104()

    def handler_100(self, cur_url):
        self.counter_100 += 1
        if self.counter_100 > self.maximum:
            self.end_script()
        self.list_100.append(cur_url)

    def handler_101(self):
        self.counter_101 += 1

    def handler_102(self, cur_url):
        self.counter_102 += 1

    def handler_103(self, msg):
        self.end_with_message(msg)

    def handler_104(self):
        self.counter_104 += 1

    def create_message(self, total_number):
        nl = "\n"
        msg = "Scraper report:" + nl + nl
        msg += "Scraping finished, scraped {0} products,".format(total_number)
        msg += " {0} not provided, {1} not available".format(self.counter_101,
                                                             self.counter_102)
        msg += ", {0} internal errors on client page".format(self.counter_104)
        msg += ", and {0} unhandled errors.".format(self.counter_100)
        if self.list_100:
            msg += nl + nl + "Unhandled errors occurred on:" + nl + nl
            msg += "\n".join(self.list_100)
        return msg

    def end_script(self):
        print "Script terminated after {0} errors".format(self.maximum)
        nl = "\n"
        msg = "Scraping terminated after\
               error occurred on {0} urls.".format(self.maximum)
        l = "\n".join(self.list_100)
        msg += nl + nl + "those errors occurred on:" + nl
        msg += l
        from modules.mail import Mail
        mail = Mail()
        mail.send_mail(msg, self.name)
        import os
        os._exit(1)

    def end_with_message(self, msg):
        if not msg:
            msg = "Script has been terminated with no message provided"
        print msg
        from modules.mail import Mail
        mail = Mail()
        mail.send_mail(msg, self.name)
        import os
        os._exit(1)
