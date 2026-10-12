"""Errores compartidos del núcleo; los adaptadores traducen sus excepciones."""
class StorageError(Exception):
    pass

class NotFound(Exception):
    pass

class PermissionDenied(Exception):
    pass

class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('Comprueba los campos indicados.')

class Duplicate(Exception):
    def __init__(self, record, mismatch):
        self.record, self.mismatch = record, mismatch

class PossibleRevision(Exception):
    def __init__(self, candidates):
        self.candidates = candidates
