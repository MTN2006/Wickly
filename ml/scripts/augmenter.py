import os
from keras_preprocessing.image import (
    ImageDataGenerator,
    img_to_array,
    load_img,
    array_to_img
)
import numpy as np

input_folder = "/Users/mohammadtalha/Documents/Projects/Wickly/ml/scripts/hammer"
output_folder = "hammer_augmented"  # folder to save augmented images
os.makedirs(output_folder, exist_ok=True)

augmentor = ImageDataGenerator(
    zoom_range=0.1,
    width_shift_range=0.05,
    height_shift_range=0.05,
    fill_mode='nearest'
)

AUG_PER_IMAGE = 10
count = 0

for fname in os.listdir(input_folder):
    if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
        continue
    path = os.path.join(input_folder, fname)
    img = load_img(path)
    x = img_to_array(img)
    x = np.expand_dims(x, axis=0)

    gen = augmentor.flow(x, batch_size=1)
    for i in range(AUG_PER_IMAGE):
        batch = next(gen)
        new_img = array_to_img(batch[0])
        new_img.save(os.path.join(output_folder, f"hammer_aug_{count}.png"))
        count += 1

print(f"✅ Generated {count} augmented images.")