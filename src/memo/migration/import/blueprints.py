# -*- coding: utf-8 -*-
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from collective.transmogrifier.utils import defaultKeys
from collective.transmogrifier.utils import Matcher
from collective.transmogrifier.utils import resolvePackageReferenceOrFile
from Products.CMFPlone.utils import safe_unicode
from zope.interface import provider
from zope.interface import implementer
from plone import api
import os
import json
from zope.component.hooks import getSite
from zope import component
from zope.intid.interfaces import IIntIds
from zope.annotation import IAnnotations
from z3c.relationfield import RelationValue
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent import modified
from collective.relationhelpers import api as relapi
from plone.app.uuid.utils import uuidToObject
from DateTime import DateTime
from collective.transmogrifier.utils import defaultMatcher
from datetime import datetime
from collective.transmogrifier.utils import traverse
#from collective.transmogrifier.utils import resolvePackageReferenceOrFile
import transaction
from zope.schema import URI
import logging
import edtf
from zope.annotation.interfaces import IAnnotations
from zc.relation.interfaces import ICatalog

MYKEY = 'saw.memo.migration.blueprints'
logger = logging.getLogger(MYKEY)


@implementer(ISection)
@provider(ISectionBlueprint)
class Example(object):
    """An example blueprint.
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context


    def __iter__(self):
        for item in self.previous:
           

            # always end with yielding the item,
            # unless you don't want it imported, or want
            # to bail on the rest of the pipeline
            yield item


@provider(ISectionBlueprint)
@implementer(ISection)
class JSONSourceMemo(object):
    """
    """
    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context

        self.path = resolvePackageReferenceOrFile(options['path'])
        if self.path is None or not os.path.isdir(self.path):
            raise Exception('Path (' + str(self.path) + ') does not exists.')

        # self.datafield_prefix = options.get('datafield-prefix', DATAFIELD)
        if 'tables' in options:
            self.tableRestricts = options['tables'] 
        else:
            self.tableRestricts = None
        self.file = options['file'] or "upgrade_memo.json"


    def __iter__(self):
        transaction.commit()
        for item in self.previous:
            yield item

        #import pdb; pdb.set_trace()    
        with open(os.path.join(self.path, self.file), "r") as read_file:
          data = json.load(read_file)

        if self.tableRestricts:
            for table in data:
              if table['type'] == 'table' and table['name'] == self.tableRestricts:
                print(table['name'])
                for item in table['data']:
                  yield item
        else:
            for item in data:
                yield item          


@provider(ISectionBlueprint)
@implementer(ISection)
class Mapping(object):
    """
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous

        # language mappings
        languageDict = {
            'Dutch': ['d0e5387'],
            'Dutch (Ripuarian)': ['d0e5577'],      
            'French': ['d0e3388'],      
            'German': ['d0e9003'],      
            'Greek': ['d0e7766'],      
            'Italian': ['d0e7671'],      
            'Latin': ['d0e8051'],      
            'Portuguese': ['d0e7956'],
            'Latin and German': ['d0e8051', 'd0e9003'],
            'Latin and Italian': ['d0e8051', 'd0e7671']
        }
        self.storage = { 'language': languageDict}

        self.tax_name = options['tax_name']
        self.tax_field = options['tax_field']

    def __iter__(self):
        for item in self.previous:
            #import pdb; pdb.set_trace()
            if self.tax_field in item and self.tax_name in self.storage:
                mapping = self.storage[self.tax_name]
                key = item[self.tax_field]
                if key in mapping:
                   item[self.tax_field] =  mapping[key]

            yield item


@provider(ISectionBlueprint)
@implementer(ISection)
class InitStructureSource(object):

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.initStructure = (
                dict(_type='Folder', _path='/locations', title='Locations'),
                dict(_type='Folder', _path='/persons', title='Persons'),
                dict(_type='Folder', _path='/libraries', title='Libraries', description=''),
                dict(_type='Folder', _path='/rules', title='Rules', description=''),                
                dict(_type='project', _path='/treatises', title='Treatises', description=''),
                dict(_type='Folder', _path='/treatises/manuscripts', title='Manuscripts'),
                dict(_type='Folder', _path='/treatises/works', title='Works'),
                dict(_type='Folder', _path='/treatises/manuscript_works', title='Manuscript Works'),
                dict(_type='project', _path='/commentaries',title='Commentaries', description=''),
                dict(_type='Folder', _path='/commentaries/manuscripts', title='Manuscripts'),
                dict(_type='Folder', _path='/commentaries/works', title='Works'),
                dict(_type='Folder', _path='/commentaries/manuscript_works', title='Manuscript Works')
                )

    def __iter__(self):
        for item in self.previous:
            yield item

        for listitem in self.initStructure:
            yield listitem


