from PIL import Image, ImageChops, ImageDraw
import os

def new_gray(size, color):
    img = Image.new('L', size)
    dr = ImageDraw.Draw(img)
    dr.rectangle((0, 0) + size, color)
    return img

def create_ignore_mask(size, ignore_regions):
    mask = new_gray(size, 255)  # Start with a full white mask
    draw = ImageDraw.Draw(mask)

    # Draw black rectangles in the areas to be ignored
    for region in ignore_regions:
        draw.rectangle(region, fill=0)

    return mask

def highlight_individual_differences(a, b, ignore_regions=[], opacity=0.85):
    diff = ImageChops.difference(a, b)
    diff = diff.convert('L')

    # Create an ignore mask and apply it to the difference image
    ignore_mask = create_ignore_mask(diff.size, ignore_regions)
    diff = ImageChops.multiply(diff, ignore_mask)

    # Amplify the differences to make them more visible
    thresholded_diff = diff.point(lambda p: p > 0 and 255)

    # Find the connected components (distinct regions)
    diff_data = thresholded_diff.load()
    width, height = thresholded_diff.size

    visited = set()
    regions = []

    def find_region(x, y):
        stack = [(x, y)]
        region = []

        while stack:
            cx, cy = stack.pop()
            if (cx, cy) not in visited and 0 <= cx < width and 0 <= cy < height and diff_data[cx, cy] == 255:
                visited.add((cx, cy))
                region.append((cx, cy))
                # Check 4-connectivity
                stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])
        return region

    for x in range(width):
        for y in range(height):
            if diff_data[x, y] == 255 and (x, y) not in visited:
                region = find_region(x, y)
                if region:
                    regions.append(region)

    # Convert the images to RGBA mode for transparency handling
    a = a.convert('RGBA')
    b = b.convert('RGBA')

    # Draw rectangles around each distinct region with semi-transparent yellow fill
    draw_a = ImageDraw.Draw(a)
    draw_b = ImageDraw.Draw(b)
    
    for region in regions:
        x_min = min(p[0] for p in region)
        y_min = min(p[1] for p in region)
        x_max = max(p[0] for p in region)
        y_max = max(p[1] for p in region)

        # Draw yellow rectangles
        draw_a.rectangle([x_min, y_min, x_max, y_max], outline="yellow", width=3)
        draw_b.rectangle([x_min, y_min, x_max, y_max], outline="yellow", width=3)

    h, w = diff.size
    mask = new_gray((w, h), int(255 * opacity))
    shade = new_gray((w, h), 0)
    new = a.copy()
    new.paste(shade, mask=mask)
    new.paste(b, mask=thresholded_diff)
    return new, a, b, len(regions)

def process_image_files(old_image_path, new_image_path, diff_folder, ignore_regions=[]):
    # Open the images
    old = Image.open(old_image_path)
    new = Image.open(new_image_path)

    # Check if the images are the same size and mode, resize or convert if necessary
    if old.size != new.size:
        print(f"Resizing images: {os.path.basename(old_image_path)}")
        new = new.resize(old.size)

    if old.mode != new.mode:
        print(f"Converting image modes: {os.path.basename(old_image_path)}")
        new = new.convert(old.mode)

    # Run the comparison function
    highlighted_diff, highlighted_old, highlighted_new, total_diffs = highlight_individual_differences(old, new, ignore_regions)

    if total_diffs != 0:
        # Create the merged image
        width, height = highlighted_old.size
        merged_image = Image.new('RGBA', (width * 2, height))
        merged_image.paste(highlighted_old, (0, 0))
        merged_image.paste(highlighted_new, (width, 0))

        # Create output filename based on the input file name
        base_filename = os.path.splitext(os.path.basename(old_image_path))[0]
        output_filename = f"{base_filename}_highlighted.png"
        output_path = os.path.join(diff_folder, output_filename)

        # Ensure the 'diff' folder exists
        os.makedirs(diff_folder, exist_ok=True)

        # Save the merged image in the diff folder
        merged_image.save(output_path)
        print(f"Merged image saved as: {output_path}")

# Paths to the input images and output folder
old_image_path = 'old/00043.png'
new_image_path = 'new/00043.png'
diff_folder = 'diff'  # Folder to save the merged images

# Specify regions to ignore [(x1, y1, x2, y2), ...]
# Minutes in datetime regions
ignore_regions = [
    (305, 98, 306, 99),  
    (305, 100, 309, 114), 
    (309, 99, 310, 99), 
    (309, 106, 314, 115),  
    (311, 103, 311, 104), 
    (313, 98, 313, 98), 
    (313, 103, 313, 104) 
]

# Process the specified image files
process_image_files(old_image_path, new_image_path, diff_folder, ignore_regions)
