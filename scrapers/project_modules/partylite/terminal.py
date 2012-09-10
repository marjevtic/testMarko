from modules.terminal import DatabaseTerminal

class PartyliteTerminal(DatabaseTerminal):
    def get_custom_arguments(self, current, value):
        super(PartyliteTerminal, self).get_custom_arguments(current, value)
        if current == 'lang':
            if value == "french" or value == 'english':
                self.d[current] = value
            else:
                print "lang option can only be set to 'french' or 'english'"
                self.os._exit(3)
        elif current == 'env':
            if value == 'dev':
                self.d[current] = False
            else:
                print "env option can only be set to 'dev'"
                self.os._exit(3)

    def _add_options(self):
        super(PartyliteTerminal, self)._add_options()
        self.options['env'] = "default is production set 'dev' for development"
        self.options['lang'] = "default is usa, set 'french' for canada\
                                \t french, or 'english' for canada english"
        self.d['lang'] = 'us'
        self.d['env'] = True

