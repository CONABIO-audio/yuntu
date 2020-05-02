"""Feature class module."""
from abc import abstractmethod
import os

import numpy as np
import yuntu.core.audio.audio as audio_module
from yuntu.core.media.base import Media
from yuntu.core.media.time import TimeMediaMixin
from yuntu.core.media.frequency import FrequencyMediaMixin
from yuntu.core.media.time_frequency import TimeFrequencyMediaMixin


# pylint: disable=abstract-method
class Feature(Media):
    """Feature base class.

    This is the base class for all audio features. A feature contains
    information extracted from the audio data.
    """

    def __init__(
            self,
            audio=None,
            array=None,
            path: str = None,
            lazy: bool = False,
            **kwargs):
        """Construct a feature."""
        if audio is not None and not isinstance(audio, audio_module.Audio):
            audio = audio_module.Audio.from_dict(audio)

        self.audio = audio
        super().__init__(path=path, lazy=lazy, array=array, **kwargs)

    def _copy_dict(self, **kwargs):
        return {
            'audio': self.audio,
            **super()._copy_dict(**kwargs),
        }

    def to_dict(self):
        data = super().to_dict()

        if self.has_audio():
            data['audio'] = self.audio.to_dict()

        return data

    def has_audio(self):
        """Return if this feature is linked to an Audio instance."""
        if not hasattr(self, 'audio'):
            return False

        return self.audio is not None

    def plot(self, ax=None, **kwargs):
        ax = super().plot(ax=ax, **kwargs)

        if kwargs.get('audio', False):
            audio_kwargs = kwargs.get('audio_kwargs', {})
            self.audio.plot(ax=ax, **audio_kwargs)

        return ax

    def load_from_path(self, path=None):
        if path is None:
            path = self.path

        extension = os.path.splitext(path)[1]
        if extension == 'npy':
            try:
                return np.load(self.path)
            except IOError:
                message = (
                    'The provided path for this feature object could '
                    f'not be read. (path={self.path})')
                raise ValueError(message)

        if extension == 'npz':
            try:
                with np.load(self.path) as data:
                    return data[type(self).__name__]
            except IOError:
                message = (
                    'The provided path for this feature object could '
                    f'not be read. (path={self.path})')
                raise ValueError(message)

        message = (
            'The provided path does not have a numpy file extension. '
            f'(extension={extension})')
        raise ValueError(message)

    @abstractmethod
    def compute(self):
        pass

    def load(self, path=None):
        if not self.has_audio():
            if not self.path_exists(path):
                message = (
                    'The provided path to feature file does not exist.')
                raise ValueError(message)

            return self.load_from_path(path)

        return self.compute()


class TimeFeature(TimeMediaMixin, Feature):
    pass


class FrequencyFeature(FrequencyMediaMixin, Feature):
    pass


class TimeFrequencyFeature(TimeFrequencyMediaMixin, Feature):
    pass
