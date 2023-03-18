class ModelVersion:
    """ 
    Allows a model to be saved along with additional metadata.
    """

    _metatdata_items = [
        'model', 'model_number', 'data_number', 'model_description', 'features'
    ]

    def __init__(self, model, metadata: dict) -> None:
        self.model = model
        self.metadata = ModelVersion._validate_metadata(metadata)

    @staticmethod
    def _validate_metadata(metadata: dict) -> dict:
        """ 
        Ensures all required metadata items are included
        """

        for item in ModelVersion._metatdata_items:
            if item not in(metadata.keys()):
                raise Exception(f'{item} is a required metadata item')

        return metadata

    def _model_name(self) -> str:
        """ 
        Creates a unique model name that will be used to save the model.
        """

        model = self.metadata['model']
        data_number = self.metadata['data_number']
        model_number = self.metadata['model_number']
        
        return f'{model}_{data_number}_{model_number}'

    def pickle_obj(self, path: str, overwrite: bool=False) -> None:
        """
        Save the object as a pickle file.
        """

        filename = self._model_name()

        if overwrite == False:
            files = listdir(path)

            if filename in(files):
                print(f'{filename} already exists')

                return None

        # This will only run if overwrite is true or the file does not exist.
        dbfile = open(join(path, filename), 'wb')
        
        pickle.dump(self, dbfile)                     
        dbfile.close()