@provider(ISectionBlueprint)
@implementer(ISection)
class DictSource(object):

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.dictionary = options['dictionary']

    def __iter__(self):
        for item in self.previous:
            yield item

        for listitem in self.dictionary:
            yield listitem


@provider(ISectionBlueprint)
@implementer(ISection)
class ReferenceUpdater(object):
    """
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        #self.context = transmogrifier.context
        self.context = transmogrifier.context if transmogrifier.context else getSite()

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)


        self.source_type = options['source_type']
        self.source_sqlIdField = options['source_sqlIdField']
        self.referenceFieldname = options['referenceFieldname']
        self.reference_type = options['reference_type']
        self.reference_sqlIdField = options['reference_sqlIdField']
        if 'sqlIdprefix' in options:
            self.sqlIdprefix = options['sqlIdprefix']
        else:
            self.sqlIdprefix = ''

        if 'annotation_key' in options:
            self.annotation_key = options['annotation_key']
            self.annotation_valuefield = options['annotation_valuefield']
            #self.annotation_value = options['annotation_value']
        else:
            self.annotation_key = None

        self.catalog = api.portal.get_tool('portal_catalog')
        self.intids = component.getUtility(IIntIds)

    def __iter__(self):
        for item in self.previous:
            sourceId = str(item[self.source_sqlIdField])
            referenceId = str(item[self.reference_sqlIdField])
            prefixed_sourceId = self.sqlIdprefix+sourceId

            srcObjBrain = self.catalog.unrestrictedSearchResults(sqlid=prefixed_sourceId, portal_type=self.source_type)[:1]
            
            if not srcObjBrain:
                logger.warning('Reference: Source {0} of type {1} not found'.format(prefixed_sourceId, self.source_type))
                yield item
                continue

            srcObj = srcObjBrain[0].getObject()

            prefixed_referenceId = self.sqlIdprefix+referenceId
            referenceObjBrain = self.catalog.unrestrictedSearchResults(sqlid=prefixed_referenceId, portal_type=self.reference_type)[:1]

            if not referenceObjBrain:
                logger.warning('Reference: Target {0} of type {1} not found, source is {2} of type {3}'.format(prefixed_referenceId, self.reference_type, srcObj.title, self.source_type))
                yield item
                continue

            referenceObj = referenceObjBrain[0].getObject()

            from_id = self.intids.getId(srcObj)
            to_id = self.intids.getId(referenceObj)
            from_attribute = self.referenceFieldname
            query = {
                'from_attribute': from_attribute,
                'from_id': from_id,
                'to_id': to_id,
            }

            existing_relations = getattr(srcObj, self.referenceFieldname, None)
            if existing_relations and isinstance(existing_relations, list):
                for relationvalue in existing_relations:
                    print(relationvalue.__dict__)
                for relationvalue in existing_relations:
                    if relationvalue.to_id == to_id:
                        existing_relations.remove(relationvalue)

                setattr(srcObj, self.referenceFieldname, existing_relations)
                modified(srcObj)

            transaction.commit()

            relapi.link_objects(
                    srcObj, referenceObj, self.referenceFieldname)

            transaction.commit()

            if self.annotation_key:
                relation_catalog = component.getUtility(ICatalog)
                relations = relation_catalog.findRelations(query)
                for relation in relations:
                    print(relation.__dict__)
                    annotations = IAnnotations(relation)
                    annotations[self.annotation_key] = item[self.annotation_valuefield]
                    #annotations[self.annotation_key] = self.annotation_value

            # always end with yielding the item,
            # unless you don't want it imported, or want
            # to bail on the rest of the pipeline
            yield item


@provider(ISectionBlueprint)
@implementer(ISection)
class AuthorExtender(object):

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        #self.context = transmogrifier.context
        self.context = transmogrifier.context if transmogrifier.context else getSite()

        filename = 'persons-corrected-20220126.json'
        with open(os.path.join('memoDBJson', filename), "r") as read_file:
            data = json.load(read_file, strict=False)
        self.mapping = data   

    def __iter__(self):
        #import pdb; pdb.set_trace()
        for item in self.previous:
            item_id = str(item['identifier'])
            mapping = list(filter(lambda x: x['OriginalId'] == item_id, self.mapping))
            if mapping:
                m = mapping[0]
                item['name'] = m["Name"]
                item['alias'] = m["alias"]
            yield item

        for item in self.mapping:
            if item["OriginalId"].startswith("n"):
                newitem = dict(name=item["Name"], alias=item["alias"], identifier=item["OriginalId"], type='n')
                yield newitem   


@provider(ISectionBlueprint)
@implementer(ISection)
class AuthorSkipper(object):

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        #self.context = transmogrifier.context
        self.context = transmogrifier.context if transmogrifier.context else getSite()

        filename = 'persons-corrected-20220126.json'
        with open(os.path.join('memoDBJson', filename), "r") as read_file:
            data = json.load(read_file, strict=False)
        self.mapping = data   

    def __iter__(self):
        #import pdb; pdb.set_trace()
        for item in self.previous:
            item_id = str(item['identifier'])
            mapping = list(filter(lambda x: x['OriginalId'] == item_id, self.mapping))
            if mapping:
                m = mapping[0]
                if m['CopyId'] or m['splitID']:
                    if m['alias'] and m['CopyId']:
                        print("{0} -c-> {1}: {2}".format(m['OriginalId'], m['CopyId'],  m['alias']))
                    if m['alias'] and m['splitID']:
                        print("{0} -s-> {1}: {2}".format(m['OriginalId'], m['splitID'],  m['alias']))
                    continue
            yield item 


@provider(ISectionBlueprint)
@implementer(ISection)
class LocationSkipper(object):

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        #self.context = transmogrifier.context
        self.context = transmogrifier.context if transmogrifier.context else getSite()

        filename = 'libs-corrected-20220328.json'
        with open(os.path.join('memoDBJson', filename), "r") as read_file:
            data = json.load(read_file, strict=False)
        allUsedLocations = list(filter(lambda x: not x['mapsTo'], data))
        self.mapping = set(map(lambda x: x['location'], allUsedLocations))

    def __iter__(self):
        #import pdb; pdb.set_trace()
        for item in self.previous:
            location = str(item['Name'])
            if not location in self.mapping:
                continue

            self.mapping.remove(location)    
            yield item

        # now add the remaining items from libs-corrected to the list of location
        for locationname in self.mapping:
            item = { "Name": locationname,
                    "Address": locationname,
                    "Longitude": None,
                    "Latitude": None,
                    "GettyID": None }

            logger.info('Added location from corrected libs: {0} '.format(locationname))        
            yield item      


@provider(ISectionBlueprint)
@implementer(ISection)
class LibraryRelator(object):


    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        #self.context = transmogrifier.context
        self.context = transmogrifier.context if transmogrifier.context else getSite()

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)


        self.source_type = options['source_type']
        self.source_sqlIdField = options['source_sqlIdField']
        self.referenceFieldname = options['referenceFieldname']
        self.reference_type = options['reference_type']
        self.reference_sqlIdField = options['reference_sqlIdField']
        if 'sqlIdprefix' in options:
            self.sqlIdprefix = options['sqlIdprefix']
        else:
            self.sqlIdprefix = ''

        if 'annotation_key' in options:
            self.annotation_key = options['annotation_key']
            self.annotation_valuefield = options['annotation_valuefield']
            #self.annotation_value = options['annotation_value']
        else:
            self.annotation_key = None

        self.catalog = api.portal.get_tool('portal_catalog')
        self.intids = component.getUtility(IIntIds)

        filename = 'libs-corrected-20220328.json'
        with open(os.path.join('memoDBJson', filename), "r") as read_file:
            data = json.load(read_file)
        self.mapping = data   

    def getMappedIds(self, requested_id, mapped_ids):
        mapping = list(filter(lambda x: x['identifier'] == requested_id, self.mapping))

        if mapping:
            # take first
            m = mapping[0]
            # requested_id is the mapped_id
            if m['mapsTo']:
               return m['mapsTo']
        return requested_id          

    def __iter__(self):

        for item in self.previous:
            sourceId = str(item[self.source_sqlIdField])
            referenceId = str(item[self.reference_sqlIdField])
            prefixed_sourceId = self.sqlIdprefix+sourceId

            srcObjBrain = self.catalog.unrestrictedSearchResults(sqlid=prefixed_sourceId, portal_type=self.source_type)[:1]
            
            if not srcObjBrain:
                logger.warning('Reference: Source {0} of type {1} not found'.format(prefixed_sourceId, self.source_type))
                yield item
                continue

            srcObj = srcObjBrain[0].getObject()

            prefixed_referenceId = self.sqlIdprefix+referenceId

            #if prefixed_referenceId == "t_3":
                #import pdb; pdb.set_trace()

            reference_Ids = self.getMappedIds(prefixed_referenceId, [])

            referenceObjBrain = self.catalog.unrestrictedSearchResults(sqlid=reference_Ids, portal_type=self.reference_type)

            if not referenceObjBrain:
                logger.warning('Reference: Target {0} of type {1} not found, source is {2} of type {3}'.format(prefixed_referenceId, self.reference_type, srcObj.title, self.source_type))
                yield item
                continue

            for brain in referenceObjBrain:    
                referenceObj = brain.getObject()

                from_id = self.intids.getId(srcObj)
                to_id = self.intids.getId(referenceObj)
                from_attribute = self.referenceFieldname
                query = {
                    'from_attribute': from_attribute,
                    'from_id': from_id,
                    'to_id': to_id,
                }

                existing_relations = getattr(srcObj, self.referenceFieldname, None)
                if existing_relations and isinstance(existing_relations, list):
                    # for relationvalue in existing_relations:
                    #     print(relationvalue.__dict__)
                    for relationvalue in existing_relations:
                        if relationvalue.to_id == to_id:
                            existing_relations.remove(relationvalue)

                    setattr(srcObj, self.referenceFieldname, existing_relations)
                    modified(srcObj)

                transaction.commit()

                relapi.link_objects(
                        srcObj, referenceObj, self.referenceFieldname)

                transaction.commit()

                if self.annotation_key:
                    relation_catalog = component.getUtility(ICatalog)
                    relations = relation_catalog.findRelations(query)
                    for relation in relations:
                        #print(relation.__dict__)
                        annotations = IAnnotations(relation)
                        annotations[self.annotation_key] = item[self.annotation_valuefield]


            # always end with yielding the item,
            # unless you don't want it imported, or want
            # to bail on the rest of the pipeline
            yield item


@provider(ISectionBlueprint)
@implementer(ISection)
class AuthorRelator(object):

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        #self.context = transmogrifier.context
        self.context = transmogrifier.context if transmogrifier.context else getSite()

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)


        self.source_type = options['source_type']
        self.source_sqlIdField = options['source_sqlIdField']
        self.referenceFieldname = options['referenceFieldname']
        self.reference_type = options['reference_type']
        self.reference_sqlIdField = options['reference_sqlIdField']
        if 'sqlIdprefix' in options:
            self.sqlIdprefix = options['sqlIdprefix']
        else:
            self.sqlIdprefix = ''

        if 'annotation_key' in options:
            self.annotation_key = options['annotation_key']
            self.annotation_valuefield = options['annotation_valuefield']
            #self.annotation_value = options['annotation_value']
        else:
            self.annotation_key = None

        self.catalog = api.portal.get_tool('portal_catalog')
        self.intids = component.getUtility(IIntIds)

        filename = 'persons-corrected-20220126.json'
        #filename = 'persons.json'
        with open(os.path.join('memoDBJson', filename), "r") as read_file:
            data = json.load(read_file)
        self.mapping = data   

    def getMappedIds(self, requested_id, mapped_ids):
        mapping = list(filter(lambda x: x['OriginalId'] == requested_id, self.mapping))

        if mapping:
            # take first
            m = mapping[0]
            # requested_id is the mapped_id
            if not m['CopyId'] and not m['splitID']:
               mapped_ids.append(requested_id) 
            elif m['CopyId']:
                #map this item to this id
                self.getMappedIds(m['CopyId'], mapped_ids)
            else:
                splitted = m['splitID'].split()
                for splitted_id in splitted:
                    self.getMappedIds(splitted_id, mapped_ids)  
        else:
            mapped_ids.append(requested_id)

        return mapped_ids          

    def __iter__(self):

        for item in self.previous:
            sourceId = str(item[self.source_sqlIdField])
            referenceId = str(item[self.reference_sqlIdField])
            prefixed_sourceId = self.sqlIdprefix+sourceId

            srcObjBrain = self.catalog.unrestrictedSearchResults(sqlid=prefixed_sourceId, portal_type=self.source_type)[:1]
            
            if not srcObjBrain:
                logger.warning('Reference: Source {0} of type {1} not found'.format(prefixed_sourceId, self.source_type))
                yield item
                continue

            srcObj = srcObjBrain[0].getObject()

            prefixed_referenceId = self.sqlIdprefix+referenceId

            #if prefixed_referenceId == "t_3":
                #import pdb; pdb.set_trace()

            reference_Ids = self.getMappedIds(prefixed_referenceId, [])

            referenceObjBrain = self.catalog.unrestrictedSearchResults(sqlid=reference_Ids, portal_type=self.reference_type)

            if not referenceObjBrain:
                logger.warning('Reference: Target {0} of type {1} not found, source is {2} of type {3}'.format(prefixed_referenceId, self.reference_type, srcObj.title, self.source_type))
                yield item
                continue

            for brain in referenceObjBrain:    
                referenceObj = brain.getObject()

                from_id = self.intids.getId(srcObj)
                to_id = self.intids.getId(referenceObj)
                from_attribute = self.referenceFieldname
                query = {
                    'from_attribute': from_attribute,
                    'from_id': from_id,
                    'to_id': to_id,
                }

                existing_relations = getattr(srcObj, self.referenceFieldname, None)
                if existing_relations and isinstance(existing_relations, list):
                    # for relationvalue in existing_relations:
                    #     print(relationvalue.__dict__)
                    for relationvalue in existing_relations:
                        if relationvalue.to_id == to_id:
                            existing_relations.remove(relationvalue)

                    setattr(srcObj, self.referenceFieldname, existing_relations)
                    modified(srcObj)

                transaction.commit()

                relapi.link_objects(
                        srcObj, referenceObj, self.referenceFieldname)

                transaction.commit()

                if self.annotation_key:
                    relation_catalog = component.getUtility(ICatalog)
                    relations = relation_catalog.findRelations(query)
                    for relation in relations:
                        #print(relation.__dict__)
                        annotations = IAnnotations(relation)
                        annotations[self.annotation_key] = item[self.annotation_valuefield]


            # always end with yielding the item,
            # unless you don't want it imported, or want
            # to bail on the rest of the pipeline
            yield item


@provider(ISectionBlueprint)
@implementer(ISection)
class SubtableLoader(object):
    """
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context
        self.file = options['file'] or "upgrade_memo.json"
        self.tableRestricts = options['tables']
        self.linkinField = options['linkinField']
        self.linkinFieldSub = options['linkinFieldSub'] if 'linkinFieldSub' in options else options['linkinField']
        self.targetField = options['targetField']
        self.valueField = options['valueField']
        self.path = resolvePackageReferenceOrFile(options['path'])
        if self.path is None or not os.path.isdir(self.path):
            raise Exception('Path (' + str(self.path) + ') does not exists.')


    def __iter__(self):

        for item in self.previous:
            

            if self.linkinField not in item:
                yield item
                continue

            with open(os.path.join(self.path, self.file), "r") as read_file:
                data = json.load(read_file)

            

            for table in data:
                if table['type'] == 'table' and table['name'] == self.tableRestricts:

                    l = []
                    for subitem in table['data']:
                        if self.linkinFieldSub in subitem:
                            if str(subitem[self.linkinFieldSub]) == str(item[self.linkinField]):
                                #import pdb; pdb.set_trace()
                                l.append(subitem[self.valueField])
                    if l:
                        item[self.targetField] = l


                     
                  
            yield item            


