import mimetypes

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from supabase import create_client


@deconstructible
class SupabaseStorage(Storage):
    """
    Django Storage backend backed by a Supabase Storage bucket.

    Files are named by the model's `upload_to` path (found_persons/<uuid>.<ext>),
    so collisions are effectively impossible and every upload is done with
    upsert=true rather than paying for an extra existence check per save.
    """

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return self._client

    @property
    def bucket(self):
        return self.client.storage.from_(settings.SUPABASE_BUCKET)

    def _save(self, name, content):
        content.seek(0)
        data = content.read()
        content_type = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0] or "application/octet-stream"
        self.bucket.upload(name, data, {"content-type": content_type, "upsert": "true"})
        return name

    def exists(self, name):
        return False

    def url(self, name):
        return self.bucket.get_public_url(name)

    def delete(self, name):
        self.bucket.remove([name])

    def size(self, name):
        raise NotImplementedError("SupabaseStorage does not support size().")

    def _open(self, name, mode="rb"):
        data = self.bucket.download(name)
        return ContentFile(data, name=name)
