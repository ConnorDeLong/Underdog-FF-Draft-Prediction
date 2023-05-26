class SaveSessionState:
    """
    Base class which allows any class inheriting it to set and receive its
    attributes to/from st.session_state
    """

    def __init__(self, session_state=None):
        self.session_state = session_state

    def __repr__(self):
        return self.__class__.__name__

    def __setattr__(self, name: str, value, initialize_session_state=False) -> None:
        """
        If initialize_session_state is True or the attribute exists in session_state,
        the attribute value in session_state is overwritten.

        Parameters
        ----------
        name : str
            Name of attribute
        value : _type_
            Value of attribute
        initialize_session_state : bool, optional
            Indicates if the attribute should be initialized in session_state, by default False
        """
        super().__setattr__(name, value)

        if self.session_state is not None and name != "session_state":
            s_name = self._get_session_state_name(name)

            if initialize_session_state:
                self.session_state[s_name] = value
            elif s_name in self.session_state:
                self.session_state[s_name] = value

    def __getattribute__(self, name: str):
        """
        Retrives the value of the attribute from session_state if the attr
        exists there. Otherwise, the values is pulled from the object instance.

        Parameters
        ----------
        name : str
            Attribute name

        Returns
        -------
        Any
            Value of attribute
        """

        _tmp = super().__getattribute__("__class__")
        class_name = object.__getattribute__(_tmp, "__name__")

        s_name = f"{class_name}_{name}"
        if super().__getattribute__("session_state") is not None:
            if s_name in super().__getattribute__("session_state"):
                return self.session_state[s_name]
            else:
                return super().__getattribute__(name)
        else:
            return super().__getattribute__(name)

    def initialize_session_state(self, name: str, value) -> None:
        """
        Sets the value in session_state if the name does not already exist.
        This is required in __init__ in order for the attribute to be tracked
        in session_state.

        Parameters
        ----------
        name : str
            Attribute name
        value : Any
            Attribute value
        """
        if self.session_state is not None:
            s_name = self._get_session_state_name(name)
            if s_name not in self.session_state:
                self.__setattr__(name, value, initialize_session_state=True)
        else:
            self.__setattr__(name, value, initialize_session_state=False)

    def _get_session_state_name(self, name: str) -> str:
        """
        Creates the name used to store the attributes value in session_state.
        This prefixes the name of the attribute with the class so that multiple
        classes can use the same attribute name.

        NOTE: This does NOT support multiple instances of the same class as
        these values will be overwritten.
        """
        return f"{str(self)}_{name}"