@provider(ISectionBlueprint)
@implementer(ISection)
class SubtableLinkLoader(object):
    """
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context
        self.file = options['file'] or "upgrade_memo.json"
        self.tableRestricts = options['tables']
        self.linkinField = options['linkinField']
        self.linkinFieldSub = options['linkinFieldSub'] if 'linkinFieldSub' in options else options['linkinField']
        self.targetField = options['targetField']
        self.path = resolvePackageReferenceOrFile(options['path'])
        if self.path is None or not os.path.isdir(self.path):
            raise Exception('Path (' + str(self.path) + ') does not exists.')

    def __iter__(self):

        for item in self.previous:
            

            if self.linkinField not in item:
                yield item
                continue

            with open(os.path.join(self.path, self.file), "r") as read_file:
                data = json.load(read_file)

            

            for table in data:
                if table['type'] == 'table' and table['name'] == self.tableRestricts:

                    l = []
                    for subitem in table['data']:
                        if self.linkinFieldSub in subitem:
                            if str(subitem[self.linkinFieldSub]) == str(item[self.linkinField]):
                                #import pdb; pdb.set_trace()
                                if subitem['link_url'] and subitem['link_url']!='':
                                    
                                    field = URI()
                                    try:
                                        field.fromUnicode(subitem['link_url'])
                                        entry = dict(_class='saw.memo.contenttypes.behaviour.literature.Link', text=subitem['link_title'], url=subitem['link_url'])
                                        l.append(entry)
                                    except:
                                        url = subitem['link_url']
                                        print('{0} is not a valid url'.format(url))
                                            
                    if l:
                        item[self.targetField] = l


                     
                  
            yield item      


@implementer(ISection)
@provider(ISectionBlueprint)
class UserCreator(object):
    """An blueprint to create Users.
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context

    def __iter__(self):
        for item in self.previous:

            email = item['email']
            username = item['username']
            
            if not email or not username:
                yield item
                continue

            password = item['password']
            firstname = item['first_name'] or ''
            lastname = item['last_name'] or ''
            fullname = item['fullname'] or (firstname + ' ' + lastname)
            company = item['company']
            prop = dict(fullname=fullname, location=company,)

            try:
                user = api.user.create(email=email, username=username, password=password, properties=prop)
                api.user.grant_roles(username=username,  roles=['Members'])
                transaction.commit()
            except ValueError as ex:
                print('"%s" cannot be created: %s' % (username, ex))
                yield item
                continue

            yield item


