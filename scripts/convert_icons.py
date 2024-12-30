#!/usr/bin/env python3
import os
from PIL import Image


def convert_icon(input_path, output_path, size=128, border_width=20):
    """
    Convert an icon to a specific size with border width
    size: the total size of the output image
    border_width: the border width as specified in DrawIO export settings
    """
    try:
        with Image.open(input_path) as img:
            # Convert to RGBA if the image is in a different mode
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Create a new image with transparent background
            new_img = Image.new(
                "RGBA", (size + 2 * border_width, size + 2 * border_width), (0, 0, 0, 0)
            )

            # Calculate the resize dimensions while maintaining aspect ratio
            target_size = (size, size)
            img_ratio = img.size[0] / img.size[1]
            if img_ratio > 1:
                # Width is the limiting factor
                resize_size = (size, int(size / img_ratio))
            else:
                # Height is the limiting factor
                resize_size = (int(size * img_ratio), size)

            # Resize the image
            img = img.resize(resize_size, Image.Resampling.LANCZOS)

            # Calculate position to paste (center the image)
            paste_x = border_width + (size - resize_size[0]) // 2
            paste_y = border_width + (size - resize_size[1]) // 2

            # Paste the resized image onto the background
            new_img.paste(img, (paste_x, paste_y), img)

            # Save the result
            new_img.save(output_path, "PNG")
            print(
                f"Converted: {os.path.basename(input_path)} -> {os.path.basename(output_path)}"
                f" (size: {size}x{size}, border: {border_width}px, total: {size + 2 * border_width}x{size + 2 * border_width})"
            )

    except Exception as e:
        print(f"Error converting {input_path}: {str(e)}")


def main():
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Set up input and output directories
    input_dir = os.path.join(project_root, "docs/Flowchart/icons_source")
    output_dir = os.path.join(project_root, "docs/Flowchart/icons_output")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Supported image formats
    supported_formats = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico")

    # Process all images in the input directory
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(supported_formats):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(
                output_dir, os.path.splitext(filename)[0] + ".png"
            )
            # Convert with size 128x128 and border width 20 (total 168x168)
            convert_icon(input_path, output_path, size=128, border_width=20)


if __name__ == "__main__":
    main()
