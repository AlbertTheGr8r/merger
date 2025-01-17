"""
Merge all images in a folder into one image.

Usage:
    python merger.py --path <image_path> --out <out_path>

Example:
    python merger.py --path /home/user/images --out /home/user/
"""
from os.path import basename

import numpy as np
import argparse
import os
import re
from PIL import Image, ImageOps
from natsort import natsorted


def success_print(title, message):
    print(f"\033[92m{title}\033[0m: {message}")


def error_print(title, message):
    print(f"\033[91m{title}\033[0m: {message}")
    exit(1)


def parse_args():
    parser = argparse.ArgumentParser("Merge all images in a folder into one image")
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        required=True,
        help="Path to the folder containing the images",
    )
    parser.add_argument(
        "-o", "--out", type=str, required=True, help="Path to the output folder"
    )
    args = parser.parse_args()

    args.path = os.path.abspath(args.path)
    files = check_for_files(args.path)

    if os.path.isdir(args.path) and not files:
        split_dirs = [
            os.path.join(args.path, split_dir)
            for split_dir in os.listdir(args.path)
            if os.path.isdir(os.path.join(args.path, split_dir))
            if check_for_files(os.path.join(args.path, split_dir))
        ]
    elif os.path.isdir(args.path) and files:
        split_dirs = [args.path]
    else:
        split_dirs = []

    if not split_dirs:
        error_print("Error", "No tiled images found in the specified directory.")

    success_print("Success", f"Found {len(split_dirs)} tiled images.")

    os.makedirs(args.out, exist_ok=True)
    return split_dirs, args.out


def check_for_files(path):
    files = []
    for file in os.listdir(path):
        matches = re.findall("_[0-9]+_[0-9]+.[a-zA-Z]+", file)
        if matches:
            files.append(file)

    return files


def check_image_file(image):
    image_extensions = [".jpg", ".jpeg", ".tif", ".bmp", ".png", ".gif"]
    for image_ext in image_extensions:
        if image.endswith(image_ext):
            return True
    return False


def group_images(images, image_ext):
    all_images = natsorted(images)
    last_y = 0
    group_index = 0
    grouped_images = [[]]
    for image in all_images:
        if image.endswith(image_ext):
            image_name_no_ext = image.replace("." + image_ext, "")
            coord_y = image_name_no_ext.split("_")[-2]
            if int(coord_y) == last_y:
                grouped_images[group_index].append(os.path.join(image))
            else:
                grouped_images.append([image])
                group_index += 1
                last_y = int(coord_y)

    return grouped_images


def pad_image(image, max_heights, max_widths):
    image_height = image.height
    image_width = image.width
    image_name_no_ext = os.path.basename(image.filename).replace("." + image.format, "")
    coord_y = int(image_name_no_ext.split("_")[-2])
    target_height = max_heights[coord_y]
    target_width = max_widths[coord_y]

    padding_height = target_height - image_height
    padding_width = target_width - image_width
    pad_top = padding_height // 2
    pad_bottom = padding_height - pad_top
    pad_left = padding_width // 2
    pad_right = padding_width - pad_left
    return ImageOps.expand(image, (pad_left, pad_top, pad_right, pad_bottom), fill="black")


def merge(grouped_images):
    horizontal_parts = []
    max_heights = [0] * len(grouped_images)
    max_widths = [0] * len(grouped_images)

    for i, group in enumerate(grouped_images):
        images = [Image.open(image) for image in group]
        for image in images:
            image_height = image.height
            image_width = image.width
            image_name_no_ext = os.path.basename(image.filename).replace("." + image.format, "")
            coord_y = int(image_name_no_ext.split("_")[-2])
            max_heights[coord_y] = max(max_heights[coord_y], image_height)
            max_widths[i] = max(max_widths[i], image_width)

    for i, group in enumerate(grouped_images):
        images = [Image.open(image) for image in group]
        padded_images = [pad_image(image, max_heights, max_widths) for image in images]
        horizontal_part = np.hstack([np.asarray(image) for image in padded_images])
        horizontal_parts.append(Image.fromarray(horizontal_part))

    full_image = np.vstack([np.asarray(image) for image in horizontal_parts])
    full_image = Image.fromarray(full_image)

    return full_image


def main():
    split_dirs, out_path = parse_args()
    for split_dir in split_dirs:
        all_images = [
            os.path.join(split_dir, image)
            for image in os.listdir(split_dir)
            if check_image_file(image)
        ]
        image_ext = all_images[0].split(".")[-1]
        image_name = basename(all_images[0]).replace(
            re.findall(f"_[0-9]+_[0-9]+.{image_ext}", all_images[0])[-1], ""
        )

        grouped_images = group_images(all_images, image_ext)
        full_image = merge(grouped_images)

        image_ext = all_images[0].split(".")[-1]

        success_print(
            "Saving",
            f"{os.path.join(out_path, image_name)}.{image_ext}",
        )
        full_image.save(os.path.join(out_path, image_name + "_merged." + image_ext))


if __name__ == "__main__":
    main()