@implementer(ISection)
@provider(ISectionBlueprint)
class GrantRoles(object):
    """An blueprint to grant admin role to Users.
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context
        self.permissioncontext = options['permissioncontext']
        self.groupids = options['groupIdsField']

    def __iter__(self):
        for item in self.previous:

            username = item['username']
            
            if not username:
                yield item
                continue

            container = api.content.get(path=self.permissioncontext)

            for group in item[self.groupids]:
                # import pdb; pdb.set_trace()
                if group == 1 or group == '1':
                    print('"%s" has group admin for: %s' % (username, self.permissioncontext))
                    api.user.grant_roles(username=username,  roles=['Manager'], obj= container)
                    transaction.commit()
           
            yield item            


@provider(ISectionBlueprint)
@implementer(ISection)
class DatesUpdater(object):
    """Sets creation and modification dates on objects.
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.creationkey = options.get('creation-key', 'creation_date')
        self.modificationkey = options.get('modification-key', 'modification_date')  # noqa
        self.effectivekey = options.get('effective-key', 'effective_date')
        self.expirationkey = options.get('expiration-key', 'expiration_date')

    def __iter__(self):

        #import pdb; pdb.set_trace()
        for item in self.previous:
            pathkey = self.pathkey(*list(item.keys()))[0]
            if not pathkey:  # not enough info
                yield item
                continue
            path = item[pathkey]

            ob = traverse(self.context, str(path).lstrip('/'), None)
            if ob is None:
                yield item
                continue  # object not found

            creationdate = item.get(self.creationkey, None)
            if creationdate and hasattr(ob, 'creation_date'):
                ob.creation_date = datetime.fromtimestamp(int(creationdate))

            modificationdate = item.get(self.modificationkey, None)
            if modificationdate and hasattr(ob, 'modification_date'):
                ob.modification_date = datetime.fromtimestamp(int(modificationdate))

            effectivedate = item.get(self.effectivekey, None)
            if effectivedate and hasattr(ob, 'effective_date'):
                ob.effective_date = datetime.fromtimestamp(int(effectivedate))

            expirationdate = item.get(self.expirationkey, None)
            if expirationdate and hasattr(ob, 'expiration_date'):
                ob.expiration_date = datetime.fromtimestamp(int(expirationdate))

            yield item


