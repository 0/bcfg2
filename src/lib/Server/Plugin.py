'''This module provides the baseclass for Bcfg2 Server Plugins'''
__revision__ = '$Revision$'

import logging, lxml.etree, re, copy

from lxml.etree import XML, XMLSyntaxError

logger = logging.getLogger('Bcfg2.Plugin')

class PluginInitError(Exception):
    '''Error raised in cases of Plugin initialization errors'''
    pass

class PluginExecutionError(Exception):
    '''Error raised in case of Plugin execution errors'''
    pass

class Plugin(object):
    '''This is the base class for all Bcfg2 Server plugins. Several attributes must be defined
    in the subclass:
    __name__ : the name of the plugin
    __version__ : a version string
    __author__ : the author/contact for the plugin

    Plugins can provide three basic types of functionality:
      - Structure creation (overloading BuildStructures)
      - Configuration entry binding (overloading HandlesEntry, or loads the Entries table)
      - Data collection (overloading GetProbes/ReceiveData)
    '''
    __name__ = 'Plugin'
    __version__ = '$Id$'
    __author__ = 'bcfg-dev@mcs.anl.gov'
    __rmi__ = []

    def __init__(self, core, datastore):
        object.__init__(self)
        self.Entries = {}
        self.core = core
        self.data = "%s/%s" % (datastore, self.__name__)
        self.logger = logging.getLogger('Bcfg2.Plugins.%s' % (self.__name__))

    def BuildStructures(self, _):
        '''Build a set of structures tailored to the client metadata'''
        return []

    def GetProbes(self, _):
        '''Return a set of probes for execution on client'''
        return []

    def ReceiveData(self, _, dummy):
        '''Receive probe results pertaining to client'''
        pass

    def HandlesEntry(self, entry):
        '''This is the slow path method for routing configuration binding requests'''
        return False

    def HandleEntry(self, entry, metadata):
        '''This is the slow-path handler for configuration entry binding'''
        raise PluginExecutionError

    def AcceptEntry(self, metadata, entry_type, entry_name, data):
        '''This is the null per-plugin implementation
        of bcfg2-admin pull'''
        raise PluginExecutionError

    def CommitChanges(self):
        '''Handle revctl commits, if needed'''
        # not implemented yet
        pass

# the rest of the file contains classes for coherent file caching

class FileBacked(object):
    '''This object caches file data in memory.
    HandleEvent is called whenever fam registers an event.
    Index can parse the data into member data as required.
    This object is meant to be used as a part of DirectoryBacked.'''
    
    def __init__(self, name):
        object.__init__(self)
        self.data = ''
        self.name = name
        #self.readonce = 0
        #self.HandleEvent()

    def HandleEvent(self, _=None):
        '''Read file upon update'''
        try:
            self.data = file(self.name).read()
            self.Index()
        except IOError:
            logger.error("Failed to read file %s" % (self.name))
            
    def Index(self):
        '''Update local data structures based on current file state'''
        pass

class DirectoryBacked(object):
    '''This object is a coherent cache for a filesystem hierarchy of files.'''
    __child__ = FileBacked
    patterns = re.compile('.*')

    def __init__(self, name, fam):
        object.__init__(self)
        self.name = name
        self.fam = fam
        self.entries = {}
        self.inventory = False
        fam.AddMonitor(name, self)

    def __getitem__(self, key):
        return self.entries[key]

    def __iter__(self):
        return self.entries.iteritems()

    def AddEntry(self, name):
        '''Add new entry to data structures upon file creation'''
        if name == '':
            logger.info("got add for empty name")
        elif self.entries.has_key(name):
            self.entries[name].HandleEvent()
        else:
            if ((name[-1] == '~') or (name[:2] == '.#') or (name[-4:] == '.swp') or (name in ['SCCS', '.svn'])):
                return
            if not self.patterns.match(name):
                return
            self.entries[name] = self.__child__('%s/%s' % (self.name, name))
            self.entries[name].HandleEvent()

    def HandleEvent(self, event):
        '''Propagate fam events to underlying objects'''
        action = event.code2str()
        if event.filename == '':
            logger.info("Got event for blank filename")
            return
        if action == 'exists':
            if event.filename != self.name:
                self.AddEntry(event.filename)
        elif action == 'created':
            self.AddEntry(event.filename)
        elif action == 'changed':
            if self.entries.has_key(event.filename):
                self.entries[event.filename].HandleEvent(event)
        elif action == 'deleted':
            if self.entries.has_key(event.filename):
                del self.entries[event.filename]
        elif action in ['endExist']:
            pass
        else:
            print "Got unknown event %s %s %s" % (event.requestID, event.code2str(), event.filename)

