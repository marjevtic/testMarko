class Logger(object):

    def __init__(self):
        self.message = ''

    def add_message(self, msg, blank=False, tab=False, nblank=1, ntab=1):
        """Adds new message with options of blank line and tab.
        Also an option to send number of blank_lines/tabs to put in."""
        self.message += '\n'
        if blank:
            for i in range(nblank):
                self.message += '\n'
        if tab:
            for i in range(ntab):
                self.message += '\t'
        self.message += msg

    def get_message(self):
        """Returns current message."""
        return self.message

    def get_final_message(self, exc, total):
        """Shortcut for creating final message from messaging and exception.

        Takes exceptin instance and total as arguments and returns final
        message from both messaging and exception as a shortcut instead of
        calling both and concatenating in code"""
        return "{0} \n\n {1}".format(self.message, exc.create_message(total))
