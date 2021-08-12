# -*- coding: utf-8 -*-
from DateTime import DateTime
from datetime import datetime
from plone.app.textfield.interfaces import IRichText
from plone.app.textfield.value import RichTextValue
from plone.namedfile.interfaces import INamedField
from plone.supermodel.interfaces import IToUnicode
from Products.CMFPlone.utils import safe_unicode
from six import string_types
from transmogrify.dexterity.interfaces import IDeserializer
from transmogrify.dexterity.interfaces import ISerializer
from zope.component import adapter
from zope.component import queryUtility
from zope.dottedname.resolve import resolve
from zope.interface import implementer
from zope.schema.interfaces import IDate
from zope.schema.interfaces import IField
from Products.CMFPlone.utils import safe_unicode
from zope.schema.interfaces import IFromUnicode

@implementer(IDeserializer)
@adapter(IDate)
class DateDeserializer(object):

    def __init__(self, field):
        self.field = field

    def __call__(self, value, filestore, item,
                 disable_constraints=False, logger=None):
        if isinstance(value, string_types):
            if value in ('', 'None'):
                value = None
            else:
                try:
                    value = DateTime(value.zfill(4)).asdatetime().date()
                except:
                    value = None    
        if isinstance(value, datetime):
            value = value.date()
        try:
            self.field.validate(value)
        except Exception as e:
            if not disable_constraints:
                raise e
            else:
                if logger:
                    logger(
                        "DateDeserializer: %s is invalid in %s: %s" % (
                            self.field.__name__,
                            item['_path'],
                            e)
                    )
        return value


@implementer(IDeserializer)
@adapter(IField)
class DefaultDeserializer(object):

    def __init__(self, field):
        self.field = field

    def __call__(self, value, filestore, item,
                 disable_constraints=False, logger=None):
        field = self.field
        if field is not None:
            try:
                if isinstance(value, str):
                    value = safe_unicode(value.strip())
                if str(type(value)) == "<type 'unicode'>":
                    value = IFromUnicode(field).fromUnicode(value.strip())
                self.field.validate(value)
            except Exception as e:
                if not disable_constraints:
                    raise e
                else:
                    if logger:
                        logger(
                            "DefaultDeserializer: %s is invalid in %s: %s" % (
                                self.field.__name__,
                                item['_path'],
                                e.__repr__())
                        )
        return value