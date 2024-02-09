import six
import types


class Field(object):
    """:class:`Field` is used to define what attributes will be serialized.

    A :class:`Field` maps a property or function on an object to a value in the
    serialized result. Subclass this to make custom fields. For most simple
    cases, overriding :meth:`Field.to_value` should give enough flexibility. If
    more control is needed, override :meth:`Field.as_getter`.

    :param str attr: The attribute to get on the object, using the same format
        as ``operator.attrgetter``. If this is not supplied, the name this
        field was assigned to on the serializer will be used.
    :param bool call: Whether the value should be called after it is retrieved
        from the object. Useful if an object has a method to be serialized.
    :param str label: A label to use as the name of the serialized field
        instead of using the attribute name of the field.
    :param bool required: Whether the field is required. If set to ``False``,
        :meth:`Field.to_value` will not be called if the value is ``None``.
    """
    #: Set to ``True`` if the value function returned from
    #: :meth:`Field.as_getter` requires the serializer to be passed in as the
    #: first argument. Otherwise, the object will be the only parameter.
    getter_takes_serializer = False

    def __init__(self, attr=None, call=False, label=None, required=True):
        """"Initializes an instance of the class with the given attributes and settings.
        Parameters:
            - attr (any, optional): Attribute to be assigned to the instance. Defaults to None.
            - call (bool, optional): Indicates whether the instance is callable. Defaults to False.
            - label (str, optional): Label to be assigned to the instance. Defaults to None.
            - required (bool, optional): Indicates whether the instance is required. Defaults to True.
        Returns:
            - None: This function does not return any value.
        Processing Logic:
            - Assigns the given attribute to the instance.
            - Sets the instance to be callable or not based on the call parameter.
            - Assigns the given label to the instance.
            - Sets the instance to be required or not based on the required parameter.""""
        
        self.attr = attr
        self.call = call
        self.label = label
        self.required = required

    def to_value(self, value):
        """Transform the serialized value.

        Override this method to clean and validate values serialized by this
        field. For example to implement an ``int`` field: ::

            def to_value(self, value):
                return int(value)

        :param value: The value fetched from the object being serialized.
        """
        return value
    to_value._serpy_base_implementation = True

    def _is_to_value_overridden(self):
        """Check if the to_value method has been overridden.
        Parameters:
            - self (object): The current object.
        Returns:
            - bool: True if the to_value method has been overridden, False otherwise.
        Processing Logic:
            - Get the to_value method from the current object.
            - If to_value is not a method, it must have been overridden.
            - Return True if to_value has been overridden, False otherwise."""
        
        to_value = self.to_value
        # If to_value isn't a method, it must have been overridden.
        if not isinstance(to_value, types.MethodType):
            return True
        return not getattr(to_value, '_serpy_base_implementation', False)

    def as_getter(self, serializer_field_name, serializer_cls):
        """Returns a function that fetches an attribute from an object.

        Return ``None`` to use the default getter for the serializer defined in
        :attr:`Serializer.default_getter`.

        When a :class:`Serializer` is defined, each :class:`Field` will be
        converted into a getter function using this method. During
        serialization, each getter will be called with the object being
        serialized, and the return value will be passed through
        :meth:`Field.to_value`.

        If a :class:`Field` has ``getter_takes_serializer = True``, then the
        getter returned from this method will be called with the
        :class:`Serializer` instance as the first argument, and the object
        being serialized as the second.

        :param str serializer_field_name: The name this field was assigned to
            on the serializer.
        :param serializer_cls: The :class:`Serializer` this field is a part of.
        """
        return None


class StrField(Field):
    """A :class:`Field` that converts the value to a string."""
    to_value = staticmethod(six.text_type)


class IntField(Field):
    """A :class:`Field` that converts the value to an integer."""
    to_value = staticmethod(int)


class FloatField(Field):
    """A :class:`Field` that converts the value to a float."""
    to_value = staticmethod(float)


class BoolField(Field):
    """A :class:`Field` that converts the value to a boolean."""
    to_value = staticmethod(bool)


class MethodField(Field):
    """A :class:`Field` that calls a method on the :class:`Serializer`.

    This is useful if a :class:`Field` needs to serialize a value that may come
    from multiple attributes on an object. For example: ::

        class FooSerializer(Serializer):
            plus = MethodField()
            minus = MethodField('do_minus')

            def get_plus(self, foo_obj):
                return foo_obj.bar + foo_obj.baz

            def do_minus(self, foo_obj):
                return foo_obj.bar - foo_obj.baz

        foo = Foo(bar=5, baz=10)
        FooSerializer(foo).data
        # {'plus': 15, 'minus': -5}

    :param str method: The method on the serializer to call. Defaults to
        ``'get_<field name>'``.
    """
    getter_takes_serializer = True

    def __init__(self, method=None, **kwargs):
        """"""
        
        super(MethodField, self).__init__(**kwargs)
        self.method = method

    def as_getter(self, serializer_field_name, serializer_cls):
        """Returns the getter method of a serializer class for a specific field.
        Parameters:
            - serializer_field_name (str): The name of the field to get the getter method for.
            - serializer_cls (class): The serializer class to get the getter method from.
        Returns:
            - method (function): The getter method for the specified field.
        Processing Logic:
            - Gets the method name based on the serializer field name.
            - Returns the method from the serializer class."""
        
        if (method_name := self.method) is None:
            method_name = 'get_{0}'.format(serializer_field_name)
        return getattr(serializer_cls, method_name)
