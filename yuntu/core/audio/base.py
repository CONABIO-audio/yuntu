"""Base classes for audio manipulation."""
from abc import ABC, abstractmethod
from pony.orm import db_session
from yuntu.core.database.base import Recording
import yuntu.core.audio.utils as audio_utils


class Media(ABC):
    """Abstract class for any media object."""

    @abstractmethod
    def build(self, meta, insert):
        """Build object from configuration input.

        This method tries insert data if 'insert' is True.
        """

    @abstractmethod
    def read(self):
        """Read media from file."""

    @abstractmethod
    def write(self, path, out_format):
        """Write media to path."""


class Audio(Media):
    """Class for all audio."""

    db_instance = None
    path = None
    timeexp = None
    media_info = None
    read_sr = None
    mask = None
    signal = None
    samplerate = None

    def __init__(self, meta, insert=False):
        self.build(meta, insert)

    @db_session
    def build(self, meta, insert):
        if isinstance(meta, Recording):
            self.db_instance = meta
        if "path" not in meta or "timeexp" not in meta:
            raise ValueError("Config dictionary must include both, path \
                             and time expansion.")
        if "id" in meta:
            self.db_instance = Recording[meta["id"]]
        elif insert:
            if "media_info" not in meta:
                meta["media_info"] = audio_utils.read_info(meta["path"],
                                                           meta["timeexp"])
            if "hash" not in meta:
                meta["hash"] = audio_utils.hash_file(meta["path"])
            self.db_instance = Recording(**meta)
        if self.db_instance is not None:
            self.media_info = self.db_instance.media_info
            self.timeexp = self.db_instance.timeexp
            self.path = self.db_instance.path
        else:
            self.timeexp = meta["timeexp"]
            self.path = meta["path"]
            self.media_info = audio_utils.read_info(meta["path"],
                                                    meta["timeexp"])
        self.read_sr = self.media_info["samplerate"]

    def set_read_sr(self, read_sr=None):
        """Set read sample rate for future loadings."""
        if read_sr is None:
            read_sr = self.media_info["samplerate"]
        if self.signal is not None and self.read_sr != read_sr:
            self.clear()
        self.read_sr = read_sr

    def set_mask(self, limits=None):
        """Set read mask.

        A read mask is a time interval that determines the part of
        the recording that is going to be read and affects any output that
        uses loaded data.
        """
        if limits is not None:
            offset = limits[0]
            duration = limits[1] - limits[0]
            self.mask = (offset, duration)
        self.clear()

    def unset_mask(self):
        """Unset read mask."""
        self.set_mask()

    def get_signal(self, refresh=False):
        """Read signal from file (mask sensitive, lazy loading)."""
        if self.signal is not None and not refresh:
            return self.signal
        self.read()
        return self.signal

    def get_spec(self):
        """Compute spectrogram (mask sensitive)."""

    def clear(self):
        """Clear cached data."""
        self.signal = None
        self.samplerate = None

    def read(self):
        """Read signal from file (mask sensitive, lazy loading)."""
        if self.mask is not None:
            offset, duration = self.mask
            self.signal, self.samplerate = audio_utils.read_media(self.path,
                                                                  self.read_sr,
                                                                  offset,
                                                                  duration)
        self.signal, self.samplerate = audio_utils.read_media(self.path,
                                                              self.read_sr)

    def write(self,
              path,
              media_format="wav",
              samplerate=None):
        """Write media to path."""
        signal = self.get_signal()
        out_sr = self.samplerate
        if samplerate is not None:
            out_sr = samplerate
        audio_utils.write_media(self.path,
                                signal,
                                out_sr,
                                self.media_info["nchannels"],
                                media_format)
