"""
AI Face Recognition utility.

Generates 128-d face embeddings with the `face_recognition` library (dlib
ResNet under the hood) and compares them with cosine similarity, per spec:

    percentage = (1 - cosine_distance) * 100

Swap `generate_face_embedding` for a DeepFace-based implementation (512-d,
e.g. ArcFace/Facenet512) if you'd rather use that backend — the rest of the
pipeline (storage, comparison, thresholding) is agnostic to embedding size.
"""
import logging

import numpy as np

logger = logging.getLogger(__name__)


def generate_face_embedding(photo_field):
    """
    Returns a 128-d embedding (list[float]) for the first face found in
    `photo_field` (an ImageField/FieldFile — read via `.open()` so this works
    with any storage backend, local or cloud), or None if no face was detected.
    """
    try:
        import face_recognition
    except ImportError:  # pragma: no cover
        logger.error(
            "face_recognition is not installed. Run `pip install face_recognition` "
            "(requires cmake + dlib) to enable AI matching."
        )
        return None

    with photo_field.open("rb") as f:
        image = face_recognition.load_image_file(f)
    face_locations = face_recognition.face_locations(image)
    if not face_locations:
        return None

    encodings = face_recognition.face_encodings(image, known_face_locations=face_locations)
    if not encodings:
        return None

    return encodings[0].tolist()


def generate_face_embedding_deepface(image_path, model_name="ArcFace"):
    """
    Alternative embedding backend using DeepFace (e.g. for 512-d ArcFace /
    Facenet512 embeddings). Not called by default — see face_utils module
    docstring.
    """
    try:
        from deepface import DeepFace
    except ImportError:  # pragma: no cover
        logger.error("deepface is not installed. Run `pip install deepface` to use this backend.")
        return None

    try:
        result = DeepFace.represent(img_path=image_path, model_name=model_name, enforce_detection=True)
    except Exception:
        logger.exception("DeepFace failed to find a face in %s", image_path)
        return None

    if not result:
        return None
    return result[0]["embedding"]


def cosine_similarity_percentage(embedding_a, embedding_b):
    """
    percentage = (1 - cosine_distance) * 100, where cosine_distance = 1 - cosine_similarity.
    So percentage is simply cosine_similarity * 100, clamped to [0, 100].
    """
    a = np.array(embedding_a, dtype=np.float64)
    b = np.array(embedding_b, dtype=np.float64)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0

    cosine_similarity = float(np.dot(a, b) / (norm_a * norm_b))
    percentage = cosine_similarity * 100
    return max(0.0, min(100.0, percentage))


def find_matches(query_embedding, candidates, threshold=50.0):
    """
    candidates: iterable of (object, embedding) tuples, e.g. (FoundPerson, embedding_list).
    Returns a list of (object, match_percentage) sorted descending, filtered
    to match_percentage > threshold.
    """
    matches = []
    for obj, embedding in candidates:
        if not embedding:
            continue
        percentage = cosine_similarity_percentage(query_embedding, embedding)
        if percentage > threshold:
            matches.append((obj, round(percentage, 2)))

    matches.sort(key=lambda pair: pair[1], reverse=True)
    return matches
