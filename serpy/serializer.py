from serpy.fields import Field
import operator
import six


class SerializerBase(Field):
    _field_map = {}


def _compile_field_to_tuple(field, name, serializer_cls):
    """"Compiles a field into a tuple for use in the serializer's fields list."
    Parameters:
        - field (Field): The field to be compiled.
        - name (str): The name of the field.
        - serializer_cls (Serializer): The serializer class being used.
    Returns:
        - tuple: A tuple containing the compiled field's name, getter function, to_value function (if overridden), call flag, required flag, and getter_takes_serializer flag.
    Processing Logic:
        - Sets a default getter function if none is provided.
        - Sets the field name to a supplied label or defaults to the attribute name."""
    
    if (getter := field.as_getter(name, serializer_cls)) is None:
        getter = serializer_cls.default_getter(field.attr or name)

    # Only set a to_value function if it has been overridden for performance.
    to_value = None
    if field._is_to_value_overridden():
        to_value = field.to_value

    # Set the field name to a supplied label; defaults to the attribute name.
    name = field.label or name

    return (name, getter, to_value, field.call, field.required,
            field.getter_takes_serializer)


class SerializerMeta(type):

    @staticmethod
    def _get_fields(direct_fields, serializer_cls):
        """Get all fields from base classes and direct fields.
        Parameters:
            - direct_fields (dict): Dictionary of direct fields.
            - serializer_cls (class): Serializer class.
        Returns:
            - field_map (dict): Dictionary of all fields.
        Processing Logic:
            - Get fields from base classes.
            - Update field map with direct fields.
            - Return field map."""
        
        field_map = {}
        # Get all the fields from base classes.
        for cls in serializer_cls.__mro__[::-1]:
            if issubclass(cls, SerializerBase):
                field_map.update(cls._field_map)
        field_map.update(direct_fields)
        return field_map

    @staticmethod
    def _compile_fields(field_map, serializer_cls):
        """Compiles a list of field tuples from a field map and a serializer class.
        Parameters:
            - field_map (dict): A dictionary mapping field names to field objects.
            - serializer_cls (class): The serializer class used to serialize the fields.
        Returns:
            - list: A list of field tuples, where each tuple contains the field object and its name.
        Processing Logic:
            - Maps field names to field objects.
            - Uses a serializer class to serialize fields.
            - Returns a list of tuples with field objects and names."""
        
        return [
            _compile_field_to_tuple(field, name, serializer_cls)
            for name, field in field_map.items()
        ]

    def __new__(cls, name, bases, attrs):
        """"""
        
        # Fields declared directly on the class.
        direct_fields = {}

        # Take all the Fields from the attributes.
        for attr_name, field in attrs.items():
            if isinstance(field, Field):
                direct_fields[attr_name] = field
        for k in direct_fields.keys():
            del attrs[k]

        real_cls = super(SerializerMeta, cls).__new__(cls, name, bases, attrs)

        field_map = cls._get_fields(direct_fields, real_cls)
        compiled_fields = cls._compile_fields(field_map, real_cls)

        real_cls._field_map = field_map
        real_cls._compiled_fields = tuple(compiled_fields)
        return real_cls


class Serializer(six.with_metaclass(SerializerMeta, SerializerBase)):
    """:class:`Serializer` is used as a base for custom serializers.

    The :class:`Serializer` class is also a subclass of :class:`Field`, and can
    be used as a :class:`Field` to create nested schemas. A serializer is
    defined by subclassing :class:`Serializer` and adding each :class:`Field`
    as a class variable:

    Example: ::

        class FooSerializer(Serializer):
            foo = Field()
            bar = Field()

        foo = Foo(foo='hello', bar=5)
        FooSerializer(foo).data
        # {'foo': 'hello', 'bar': 5}

    :param instance: The object or objects to serialize.
    :param bool many: If ``instance`` is a collection of objects, set ``many``
        to ``True`` to serialize to a list.
    :param context: Currently unused parameter for compatability with Django
        REST Framework serializers.
    """
    #: The default getter used if :meth:`Field.as_getter` returns None.
    default_getter = operator.attrgetter

    def __init__(self, instance=None, many=False, data=None, context=None,
                 **kwargs):
        """"""
        
        if data is not None:
            raise RuntimeError(
                'serpy serializers do not support input validation')

        super(Serializer, self).__init__(**kwargs)
        self.instance = instance
        self.many = many
        self._data = None

    def _serialize(self, instance, fields):
        """Serializes an instance of a class into a dictionary, using the provided fields.
        Parameters:
            - instance (object): The instance of the class to be serialized.
            - fields (list): A list of tuples containing information about the fields to be serialized. Each tuple should contain the field name, a getter function, a function to convert the value, a boolean indicating if the getter function needs to be called, a boolean indicating if the field is required, and a boolean indicating if the getter function needs to be passed the instance as an argument.
        Returns:
            - dict: A dictionary containing the serialized data.
        Processing Logic:
            - Loops through the provided fields and uses the getter function to retrieve the value from the instance.
            - If the getter function fails to retrieve the value and the field is not required, the loop continues to the next field.
            - If the getter function succeeds or the field is required, the value is converted using the provided function and added to the dictionary.
            - The dictionary is then returned."""
        
        v = {}
        for name, getter, to_value, call, required, pass_self in fields:
            if pass_self:
                result = getter(self, instance)
            else:
                try:
                    result = getter(instance)
                except (KeyError, AttributeError):
                    if required:
                        raise
                    else:
                        continue
                if required or result is not None:
                    if call:
                        result = result()
                    if to_value:
                        result = to_value(result)
            v[name] = result

        return v

    def to_value(self, instance):
        """"""
        
        fields = self._compiled_fields
        if self.many:
            serialize = self._serialize
            return [serialize(o, fields) for o in instance]
        return self._serialize(instance, fields)

    @property
    def data(self):
        """Get the serialized data from the :class:`Serializer`.

        The data will be cached for future accesses.
        """
        # Cache the data for next time .data is called.
        if self._data is None:
            self._data = self.to_value(self.instance)
        return self._data


class DictSerializer(Serializer):
    """:class:`DictSerializer` serializes python ``dicts`` instead of objects.

    Instead of the serializer's fields fetching data using
    ``operator.attrgetter``, :class:`DictSerializer` uses
    ``operator.itemgetter``.

    Example: ::

        class FooSerializer(DictSerializer):
            foo = IntField()
            bar = FloatField()

        foo = {'foo': '5', 'bar': '2.2'}
        FooSerializer(foo).data
        # {'foo': 5, 'bar': 2.2}
    """
    default_getter = operator.itemgetter
