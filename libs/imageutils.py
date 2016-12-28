import io
import requests
from PIL import Image, ImageOps


def fit_size(image_url, size=None):
    old = Image.open(io.BytesIO(requests.get(image_url).content)).convert('RGB')
    if not size:
        size = (0, int(old.size[0] / 4))
    new = ImageOps.expand(
        old,
        border=size,
        fill='white'
    )
    arr = io.BytesIO()
    new.save(arr, format='PNG')
    arr.seek(0)
    return io.BufferedReader(arr)
