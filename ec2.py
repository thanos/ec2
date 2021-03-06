from __future__ import with_statement

import os
import re
import boto.ec2

__author__ = 'Matt Robenolt <matt@ydekproductions.com>'
__version__ = '0.1.0'
__license__ = 'BSD'
__all__ = ('credentials', 'instances')


class credentials(object):
    """
    Simple credentials singleton that holds our fun AWS info
    and masquerades as a dict
    """
    ACCESS_KEY_ID = None
    SECRET_ACCESS_KEY = None
    REGION_NAME = 'us-east-1'

    def keys(self):
        return ['aws_access_key_id', 'aws_secret_access_key', 'region_name']

    def __getitem__(self, item):
        item = item.upper()
        return os.environ.get(item) or getattr(self, item, None) or getattr(self, item[4:])

    @classmethod
    def from_file(cls, filename):
        """
        Load ACCESS_KEY_ID and SECRET_ACCESS_KEY from csv
        generated by Amazon's IAM.

        >>> ec2.credentials.from_file('credentials.csv')
        """
        import csv
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            row = reader.next()  # Only one row in the file
        try:
            cls.ACCESS_KEY_ID = row['Access Key Id']
            cls.SECRET_ACCESS_KEY = row['Secret Access Key']
        except KeyError:
            raise IOError('Invalid credentials format')


class instances(object):
    """Singleten to stem off queries for instances"""

    @classmethod
    def _connect(cls):
        return boto.ec2.connect_to_region(**credentials())

    @classmethod
    def all(cls):
        """
        Grab all AWS instances and cache them for future filters

        >>> ec2.instances.all()
        [ ... ]
        """
        if not hasattr(cls, '_instances'):
            conn = cls._connect()
            # Ugh
            cls._instances = [i for r in conn.get_all_instances() for i in r.instances]
        return cls._instances

    @classmethod
    def filter(cls, **kwargs):
        """
        The meat. Filter instances using Django model style syntax.

        All kwargs are translated into attributes on instance objects.
        If the attribute is not found, it looks for a similar key
        in the tags.

        There are a couple comparisons to check against as well:
            exact: check strict equality
            iexact: case insensitive exact
            like: check against regular expression
            ilike: case insensitive like
            contains: check if string is found with attribute
            icontains: case insensitive contains
            startswith: check if attribute value starts with the string
            istartswith: case insensitive startswith
            endswith: check if attribute value ends with the string
            iendswith: case insensitive startswith

        >>> ec2.instances.filter(state='running', name__startswith='production')
        [ ... ]
        """
        instances = cls.all()
        for key in kwargs:
            instances = filter(lambda i: _comp(key, kwargs[key], i), instances)
        return instances

    @classmethod
    def clear(cls):
        "Clear the cached instances"
        try:
            del cls._instances
        except AttributeError:
            pass


# Yonder lies all the crap for filtering instances

def _comp(key, value, instance):
    "Map a key name to a specific comparison function"
    if '__' not in key:
        # If no __ exists, default to doing an "exact" comparison
        key, comp = key, 'exact'
    else:
        key, comp = key.rsplit('__', 1)
    # Check if comp is valid
    if hasattr(_Compare, comp):
        return getattr(_Compare, comp)(key, value, instance)
    raise AttributeError("No comparison '%s'" % comp)


class _Compare(object):
    "Private class, namespacing comparison functions."

    @staticmethod
    def exact(key, value, instance):
        try:
            return getattr(instance, key) == value
        except AttributeError, e:
            # Fall back to checking tags
            for tag in instance.tags:
                if key == tag.lower():
                    return instance.tags[tag] == value
            # There is no tag found either
            raise e

    @staticmethod
    def iexact(key, value, instance):
        value = value.lower()
        try:
            return getattr(instance, key).lower() == value
        except AttributeError, e:
            # Fall back to checking tags
            for tag in instance.tags:
                if key == tag.lower():
                    return instance.tags[tag].lower() == value
            # There is no tag found either
            raise e

    @staticmethod
    def like(key, value, instance):
        if isinstance(value, basestring):
            # If a string is passed in, we want to convert it to a pattern object
            value = re.compile(value)
        try:
            return bool(value.match(getattr(instance, key)))
        except AttributeError, e:
            # Fall back to checking tags
            for tag in instance.tags:
                if key == tag.lower():
                    return bool(value.match(instance.tags[tag]))
            # There is no tag found either
            raise e
    # Django alias
    regex = like

    @staticmethod
    def ilike(key, value, instance):
        return _Compare.like(key, re.compile(value, re.I), instance)
    # Django alias
    iregex = ilike

    @staticmethod
    def contains(key, value, instance):
        try:
            return value in getattr(instance, key)
        except AttributeError, e:
            # Fall back to checking tags
            for tag in instance.tags:
                if key == tag.lower():
                    return value in instance.tags[tag]
            # There is no tag found either
            raise e

    @staticmethod
    def icontains(key, value, instance):
        value = value.lower()
        try:
            return value in getattr(instance, key).lower()
        except AttributeError, e:
            # Fall back to checking tags
            for tag in instance.tags:
                if key == tag.lower():
                    return value in instance.tags[tag]
            # There is no tag found either
            raise e

    @staticmethod
    def startswith(key, value, instance):
        try:
            return getattr(instance, key).startswith(value)
        except AttributeError, e:
            # Fall back to checking tags
            for tag in instance.tags:
                if key == tag.lower():
                    return instance.tags[tag].startswith(value)
            # There is no tag found either
            raise e

    @staticmethod
    def istartswith(key, value, instance):
        value = value.lower()
        try:
            return getattr(instance, key).startswith(value)
        except AttributeError, e:
            # Fall back to checking tags
            for tag in instance.tags:
                if key == tag.lower():
                    return instance.tags[tag].lower().startswith(value)
            # There is no tag found either
            raise e

    @staticmethod
    def endswith(key, value, instance):
        try:
            return getattr(instance, key).endswith(value)
        except AttributeError, e:
            # Fall back to checking tags
            for tag in instance.tags:
                if key == tag.lower():
                    return instance.tags[tag].endswith(value)
            # There is no tag found either
            raise e

    @staticmethod
    def iendswith(key, value, instance):
        value = value.lower()
        try:
            return getattr(instance, key).endswith(value)
        except AttributeError, e:
            # Fall back to checking tags
            for tag in instance.tags:
                if key == tag.lower():
                    return instance.tags[tag].lower().endswith(value)
            # There is no tag found either
            raise e
