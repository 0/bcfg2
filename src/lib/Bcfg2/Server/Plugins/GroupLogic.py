""" GroupLogic is a connector plugin that lets you use an XML Genshi
template to dynamically set additional groups for clients. """

import os
import lxml.etree
import Bcfg2.Server.Plugin
from Bcfg2.Server.Plugins.Metadata import MetadataGroup
try:
    from Bcfg2.Server.Plugins.Bundler import BundleTemplateFile
except ImportError:
    # BundleTemplateFile missing means that genshi is missing.  we
    # import genshi to get the _real_ error
    import genshi  # pylint: disable=W0611


class GroupLogicConfig(BundleTemplateFile):
    """ Representation of the GroupLogic groups.xml file """
    create = lxml.etree.Element("GroupLogic",
                                nsmap=dict(py="http://genshi.edgewall.org/"))

    def __init__(self, name, fam):
        BundleTemplateFile.__init__(self, name,
                                    Bcfg2.Server.Plugin.Specificity(), None)
        self.fam = fam
        self.should_monitor = True
        self.fam.AddMonitor(self.name, self)

    def _match(self, item, metadata):
        if item.tag == 'Group' and not len(item.getchildren()):
            return [item]
        return BundleTemplateFile._match(self, item, metadata)


class GroupLogic(Bcfg2.Server.Plugin.Plugin,
                 Bcfg2.Server.Plugin.Connector):
    """ GroupLogic is a connector plugin that lets you use an XML
    Genshi template to dynamically set additional groups for
    clients. """
    # perform grouplogic later than other Connector plugins, so it can
    # use groups set by them
    sort_order = 1000

    def __init__(self, core, datastore):
        Bcfg2.Server.Plugin.Plugin.__init__(self, core, datastore)
        Bcfg2.Server.Plugin.Connector.__init__(self)
        self.config = GroupLogicConfig(os.path.join(self.data, "groups.xml"),
                                       core.fam)

    def get_additional_groups(self, metadata):
        rv = []
        for el in self.config.get_xml_value(metadata).findall("Group"):
            if el.get("category"):
                rv.append(MetadataGroup(el.get("name"),
                                        category=el.get("category")))
            else:
                rv.append(el.get("name"))
        return rv