class XMLFileBacked(FileBacked):
    '''This object is a coherent cache for an XML file to be used as a part of DirectoryBacked.'''
    __identifier__ = 'name'

    def __init__(self, filename):
        self.label = "dummy"
        self.entries = []
        FileBacked.__init__(self, filename)

    def Index(self):
        '''Build local data structures'''
        try:
            xdata = XML(self.data)
        except XMLSyntaxError:
            logger.error("Failed to parse %s"%(self.name))
            return
        self.label = xdata.attrib[self.__identifier__]
        self.entries = xdata.getchildren()

    def __iter__(self):
        return iter(self.entries)

class SingleXMLFileBacked(XMLFileBacked):
    '''This object is a coherent cache for an independent XML File.'''
    def __init__(self, filename, fam):
        XMLFileBacked.__init__(self, filename)
        fam.AddMonitor(filename, self)

class StructFile(XMLFileBacked):
    '''This file contains a set of structure file formatting logic'''
    def __init__(self, name):
        XMLFileBacked.__init__(self, name)
        self.fragments = {}

    def Index(self):
        '''Build internal data structures'''
        try:
            xdata = lxml.etree.XML(self.data)
        except lxml.etree.XMLSyntaxError:
            logger.error("Failed to parse file %s" % self.name)
            return
        self.fragments = {}
        work = {lambda x:True: xdata.getchildren()}
        while work:
            (predicate, worklist) = work.popitem()
            self.fragments[predicate] = [item for item in worklist if item.tag != 'Group'
                                         and not isinstance(item, lxml.etree._Comment)]
            for group in [item for item in worklist if item.tag == 'Group']:
                # if only python had forceable early-binding
                if group.get('negate', 'false') == 'true':
                    cmd = "lambda x:'%s' not in x.groups and predicate(x)"
                else:
                    cmd = "lambda x:'%s' in x.groups and predicate(x)"
                    
                newpred = eval(cmd % (group.get('name')), {'predicate':predicate})
                work[newpred] = group.getchildren()

    def Match(self, metadata):
        '''Return matching fragments of independant'''
        matching = [frag for (pred, frag) in self.fragments.iteritems() if pred(metadata)]
        if matching:
            return reduce(lambda x, y:x+y, matching)
        logger.error("File %s got null match" % (self.name))
        return []

class INode:
    '''LNodes provide lists of things available at a particular group intersection'''
    raw = {'Client':"lambda x:'%s' == x.hostname and predicate(x)",
           'Group':"lambda x:'%s' in x.groups and predicate(x)"}
    nraw = {'Client':"lambda x:'%s' != x.hostname and predicate(x)",
            'Group':"lambda x:'%s' not in x.groups and predicate(x)"}
    containers = ['Group', 'Client']
    ignore = []
    
    def __init__(self, data, idict, parent=None):
        self.data = data
        self.contents = {}
        if parent == None:
            self.predicate = lambda x:True
        else:
            predicate = parent.predicate
            if data.get('negate', 'false') == 'true':
                psrc = self.nraw
            else:
                psrc = self.raw
            if data.tag in psrc.keys():
                self.predicate = eval(psrc[data.tag] % (data.get('name')),
                                      {'predicate':predicate})
            else:
                raise Exception
        mytype = self.__class__
        self.children = []
        for item in data.getchildren():
            if item.tag in self.ignore:
                continue
            elif item.tag in self.containers:
                self.children.append(mytype(item, idict, self))
            else:
                try:
                    self.contents[item.tag][item.get('name')] = item.attrib
                except KeyError:
                    self.contents[item.tag] = {item.get('name'):item.attrib}
                if item.text:
                    self.contents[item.tag]['__text__'] = item.text
                try:
                    idict[item.tag].append(item.get('name'))
                except KeyError:
                    idict[item.tag] = [item.get('name')]

    def Match(self, metadata, data):
        '''Return a dictionary of package mappings'''
        if self.predicate(metadata):
            for key in self.contents:
                try:
                    data[key].update(self.contents[key])
                except:
                    data[key] = {}
                    data[key].update(self.contents[key])
            for child in self.children:
                child.Match(metadata, data)

