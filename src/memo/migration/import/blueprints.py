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

from plone.app.uuid.utils import uuidToObject


import logging


logger = logging.getLogger('Transmogrifier')


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

        if 'path-key' in options:
            pathkeys = options['path-key'].splitlines()
        else:
            pathkeys = defaultKeys(options['blueprint'], name, 'path')
        self.pathkey = Matcher(*pathkeys)

    def __iter__(self):
        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]

            # if you need to get the object (after the constructor part)
            obj = self.context.unrestrictedTraverse(
                safe_unicode(item['_path'].lstrip('/')).encode('utf-8'),
                None,
            )
            if not obj:
                yield item
                continue

            # do things here

            logger.info('[processing path] %s', pathkey)

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
        self.tableRestricts = options['tables']


    def __iter__(self):
        for item in self.previous:
            yield item

        with open(os.path.join(self.path, "upgrade_memo.json"), "r") as read_file:
          data = json.load(read_file)

       

        for table in data:
          if table['type'] == 'table' and table['name'] in self.tableRestricts:
            print(table['name'])
            for item in table['data']:
              yield item

@provider(ISectionBlueprint)
@implementer(ISection)
class InitStructureSource(object):

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.initStructure = (
                dict(_type='Folder', _path='/treatises',  title='Treatises', description='root'),
                dict(_type='libraries', _path='/treatises/libraries', title='Libraries'),
                dict(_type='authors', _path='/treatises/authors', title='Authors'),
                dict(_type='manuscripts', _path='/treatises/manuscripts', title='Manuscripts'),
                dict(_type='works', _path='/treatises/works', title='Works')
                )

    def __iter__(self):
        for item in self.previous:
            yield item

        for listitem in self.initStructure:
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

        self.referenceFieldname = options['referenceFieldname']
        self.sqlIdField = options['sqlIdField']

        self.catalog = api.portal.get_tool('portal_catalog')
        self.intids = component.getUtility(IIntIds)


    def __iter__(self):
        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]
            path = item[pathkey]


            obj = self.context.unrestrictedTraverse(
                safe_unicode(path).lstrip('/'), None)

            if not obj:
                yield item
                continue

            #import pdb; pdb.set_trace()

            if self.sqlIdField not in item:
                yield item
                continue

            if item[self.sqlIdField] is None:
                yield item
                continue   

            try:    
                linkedId = int(item[self.sqlIdField])
            except ValueError as ex:
                print('"%s" cannot be converted to an int: %s' % (item[self.sqlIdField], ex))
                yield item
                continue
            except TypeError as ext:
                print('"%s" cannot be converted to an int: %s' % (item[self.sqlIdField], ext))
                yield item
                continue       

            relObjBrain = self.catalog.unrestrictedSearchResults(sqlid=linkedId)[:1]
            

            if not relObjBrain:
                yield item
                continue

            relObj = relObjBrain[0].getObject()
            relObj_id = self.intids.getId(relObj)


            if relObj_id >= 0:
                setattr(obj, self.referenceFieldname, RelationValue(relObj_id))

            notify(ObjectModifiedEvent(obj))

            # always end with yielding the item,
            # unless you don't want it imported, or want
            # to bail on the rest of the pipeline
            yield item
