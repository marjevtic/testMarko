
from modules import BaseXml


class CommonXml(BaseXml):
    def __init__(self, properties=True):
        super(CommonXml, self).__init__()
        if properties:
            self.properties = self.ET.Element("properties")
            self.products.insert(0, self.properties)

    def add_property(self, identifier, name, value):
        """Function that adds property to tags if needed."""
        prop = self.ET.Element("property")
        self.properties.append(prop)
        prop.attrib["identifier"] = identifier
        prop.attrib["display-name"] = name
        prop.attrib["value-type"] = value

    def write_xml(self, project_name, file_name="export"):
        """Writes xml tree generated during the scrape into string and in file.
        It checks for file if it exists already by a given name and if it does
        it keeps the last on under the name of passed value plus '_backup'"""
        import os
        new_path = 'xml/{0}/'.format(project_name)
        if not os.path.exists(new_path):
            os.makedirs(new_path)
        print "Writing to xml file..."
        output = self.ET.tostring(self.products, "utf-8")
        directory = os.path.join((os.path.join(os.getcwd(),
                                 "xml/{0}/".format(project_name))),
                                 file_name + ".xml")
        dir_new = os.path.join((os.path.join(os.getcwd(),
                               "xml/{0}/".format(project_name))),
                               file_name + "_backup.xml")
        if os.path.exists(directory):
            if os.path.exists(dir_new):
                os.remove(dir_new)
            os.rename(directory, dir_new)
        output = self._replace_characters(output)
        with open("xml/{0}/{1}.xml".format(project_name, file_name), 'w') as f:
            f.write(output)
        print "Writing to xml file finished"

    def _replace_characters(self, output):
        """Private function to un-escape some signs.
        Un-escapes some signs that are escaped by default in xmletree so they
        wouldn't break xml tree, but we need them in order to have CDATA."""
        output = output.replace("&amp;", '&')
        output = output.replace("&quot;", '"')
        output = output.replace("&lt;", "<")
        output = output.replace("&gt;", ">")
        return output


class VariantsXml(CommonXml):

    def write_xml(self, project_name, file_name="export"):
        import os
        new_path = 'xml/{0}/'.format(project_name)
        if not os.path.exists(new_path):
            os.makedirs(new_path)
        print "Writing to xml file..."
        self.delete_variants(project_name)
        output = self.ET.tostring(self.products, "utf-8")
        directory = os.path.join((os.path.join(os.getcwd(),
                                 "xml/{0}/".format(project_name))),
                                 file_name + ".xml")
        dir_new = os.path.join((os.path.join(os.getcwd(),
                               "xml/{0}/".format(project_name))),
                               file_name + "_backup.xml")
        if os.path.exists(directory):
            if os.path.exists(dir_new):
                os.remove(dir_new)
            os.rename(directory, dir_new)
        output = self._replace_characters(output)
        with open("xml/{0}/{1}.xml".format(project_name, file_name), 'w') as f:
            f.write(output)
        print "Writing to xml file finished"

    def delete_variants(self, project_name):
        """Function for getting variants that needs to be deleted for products.
        Gets all previous variants for products that are scraped in current
        scrape. All variants are stored as dicts in the way that main id is the
        key and all possible variants for it are values. So here it gets all
        previous variants for specific product and updates current xml with
        them so we delete all variants in database for that product."""
        import simplejson
        import os
        try:
            with open('variants/{0}'.format(project_name), 'r') as f:
                ids = f.read()
                ids = simplejson.loads(ids)
        except IOError:
            print "File doesn't exist yet"
            ids = dict()
        # read ids from file into a dict
        current_dict = {}
        for i in self.delete:
            # add each id from delete to current_dict the same way it's in the
            # dict with all ids
            if "_" in i.text:
                self._add_to_dict(current_dict, i.text.split("_")[0], i.text)
            else:
                self._add_to_dict(current_dict, i.text, i.text)
        # go through all keys in ids
        for i in current_dict:
            # see if id in current_dict
            if i in ids:
                # if it is create new field with all child ids in it
                # from both of those
                all_ids = list(set(ids[i] + current_dict[i]))
                all_ids.sort()
                # write those all ids to ids on the right place/key
                ids[i] = all_ids
                # go through that new field
                for x in ids[i]:
                    # if id is not in current_id (delete) put it in there
                    # for deletion
                    if x not in current_dict[i]:
                        self._add_element("product_id", x, self.delete)
            else:
                ids[i] = current_dict[i]
        # write new ids to file
        with open('variants/{0}'.format(project_name), 'w') as f:
            f.write(simplejson.dumps(ids))

    def _add_to_dict(self, d, key, value):
        try:
            d[key].append(value)
        except:
            d[key] = [value]