@provider(ISectionBlueprint)
@implementer(ISection)
class UserMapper(object):
    """Sets creation and modification dates on objects.
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context
        self.file = options['file'] or "upgrade_memo.json"
        self.path = resolvePackageReferenceOrFile(options['path'])
        if self.path is None or not os.path.isdir(self.path):
            raise Exception('Path (' + str(self.path) + ') does not exists.')
        with open(os.path.join(self.path, self.file), "r") as read_file:
            data = json.load(read_file, strict=False)
        self.mapping = data   

    def __iter__(self):

        #import pdb; pdb.set_trace()

        for item in self.previous:
            if 'creator' in item and item['creator']:
                mapping = list(filter(lambda x: x['fullname'] == item['creator'], self.mapping))
                if mapping:
                    item['creators'] = mapping[0]['username']
                else:
                    item['creators'] = item['creator']
                    
            yield item


@provider(ISectionBlueprint)
@implementer(ISection)
class MergeSubTable(object):
    """
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context
        self.file = options['file'] or "upgrade_memo.json"
        if 'tables' in options:
            self.tableRestricts = options['tables'] 
        else:
            self.tableRestricts = None
        self.linkinField = options['linkinField']
        self.linkinFieldSub = options['linkinFieldSub'] if 'linkinFieldSub' in options else options['linkinField']
        self.targetField = options['targetField']
        self.valueField = options['valueField']
        self.path = resolvePackageReferenceOrFile(options['path'])
        if self.path is None or not os.path.isdir(self.path):
            raise Exception('Path (' + str(self.path) + ') does not exists.')

    def __iter__(self):
        for item in self.previous:

            if self.linkinField not in item:
                yield item
                continue

            with open(os.path.join(self.path, self.file), "r") as read_file:
                data = json.load(read_file)

            if self.tableRestricts:
                for table in data:
                  if table['type'] == 'table' and table['name'] == self.tableRestricts:
                    print(table['name'])
                    for subitem in table['data']:
                        if str(subitem[self.linkinFieldSub]) == str(item[self.linkinField]):
                            item[self.targetField] = subitem[self.valueField]
            else:
                for subitem in data:
                    if str(subitem[self.linkinFieldSub]) == str(item[self.linkinField]):
                            #import pdb; pdb.set_trace()
                            item[self.targetField] = subitem[self.valueField]
                    
            yield item        


