import os
import base64
from PIL import Image
from io import BytesIO

# Define base64 encodings for icons
ICON_DATA = {
    # Lock/Unlock icons
    "lock.png": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAjklEQVR4nO2USwrAIAxEJ9SLFLzJXEQ8hyDewYvoNiwFQWuaSL9QyINZGXyTGSPC+LtwzgFKWSil9qiZOQLA0gOllDPVNYWsWX/HEgDGGCilHK+5jWaLJGZmAJhn9toU/vO0JndSuFEPykmpWQbXRltLmxyhZxl8jm48zLWTPO+gJ5bw7t7E+zwR83eEL+MBCNJ1cYx21mcAAAAASUVORK5CYII=",
    "unlock.png": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAsklEQVR4nO2UTQrCQAyFP8Sbdf/xJp5B7MYTuXDpVtCFPyCCXkPMQoqUOtN2nAEN+CAQMnnzXiaZwR5/Bd8PyeV4vF2ul3s+HpKq9waK7cKYrDHcwH2qGzzPTsAWOAJKIbfABZgqTa6VJlVsMgA2xSZDA88bozRZdW3ShIrN+b1dZWngeWM+xKr2EkUHDxY1S8i74VCz+l4VKaV8jXKVvk4mKdU4vGaSL5K/if57yjkAD0ZAcbmfGMFmAAAAAElFTkSuQmCC",
    
    # Auto/Manual icons
    "auto.png": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAACEklEQVR4nL2Vz0tVURTHP+fpKIiDMkdBMAJxEP0BEf4FTcJJDppEg9D5jJw0aNCgoEETJ04aBU2aNohAkAZRgyDKQRD0A3+gIpKK5NO3775931t3ve19DUQXznDvWvtz1l77rHvh/6w2kLIKgIpzRgzmnHF1y8q6z+/wZpKXh3YDEbAOBBtCkLsGnHXO0F9Uk0FmOYMKKH8KIcCVkjrwS7FQYMBnlTXdgTtWtMpFYEbY+Yl7YyeMcYYfAB6KyJJT+C3qxLWvKTVw4fhFKxpRcmGMA8YC/qhBwWU2GDJGKXNiVcG5JLzRwFqDV6Cv2x9iBVd8G6sqWrcuDj76Y3dD0JfSKb6IQTmjvnEVaO21HwI0jAKWgfHk43eB7xsJeB4n0WB3OQs3FiYuSNmugaeBTu3UrUlvMNr+mLK1FXiRWw+4aQ1m/UlHQecHAVQrKQD1nHXONS8wdXgRGPOCcWCtEu/cBfwFRoD3wGtgoMGUJbgfuA10JQDvVOUeZxzZN7i+A9zPffCr4qQHdOv9uo02QXeTXmR+FdgFnOgEfgNnKlkh12jbDLTsUOd7U5e4eiNl0pv9dI2mwQ9NdF+zzrIQeK4uWnbAyeQgJQRnE97kLBotdMlzMJvS4d6QCZuBz8nJTgK3EqN1YBM438jFlM7lL9i1IhDvW9FyrxlvMKH/6Hez/Qw2VXQF2tZ+AnP76Z5zdMKOAAAAAElFTkSuQmCC",
    "manual.png": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAAB0UlEQVR4nM1VS0tbQRT+JqFCqRTpQlzowrZgbZdK/QuCiy5jLoguXIk/oIKLtpvsK+TCbheKuHGhiQhCRPEdY5q0UQwh79z7yDEzvV6T6LnU6EM+GMbMd77znTlnHsAvn2/wfKH5OdQNXg6NZrOZTa5kMr89a9AKe71WoxIE+BoEeO8H+OAHqPsNPPrRwDj3T5UUfV/Lxe327kw+fzEMHt/7AUkEk1ZrqlHYkWGYzzzPQbFYjXu9GbfbQ7vdO0ylkjYAxRj/w/b2qyQPvl/n5Jrrlty7FoR+qoSbZtvtzPFyIpEwLYVeQ7UPbtuYbJY9xHNDiT+m+XWoQSmBQODzRxSivdMR4CyKw+F40lL4ZxSZv47RhEk0gF2YaAvqVCQIhM2iyXl5jl+QS+4JhcT9A0Zi7wiCS2okApP9GokGfEe1IFZwTAmBxw3ZlbgeUxH8kxp9OVYkEVP+Sw5+IbdUxBh8QW6w5FfzlAiXw0sRSVwDa8Cq9sLo9XP0q3TZLkb6LU7qGH1HNVlHRQdgG9Md0KXHXDZlBD1wZDcKuSzh0IbOwKVD2aIXAI7l+3vIyV/pLiP8vJLndxQ/r0Wz6A6KQ70/UPxBHXt71cxMOo1pZ/AfwDejndQsQQKd5gAAAABJRU5ErkJggg==",
    
    # Motors on/off icons
    "motors_on.png": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAABYElEQVR4nOWVP0vDUBTFf7EWLLi4ualTdHSwQqEKHRwcXCyIH8HRb+DgYMHRzc/QydHJLyBFh+pSHdz8s1ZEqNKmTeJgHgSRJG9IA+IPHsm95553cu+7N5D+yhLQBAIZLXm2YIUlPaAm84bAVBwjLXnfB/piANAHdqQXm2MWOATGQMe0wKoYdIBVM6nufRexJbMowKwYFLwYA9pK5FnNkxU2hpLkUlwJVBSNjcV0jLNgBOxHGHwAm/N0UQM4Ap6AV+AZOAFKYqOs0pPYJRYpK8GJasb3vwjcyLpO9JHJZVM18mqw/gYXST5QMQ1MKv7aOgGOgYYqcFvF1HPg2Ow6I4ssBruyThc4Aw7MyZJUGrJrx93BppFzHJJfN9ZxXCX2K/BuSZ5E2kboXu0A2Pc7tpXXVSLPOF/m8hb1DNi0dVQyYu+V2DEfmZslTeZpMHAtzjO5L7vf/ZXPpODkfwBQsyB9e1jDGQAAAABJRU5ErkJggg==",
    "motors_off.png": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAABjklEQVR4nM2VsUtCURTGf48GN4cGdUmXQIJoaEgEnJwaGiKMCKGhsb/AoUGipcH/oE0aGlyCCFyixcFVEBRFEATxJQo+n3rq+joPQeS+d0Ww9IMLl3u+c77vnnvuuRf+dyyBOA/IQC5ySk46t2XmFcW+FZMPLxvuTJFdBnaACm5Umah0fAScA9fAF5CFWWDBELCEzBjsC4ozg/0RWJ5HwKEIfPvsGRHvBPmVoxz9DBLfAseW6i38wJMIXAHrPnsWOBORD2B3FoEz6SUTsN8SUw7oTkMAI6QrQttA2WdLifCZwfYjRDERwCMwCQnIZxhvdMbliHkpKVgKCRjHzGg5MqVLkWA0RUOZZDRLoR4isIwm+Ao4BfaBI1n3QmOGWJqF59+CnLAKvAEt4AO4A3YnCzwLyPcjI1oCp8AksFcPOkTfiLLiw9iimJyMPNXyP6WUKKO5f12HqCxeGXJAdh4Bj2BXRbTiKQ/ZT/qmRnkL29J+YnLKWHWIyqKvA76C/fmyc5MukbTorNJ5LSaXzn37K59JwZN/ATn2WEP5+aKvAAAAAElFTkSuQmCC",
    
    # Playback icons
    "play.png": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAVklEQVR4nGNgGAUjAXAAsX6o/R+KOaBoKxD/h2IUi9iB+BcUf4Yi0oBEID6HxZH4MAdJlg4m8AOIpUkxnBGIL+CIg4tQOXrCbHgk8ZgfBeQAZmIdAACg1h4Jmn+5GAAAAABJRU5ErkJggg==",
    "stop.png": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAMUlEQVR4nGNgGAWjgHbAY7AF/EY88B2x8KNJPOQc3kSSw41DzZGjSTzkHD4KRgFNAACYMQ0LPzYKQQAAAABJRU5ErkJggg=="
}

# Create output folder if it doesn't exist
if not os.path.exists("ui/resources"):
    os.makedirs("ui/resources")

# Save icons
for filename, b64_data in ICON_DATA.items():
    img_data = base64.b64decode(b64_data)
    img = Image.open(BytesIO(img_data))
    
    output_path = os.path.join("ui/resources", filename)
    img.save(output_path)
    print(f"Created {output_path}")

print("All icons created successfully!") 