class XMLSrc(XMLFileBacked):
    '''XMLSrc files contain a LNode hierarchy that returns matching entries'''
    __node__ = INode

    def __init__(self, filename):
        XMLFileBacked.__init__(self, filename)
        self.items = {}
        self.cache = None
        self.pnode = None
        self.priority = -1

    def HandleEvent(self, _=None):
        '''Read file upon update'''
        try:
            data = file(self.name).read()
        except IOError:
            logger.error("Failed to read file %s" % (self.name))
            return
        self.items = {}
        try:
            xdata = lxml.etree.XML(data)
        except lxml.etree.XMLSyntaxError:
            logger.error("Failed to parse file %s" % (self.name))
            return
        self.pnode = self.__node__(xdata, self.items)
        self.cache = None
        try:
            self.priority = int(xdata.get('priority'))
        except (ValueError, TypeError):
            logger.error("Got bogus priority %s for file %s" % (xdata.get('priority'), self.name))
        del xdata, data

    def Cache(self, metadata):
        '''Build a package dict for a given host'''
        if self.cache == None or self.cache[0] != metadata:
            cache = (metadata, {})
            if self.pnode == None:
                logger.error("Cache method called early for %s; forcing data load" % (self.name))
                self.HandleEvent()
                return
            self.pnode.Match(metadata, cache[1])
            self.cache = cache

class XMLDirectoryBacked(DirectoryBacked):
    '''Directorybacked for *.xml'''
    patterns = re.compile('.*\.xml')    

class PrioDir(Plugin, XMLDirectoryBacked):
    '''This is a generator that handles package assignments'''
    __name__ = 'PrioDir'
    __child__ = XMLSrc

    def __init__(self, core, datastore):
        Plugin.__init__(self, core, datastore)
        try:
            XMLDirectoryBacked.__init__(self, self.data, self.core.fam)
        except OSError:
            self.logger.error("Failed to load %s indices" % (self.__name__))
            raise PluginInitError

    def HandleEvent(self, event):
        '''Handle events and update dispatch table'''
        XMLDirectoryBacked.HandleEvent(self, event)
        for src in self.entries.values():
            for itype, children in src.items.iteritems():
                for child in children:
                    try:
                        self.Entries[itype][child] = self.BindEntry
                    except KeyError:
                        self.Entries[itype] = {child: self.BindEntry}

    def BindEntry(self, entry, metadata):
        '''Check package lists of package entries'''
        [src.Cache(metadata) for src in self.entries.values()]
        name = entry.get('name')
        if not src.cache:
            self.logger.error("Called before data loaded")
            raise PluginExecutionError
        matching = [src for src in self.entries.values()
                    if src.cache and src.cache[1].has_key(entry.tag)
                    and src.cache[1][entry.tag].has_key(name)]
        if len(matching) == 0:
            raise PluginExecutionError
        elif len(matching) == 1:
            index = 0
        else:
            prio = [int(src.priority) for src in matching]
            if prio.count(max(prio)) > 1:
                self.logger.error("Found conflicting %s sources with same priority for %s, pkg %s" %
                                  (entry.tag.lower(), metadata.hostname, entry.get('name')))
                raise PluginExecutionError
            index = prio.index(max(prio))

        data = matching[index].cache[1][entry.tag][name]
        if data.has_key('__text__'):
            entry.text = data['__text__']
        if data.has_key('__children__'):
            [entry.append(copy.deepcopy(item)) for item in data['__children__']]
        [entry.attrib.__setitem__(key, data[key]) for key in data.keys() \
         if not key.startswith('__')]