@provider(ISectionBlueprint)
@implementer(ISection)
class EdtfConverter(object):
    """
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context

    def __iter__(self):
        #import pdb; pdb.set_trace()
        for item in self.previous:  
            value_from = None 
            value_to = None
            if 'date_from' in item and item['date_from']:
                try:
                    #value_from = DateTime(item['date_from'].zfill(4)).asdatetime().date()
                    value_from = item['date_from'].zfill(4)
                except:
                    value_from = None    
            if 'date_to' in item and item['date_to'] :
                try:
                    #value_to = DateTime(item['date_to'].zfill(4)).asdatetime().date()
                    value_to = item['date_to'].zfill(4)
                except:
                    value_to = None   
            if value_from and value_to:         
                calc_edtf_date = u'{0}/{1}'.format(
                        value_from,
                        value_to
                        )
                try:
                    edtf.parse_edtf(calc_edtf_date)
                    item['edtf_date'] = calc_edtf_date 
                    del item['date_from']                 
                    del item['date_to']                 
                except:
                    print("date value converting failed: " + calc_edtf_date)

            yield item        


@provider(ISectionBlueprint)
@implementer(ISection)
class GeolocationConverter(object):
    """
    """

    def __init__(self, transmogrifier, name, options, previous):
        self.transmogrifier = transmogrifier
        self.name = name
        self.options = options
        self.previous = previous
        self.context = transmogrifier.context

    def __iter__(self):

        for item in self.previous:

            if 'Longitude' in item and item['Longitude'] and 'Latitude' in item and item['Latitude']:
                longitude = str(item['Longitude'])
                latitude = str(item['Latitude'])
                geolocation = dict(_class='plone.formwidget.geolocation.geolocation.Geolocation', longitude=longitude, latitude=latitude)
                item['geolocation'] = geolocation
            
            yield item 
